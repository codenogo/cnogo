#!/usr/bin/env python3
"""cnogo Memory Engine — Public API.

Purpose-built issue tracker for cnogo's artifact-driven SDLC.
Zero external dependencies (stdlib + sqlite3 only).

Usage from commands:
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path('.').resolve()))
    from scripts.memory import init, create, ready, claim, close

Usage from CLI:
    python3 scripts/workflow_memory.py ready
    python3 scripts/workflow_memory.py create --title "My task"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import storage as _st
from .identity import content_hash as _content_hash
from .identity import generate_child_id as _child_id
from .identity import generate_id as _gen_id
from .graph import rebuild_blocked_cache as _rebuild_blocked_cache
from .models import Dependency, Event, Issue
from .storage import with_retry as _with_retry

__all__ = [
    # Init
    "init", "is_initialized",
    # Issue CRUD
    "create", "show", "update", "claim", "close", "reopen", "release",
    # Query
    "ready", "list_issues", "stats", "get_phase", "set_phase",
    # Dependencies
    "dep_add", "dep_remove", "blockers", "blocks",
    # Sync
    "export_jsonl", "import_jsonl", "sync",
    # Context
    "prime", "checkpoint", "history", "show_graph",
    # Bridge (Agent Teams integration)
    "plan_to_task_descriptions", "generate_implement_prompt",
    "detect_file_conflicts",
    # Worktree (parallel agent isolation)
    "create_session", "merge_session", "cleanup_session",
    "get_conflict_context", "load_session", "save_session",
]

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_DB_NAME = "memory.db"
_CNOGO_DIR = ".cnogo"
_root: Path | None = None


def _db_path(root: Path | None = None) -> Path:
    r = root or _root or Path(".")
    return r / _CNOGO_DIR / _DB_NAME


def _conn(root: Path | None = None):  # noqa: ANN202
    """Get a connection to the memory database."""
    return _st.connect(_db_path(root))


def _emit(conn, issue_id: str, event_type: str, actor: str,
          data: dict[str, Any] | None = None) -> None:
    """Record an event in the audit trail."""
    _st.insert_event(conn, Event(
        issue_id=issue_id,
        event_type=event_type,
        actor=actor,
        data=data or {},
        created_at=_st._now(),
    ))


def _auto_export(root: Path) -> None:
    """Best-effort JSONL export after state-changing operations.

    Keeps .cnogo/issues.jsonl in sync with SQLite so git always sees
    the latest state. Failures are silently ignored — JSONL is a
    convenience layer, not the source of truth.
    """
    try:
        from .sync import export_jsonl as _export
        _export(root)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def init(root: Path) -> None:
    """Initialize .cnogo/ directory with memory.db schema."""
    global _root
    _root = root
    cnogo_dir = root / _CNOGO_DIR
    cnogo_dir.mkdir(parents=True, exist_ok=True)
    conn = _st.connect(cnogo_dir / _DB_NAME)
    conn.close()


def is_initialized(root: Path | None = None) -> bool:
    """Check if memory engine is set up in this project."""
    r = root or _root or Path(".")
    return (r / _CNOGO_DIR / _DB_NAME).exists()


# ---------------------------------------------------------------------------
# Issue CRUD
# ---------------------------------------------------------------------------

def create(
    title: str,
    *,
    issue_type: str = "task",
    parent: str | None = None,
    feature_slug: str | None = None,
    plan_number: str | None = None,
    phase: str | None = None,
    priority: int = 2,
    labels: list[str] | None = None,
    description: str | None = None,
    metadata: dict | None = None,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Create a new issue. Returns Issue with generated ID.

    Retries on SQLITE_BUSY with exponential backoff for multi-agent
    robustness.
    """
    r = root or _root or Path(".")

    def _do_create() -> Issue:
        conn = _conn(r)
        try:
            # Acquire write lock early for child counter atomicity (W-1)
            conn.execute("BEGIN IMMEDIATE")
            now = _st._now()

            # Generate ID — hierarchical if parent given, hash-based otherwise
            if parent is not None:
                if not _st.id_exists(conn, parent):
                    raise ValueError(f"Parent issue {parent} not found")
                child_num = _st.next_child_number(conn, parent)
                issue_id = _child_id(parent, child_num)
            else:
                # Try with increasing nonce, then more bytes on collision
                issue_id = ""
                for nonce in range(10):
                    candidate = _gen_id(title, actor, nonce=nonce)
                    if not _st.id_exists(conn, candidate):
                        issue_id = candidate
                        break
                if not issue_id:
                    # Extend to 5 bytes
                    for nonce in range(10):
                        candidate = _gen_id(title, actor, id_bytes=5, nonce=nonce)
                        if not _st.id_exists(conn, candidate):
                            issue_id = candidate
                            break
                if not issue_id:
                    raise RuntimeError("Failed to generate unique ID after retries")

            chash = _content_hash(title, description or "", issue_type)

            issue = Issue(
                id=issue_id,
                title=title,
                content_hash=chash,
                description=description or "",
                status="open",
                issue_type=issue_type,
                priority=priority,
                feature_slug=feature_slug or "",
                plan_number=plan_number or "",
                phase=_st.normalize_phase(phase or "discuss"),
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )

            _st.insert_issue(conn, issue)

            # Labels
            for lbl in (labels or []):
                _st.add_label(conn, issue_id, lbl)
            issue.labels = labels or []

            # Parent-child dependency
            if parent is not None:
                dep = Dependency(
                    issue_id=issue_id,
                    depends_on_id=parent,
                    dep_type="parent-child",
                    created_at=now,
                )
                _st.insert_dependency(conn, dep)

            # Event
            _emit(conn, issue_id, "created", actor, {
                "title": title,
                "issue_type": issue_type,
                "parent": parent,
            })

            # Rebuild blocked cache after structural change
            _rebuild_blocked_cache(conn)

            conn.commit()
            return issue
        finally:
            conn.close()

    result = _with_retry(_do_create)
    _auto_export(r)
    return result


