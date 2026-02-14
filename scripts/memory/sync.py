#!/usr/bin/env python3
"""JSONL sync layer for the cnogo memory engine.

Provides export (SQLite -> .cnogo/issues.jsonl) and import (JSONL -> SQLite)
for git-portable state synchronization.

Format: one JSON object per line, sorted by ID for deterministic diffs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import storage as _st
from .graph import rebuild_blocked_cache
from .models import Dependency, Event

_CNOGO_DIR = ".cnogo"
_DB_NAME = "memory.db"
_JSONL_NAME = "issues.jsonl"

# Schema validation constants (W-4)
_VALID_STATUSES = frozenset({"open", "in_progress", "closed"})
_VALID_TYPES = frozenset({
    "epic", "task", "subtask", "bug", "quick", "background",
})


def export_jsonl(root: Path) -> Path:
    """Export all issues from SQLite to .cnogo/issues.jsonl.

    Each line is a self-contained JSON object with deps, labels, and
    events inlined. Sorted by ID for stable, merge-friendly diffs.
    Returns the path to the JSONL file.
    """
    db_path = root / _CNOGO_DIR / _DB_NAME
    jsonl_path = root / _CNOGO_DIR / _JSONL_NAME

    conn = _st.connect(db_path)
    try:
        issues = _st.all_issues(conn)
        all_deps = _st.all_dependencies(conn)
        all_labels = _st.all_labels(conn)
        all_events = _st.all_events(conn)

        # Group deps by issue_id
        deps_by_issue: dict[str, list[dict[str, str]]] = {}
        for dep in all_deps:
            deps_by_issue.setdefault(dep.issue_id, []).append(dep.to_dict())

        # Group events by issue_id (B-1)
        events_by_issue: dict[str, list[dict[str, Any]]] = {}
        for event in all_events:
            events_by_issue.setdefault(event.issue_id, []).append(
                event.to_dict()
            )

        # Build JSONL lines
        lines: list[str] = []
        for issue in issues:
            d = issue.to_dict()
            # Inline deps, labels, and events
            if issue.id in deps_by_issue:
                d["deps"] = deps_by_issue[issue.id]
            if issue.id in all_labels:
                d["labels"] = all_labels[issue.id]
            if issue.id in events_by_issue:
                d["events"] = events_by_issue[issue.id]
            lines.append(json.dumps(d, separators=(",", ":")))

        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        jsonl_path.write_text("\n".join(lines) + "\n" if lines else "",
                              encoding="utf-8")
        return jsonl_path
    finally:
        conn.close()


def import_jsonl(root: Path) -> int:
    """Import .cnogo/issues.jsonl into SQLite.

    Upserts issues, recreates deps/labels/events, rebuilds blocked cache.
    Returns count of issues imported.
    """
    db_path = root / _CNOGO_DIR / _DB_NAME
    jsonl_path = root / _CNOGO_DIR / _JSONL_NAME

    if not jsonl_path.exists():
        return 0

    text = jsonl_path.read_text(encoding="utf-8").strip()
    if not text:
        return 0

    conn = _st.connect(db_path)
    _st.migrate(conn)  # ensure schema exists
    try:
        count = 0
        # First pass: import all issues (needed for FK validation on deps)
        parsed: list[tuple[int, dict[str, Any]]] = []
        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"Warning: skipping malformed JSON at line {line_num}",
                    file=sys.stderr,
                )
                continue

            # Schema validation (W-4)
            try:
                issue = _obj_to_issue(obj)
            except ValueError as e:
                print(
                    f"Warning: skipping invalid issue at line {line_num}: {e}",
                    file=sys.stderr,
                )
                continue

            _st.upsert_issue(conn, issue)
            parsed.append((line_num, obj))
            count += 1

        # Second pass: import deps, labels, events (after all issues exist)
        for line_num, obj in parsed:
            issue_id = obj.get("id", "")

            # Recreate labels
            existing_labels = _st.get_labels(conn, issue_id)
            new_labels = obj.get("labels", [])
            for lbl in new_labels:
                if lbl not in existing_labels:
                    _st.add_label(conn, issue_id, lbl)

            # Recreate deps with FK validation (W-7)
            deps = obj.get("deps", [])
            for dep_obj in deps:
                depends_on = dep_obj.get("depends_on", "")
                dep_type = dep_obj.get("type", "blocks")
                if not depends_on:
                    continue
                if not _st.id_exists(conn, depends_on):
                    print(
                        f"Warning: skipping dep {issue_id} -> {depends_on}"
                        f" (target not found)",
                        file=sys.stderr,
                    )
                    continue
                dep = Dependency(
                    issue_id=issue_id,
                    depends_on_id=depends_on,
                    dep_type=dep_type,
                    created_at=obj.get("created_at", ""),
                )
                _st.insert_dependency(conn, dep)

            # Import events if none exist locally (B-1)
            events = obj.get("events", [])
            if events:
                existing_count = conn.execute(
                    "SELECT COUNT(*) as cnt FROM events WHERE issue_id = ?",
                    (issue_id,),
                ).fetchone()["cnt"]
                if existing_count == 0:
                    for ev_obj in events:
                        ev_data = ev_obj.get("data", {})
                        if isinstance(ev_data, str):
                            try:
                                ev_data = json.loads(ev_data)
                            except (json.JSONDecodeError, TypeError):
                                ev_data = {}
                        event = Event(
                            issue_id=issue_id,
                            event_type=ev_obj.get("event_type", ""),
                            actor=ev_obj.get("actor", ""),
                            data=ev_data,
                            created_at=ev_obj.get("created_at", ""),
                        )
                        _st.insert_event(conn, event)

        rebuild_blocked_cache(conn)
        _rebuild_child_counters(conn)
        conn.commit()
        return count
    finally:
        conn.close()


def sync(root: Path) -> None:
    """Full sync: export JSONL, then git add the file."""
    jsonl_path = export_jsonl(root)

    # Stage the JSONL file for git
    try:
        subprocess.run(
            ["git", "add", "--", str(jsonl_path)],
            cwd=str(root),
            capture_output=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        pass  # Not in a git repo or git not available — that's fine


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _obj_to_issue(obj: dict[str, Any]) -> "Issue":
    """Parse a JSONL object into an Issue.

    Validates required fields and enum values (W-4).
    Raises ValueError on invalid data.
    """
    # Required fields
    issue_id = obj.get("id", "")
    title = obj.get("title", "")
    if not issue_id or not title:
        raise ValueError(f"Missing required fields: id={issue_id!r}, title={title!r}")

    # Enum validation
    status = obj.get("status", "open")
    if status not in _VALID_STATUSES:
        raise ValueError(f"Invalid status: {status!r}")

    issue_type = obj.get("issue_type", "task")
    if issue_type not in _VALID_TYPES:
        raise ValueError(f"Invalid issue_type: {issue_type!r}")

    # Range validation
    priority = obj.get("priority", 2)
    if not isinstance(priority, int) or priority < 0 or priority > 4:
        raise ValueError(f"Invalid priority: {priority!r}")

    # Metadata
    meta = obj.get("metadata", {})
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}

    from .models import Issue as _Issue
    return _Issue(
        id=issue_id,
        content_hash=obj.get("content_hash", ""),
        title=title,
        description=obj.get("description", ""),
        status=status,
        issue_type=issue_type,
        priority=priority,
        assignee=obj.get("assignee", ""),
        feature_slug=obj.get("feature_slug", ""),
        plan_number=obj.get("plan_number", ""),
        close_reason=obj.get("close_reason", ""),
        metadata=meta if isinstance(meta, dict) else {},
        created_at=obj.get("created_at", ""),
        updated_at=obj.get("updated_at", ""),
        closed_at=obj.get("closed_at", ""),
    )


def _rebuild_child_counters(conn) -> None:
    """Rebuild child_counters table from existing hierarchical IDs."""
    conn.execute("DELETE FROM child_counters")
    # Find all issues whose ID contains a dot (hierarchical)
    rows = conn.execute(
        "SELECT id FROM issues WHERE id LIKE '%.%' ORDER BY id"
    ).fetchall()
    counters: dict[str, int] = {}
    for row in rows:
        issue_id = row["id"]
        # Parent is everything before the last dot
        last_dot = issue_id.rfind(".")
        if last_dot == -1:
            continue
        parent = issue_id[:last_dot]
        try:
            child_num = int(issue_id[last_dot + 1:])
        except ValueError:
            continue
        current_max = counters.get(parent, 0)
        if child_num >= current_max:
            counters[parent] = child_num + 1

    for parent_id, next_child in counters.items():
        conn.execute(
            "INSERT OR REPLACE INTO child_counters (parent_id, next_child)"
            " VALUES (?, ?)",
            (parent_id, next_child),
        )