def show(issue_id: str, *, root: Path | None = None) -> Issue | None:
    """Get full issue details including deps, labels, and recent events."""
    conn = _conn(root)
    try:
        issue = _st.get_issue(conn, issue_id)
        if issue is None:
            return None
        issue.labels = _st.get_labels(conn, issue_id)
        issue.deps = _st.get_dependencies(conn, issue_id)
        issue.blocks_issues = [
            i.id for i in _st.get_blocks(conn, issue_id)
        ]
        issue.recent_events = _st.get_events(conn, issue_id, limit=10)
        return issue
    finally:
        conn.close()


def update(
    issue_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    assignee: str | None = None,
    metadata: dict | None = None,
    comment: str | None = None,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Update issue fields. Emits 'updated' event.

    The ``assignee`` parameter allows direct reassignment without going
    through the release/claim cycle. Pass an empty string to unassign.
    """
    r = root or _root or Path(".")
    conn = _conn(r)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")

        fields: dict[str, Any] = {}
        changes: dict[str, Any] = {}

        if title is not None and title != existing.title:
            fields["title"] = title
            changes["title"] = {"old": existing.title, "new": title}
        if description is not None and description != existing.description:
            fields["description"] = description
            changes["description"] = True
        if priority is not None and priority != existing.priority:
            fields["priority"] = priority
            changes["priority"] = {"old": existing.priority, "new": priority}
        if assignee is not None and assignee != existing.assignee:
            fields["assignee"] = assignee
            changes["assignee"] = {"old": existing.assignee, "new": assignee}
        if metadata is not None:
            merged = {**existing.metadata, **metadata}
            fields["metadata"] = merged
            changes["metadata_keys"] = list(metadata.keys())

        if fields:
            # Recompute content hash
            new_title = fields.get("title", existing.title)
            new_desc = fields.get("description", existing.description)
            fields["content_hash"] = _content_hash(
                new_title, new_desc, existing.issue_type
            )
            _st.update_issue_fields(conn, issue_id, **fields)

        if comment:
            _emit(conn, issue_id, "commented", actor, {"comment": comment})
        if changes:
            _emit(conn, issue_id, "updated", actor, changes)

        conn.commit()
        result = _st.get_issue(conn, issue_id)  # type: ignore[return-value]
    finally:
        conn.close()
    _auto_export(r)
    return result


def claim(
    issue_id: str,
    *,
    actor: str,
    root: Path | None = None,
) -> Issue:
    """Atomic claim: sets assignee + in_progress. Raises if already claimed.

    Retries on SQLITE_BUSY with exponential backoff for multi-agent
    robustness.
    """
    r = root or _root or Path(".")

    def _do_claim() -> Issue:
        conn = _conn(r)
        try:
            # Acquire write lock early for CAS atomicity (W-6)
            conn.execute("BEGIN IMMEDIATE")
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if existing.status == "closed":
                raise ValueError(f"Issue {issue_id} is closed")

            ok = _st.claim_issue(conn, issue_id, actor)
            if not ok:
                raise ValueError(
                    f"Issue {issue_id} already claimed by {existing.assignee!r}"
                )

            _emit(conn, issue_id, "claimed", actor)
            conn.commit()
            return _st.get_issue(conn, issue_id)  # type: ignore[return-value]
        finally:
            conn.close()

    result = _with_retry(_do_claim)
    _auto_export(r)
    return result


def close(
    issue_id: str,
    *,
    reason: str = "completed",
    comment: str | None = None,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Close an issue. Rebuilds blocked cache, auto-closes parent epic if
    all siblings are now closed, and auto-exports JSONL.

    Retries on SQLITE_BUSY with exponential backoff for multi-agent
    robustness.
    """
    r = root or _root or Path(".")

    def _do_close() -> Issue:
        conn = _conn(r)
        try:
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")

            ok = _st.close_issue(conn, issue_id, reason)
            if not ok:
                raise ValueError(f"Issue {issue_id} is already closed")

            _emit(conn, issue_id, "closed", actor, {
                "reason": reason,
                "comment": comment or "",
            })

            # Auto-close parent epic if all children are now closed
            _try_auto_close_parent(conn, issue_id, actor)

            _rebuild_blocked_cache(conn)
            conn.commit()
            return _st.get_issue(conn, issue_id)  # type: ignore[return-value]
        finally:
            conn.close()

    result = _with_retry(_do_close)
    _auto_export(r)
    return result


def reopen(
    issue_id: str,
    *,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Reopen a closed issue."""
    r = root or _root or Path(".")
    conn = _conn(r)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")

        ok = _st.reopen_issue(conn, issue_id)
        if not ok:
            raise ValueError(f"Issue {issue_id} is not closed")

        _emit(conn, issue_id, "reopened", actor)
        _rebuild_blocked_cache(conn)
        conn.commit()
        result = _st.get_issue(conn, issue_id)  # type: ignore[return-value]
    finally:
        conn.close()
    _auto_export(r)
    return result


def release(
    issue_id: str,
    *,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Release a claimed (in_progress) issue back to open/unassigned.

    Used to reclaim tasks from dead agents or re-assign work.
    Resets status to 'open' and clears assignee.
    """
    r = root or _root or Path(".")
    conn = _conn(r)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")

        ok = _st.release_issue(conn, issue_id)
        if not ok:
            raise ValueError(
                f"Issue {issue_id} is not in_progress (status={existing.status!r})"
            )

        _emit(conn, issue_id, "released", actor, {
            "previous_assignee": existing.assignee,
        })
        _rebuild_blocked_cache(conn)
        conn.commit()
        result = _st.get_issue(conn, issue_id)  # type: ignore[return-value]
    finally:
        conn.close()
    _auto_export(r)
    return result


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def ready(
    *,
    assignee: str | None = None,
    feature_slug: str | None = None,
    label: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[Issue]:
    """Get unblocked, open issues ready for work."""
    conn = _conn(root)
    try:
        return _st.ready_issues_query(
            conn,
            assignee=assignee,
            feature_slug=feature_slug,
            label=label,
            limit=limit,
        )
    finally:
        conn.close()


def list_issues(
    *,
    status: str | None = None,
    issue_type: str | None = None,
    feature_slug: str | None = None,
    parent: str | None = None,
    assignee: str | None = None,
    label: str | None = None,
    limit: int = 100,
    root: Path | None = None,
) -> list[Issue]:
    """List issues with optional filters."""
    conn = _conn(root)
    try:
        return _st.list_issues_query(
            conn,
            status=status,
            issue_type=issue_type,
            feature_slug=feature_slug,
            parent=parent,
            assignee=assignee,
            label=label,
            limit=limit,
        )
    finally:
        conn.close()


def stats(*, root: Path | None = None) -> dict:
    """Return counts: open, in_progress, closed, ready, blocked, by_type, by_feature."""
    conn = _conn(root)
    try:
        return _st.get_stats(conn)
    finally:
        conn.close()


def get_phase(
    feature_slug: str,
    *,
    root: Path | None = None,
) -> str:
    """Get current workflow phase for a feature."""
    conn = _conn(root)
    try:
        return _st.get_feature_phase(conn, feature_slug)
    finally:
        conn.close()


def set_phase(
    feature_slug: str,
    phase: str,
    *,
    root: Path | None = None,
) -> int:
    """Set workflow phase for all issues in a feature.

    Returns number of updated rows.
    """
    r = root or _root or Path(".")
    def _do_set() -> int:
        conn = _conn(r)
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = _st.set_feature_phase(conn, feature_slug, phase)
            conn.commit()
            return count
        finally:
            conn.close()

    count = _with_retry(_do_set)
    _auto_export(r)
    return count


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def dep_add(
    issue_id: str,
    depends_on: str,
    *,
    dep_type: str = "blocks",
    actor: str = "claude",
    root: Path | None = None,
) -> None:
    """Add dependency. Raises on cycle detection."""
    r = root or _root or Path(".")
    conn = _conn(r)
    try:
        # Validate both issues exist
        if not _st.id_exists(conn, issue_id):
            raise ValueError(f"Issue {issue_id} not found")
        if not _st.id_exists(conn, depends_on):
            raise ValueError(f"Issue {depends_on} not found")

        # Cycle detection
        if _would_create_cycle(conn, issue_id, depends_on):
            raise ValueError(
                f"Adding {issue_id} → {depends_on} would create a cycle"
            )

        dep = Dependency(
            issue_id=issue_id,
            depends_on_id=depends_on,
            dep_type=dep_type,
            created_at=_st._now(),
        )
        _st.insert_dependency(conn, dep)

        _emit(conn, issue_id, "dep_added", actor, {
            "depends_on": depends_on,
            "dep_type": dep_type,
        })

        _rebuild_blocked_cache(conn)
        conn.commit()
    finally:
        conn.close()
    _auto_export(r)


def dep_remove(
    issue_id: str,
    depends_on: str,
    *,
    actor: str = "claude",
    root: Path | None = None,
) -> None:
    """Remove dependency. Rebuilds blocked cache."""
    r = root or _root or Path(".")
    conn = _conn(r)
    try:
        ok = _st.remove_dependency(conn, issue_id, depends_on)
        if ok:
            _emit(conn, issue_id, "dep_removed", actor, {
                "depends_on": depends_on,
            })
            _rebuild_blocked_cache(conn)
        conn.commit()
    finally:
        conn.close()
    _auto_export(r)


def blockers(
    issue_id: str,
    *,
    root: Path | None = None,
) -> list[Issue]:
    """Get issues blocking this one."""
    conn = _conn(root)
    try:
        return _st.get_blocked_by(conn, issue_id)
    finally:
        conn.close()


def blocks(
    issue_id: str,
    *,
    root: Path | None = None,
) -> list[Issue]:
    """Get issues this one blocks."""
    conn = _conn(root)
    try:
        return _st.get_blocks(conn, issue_id)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Blocked Cache & Cycle Detection (inline — Phase 2 adds graph.py)
# ---------------------------------------------------------------------------

def _try_auto_close_parent(conn, issue_id: str, actor: str) -> None:
    """Auto-close a parent epic when all its children are closed.

    Finds the parent via parent-child dependency, checks if all siblings
    are closed, and if so closes the parent with reason 'completed'.
    """
    # Find parent via parent-child dependency
    rows = conn.execute(
        """SELECT depends_on_id FROM dependencies
           WHERE issue_id = ? AND dep_type = 'parent-child'""",
        (issue_id,),
    ).fetchall()
    if not rows:
        return

    parent_id = rows[0]["depends_on_id"]
    parent = _st.get_issue(conn, parent_id)
    if parent is None or parent.status == "closed":
        return

    # Check if all children of this parent are now closed
    children = conn.execute(
        """SELECT i.status FROM issues i
           JOIN dependencies d ON i.id = d.issue_id
           WHERE d.depends_on_id = ? AND d.dep_type = 'parent-child'""",
        (parent_id,),
    ).fetchall()

    if not children:
        return

    all_closed = all(c["status"] == "closed" for c in children)
    if all_closed:
        _st.close_issue(conn, parent_id, "completed")
        _emit(conn, parent_id, "closed", actor, {
            "reason": "completed",
            "comment": "Auto-closed: all children completed",
        })


_CYCLE_MAX_ITERATIONS = 10_000


def _would_create_cycle(conn, issue_id: str, depends_on_id: str) -> bool:
    """Check if adding issue_id -> depends_on_id would create a cycle.

    DFS from depends_on_id following outgoing edges. If we reach issue_id,
    a cycle would form. Bounded to _CYCLE_MAX_ITERATIONS to prevent DoS
    on pathologically large graphs.
    """
    visited: set[str] = set()
    stack = [depends_on_id]
    iterations = 0
    while stack:
        iterations += 1
        if iterations > _CYCLE_MAX_ITERATIONS:
            raise ValueError(
                f"Cycle detection exceeded {_CYCLE_MAX_ITERATIONS} iterations"
            )
        current = stack.pop()
        if current == issue_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        rows = conn.execute(
            "SELECT depends_on_id FROM dependencies WHERE issue_id = ?",
            (current,),
        ).fetchall()
        for row in rows:
            stack.append(row["depends_on_id"])
    return False


# ---------------------------------------------------------------------------
# Sync (stubs — Phase 3 adds sync.py / context.py)
# ---------------------------------------------------------------------------

def export_jsonl(root: Path) -> Path:
    """Export SQLite -> .cnogo/issues.jsonl. Returns path."""
    from .sync import export_jsonl as _export
    return _export(root)


def import_jsonl(root: Path) -> int:
    """Import .cnogo/issues.jsonl -> SQLite. Returns count imported."""
    from .sync import import_jsonl as _import
    return _import(root)


def sync(root: Path) -> None:
    """Full sync: export, git add, commit if changes."""
    from .sync import sync as _sync
    _sync(root)


def prime(
    *,
    limit: int = 10,
    verbose: bool = False,
    root: Path | None = None,
) -> str:
    """Generate minimal context summary for agent injection."""
    from .context import prime as _prime
    return _prime(limit=limit, verbose=verbose, root=root)


def checkpoint(
    *,
    feature_slug: str | None = None,
    limit: int = 3,
    root: Path | None = None,
) -> str:
    """Generate a compact progress checkpoint."""
    from .context import checkpoint as _checkpoint
    return _checkpoint(feature_slug=feature_slug, limit=limit, root=root)


def history(
    issue_id: str,
    *,
    limit: int = 10,
    root: Path | None = None,
) -> str:
    """Render event history for an issue."""
    from .context import history as _history
    return _history(issue_id, limit=limit, root=root)


def show_graph(feature_slug: str, *, root: Path | None = None) -> str:
    """Render ASCII dependency graph for a feature."""
    from .context import show_graph as _show_graph
    return _show_graph(feature_slug, root=root)


# ---------------------------------------------------------------------------
# Bridge (Agent Teams integration)
# ---------------------------------------------------------------------------

def plan_to_task_descriptions(
    plan_json_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Read an NN-PLAN.json and generate task descriptions for agent teammates."""
    from .bridge import plan_to_task_descriptions as _bridge
    return _bridge(plan_json_path, root)


def generate_implement_prompt(
    *,
    task_name: str,
    action: str,
    files: list[str],
    verify: list[str],
    memory_id: str = "",
) -> str:
    """Generate the full agent prompt for an implementer teammate."""
    from .bridge import generate_implement_prompt as _gen
    return _gen(
        task_name=task_name,
        action=action,
        files=files,
        verify=verify,
        memory_id=memory_id,
    )


def detect_file_conflicts(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check for file overlaps that may produce merge conflicts (advisory).

    Returns a list of conflict dicts: [{file, tasks, severity}].
    Severity is always "advisory" — worktree isolation prevents runtime
    interference, and the resolver agent handles merge conflicts at merge time.
    Empty list = no overlaps detected.
    """
    from .bridge import detect_file_conflicts as _detect
    return _detect(tasks)


# ---------------------------------------------------------------------------
# Worktree (parallel agent isolation)
# ---------------------------------------------------------------------------

def create_session(
    plan_json_path: Path,
    root: Path,
    task_descriptions: list[dict[str, Any]],
) -> Any:
    """Create worktrees for parallel agent execution."""
    from .worktree import create_session as _create
    return _create(plan_json_path, root, task_descriptions)


def merge_session(session: Any, root: Path) -> Any:
    """Merge agent branches sequentially in task order."""
    from .worktree import merge_session as _merge
    return _merge(session, root)


def cleanup_session(session: Any, root: Path) -> None:
    """Remove all worktrees, delete branches, and remove state file."""
    from .worktree import cleanup_session as _cleanup
    _cleanup(session, root)


def get_conflict_context(
    session: Any,
    task_index: int,
    plan_json_path: Path,
    root: Path,
) -> dict[str, Any]:
    """Build context dict for the resolver agent."""
    from .worktree import get_conflict_context as _ctx
    return _ctx(session, task_index, plan_json_path, root)


def load_session(root: Path) -> Any:
    """Read and deserialize worktree session state. Returns None if no file."""
    from .worktree import load_session as _load
    return _load(root)


def save_session(session: Any, root: Path) -> None:
    """Serialize worktree session to JSON, write atomically."""
    from .worktree import save_session as _save
    _save(session, root)
