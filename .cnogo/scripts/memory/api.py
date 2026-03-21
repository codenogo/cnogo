#!/usr/bin/env python3
"""Public memory API wrappers with repo-root resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import bootstrap as _bootstrap_api
from . import cost_tracking as _cost_tracking_api
from . import creation as _creation_api
from . import dependencies as _dependencies_api
from . import issues as _issues_api
from . import lifecycle as _lifecycle_api
from . import phases as _phases_api
from . import queries as _queries_api
from . import runtime as _runtime
from .models import Issue

_root: Path | None = None


def _resolve_root(root: Path | None = None) -> Path:
    return root or _root or Path(".")


def _db_path(root: Path | None = None) -> Path:
    return _runtime.db_path(_resolve_root(root))


def _conn(root: Path | None = None):  # noqa: ANN202
    """Get a connection to the memory database."""
    return _runtime.conn(_resolve_root(root))


def _emit(
    conn,
    issue_id: str,
    event_type: str,
    actor: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Record an event in the audit trail."""
    _runtime.emit(conn, issue_id, event_type, actor, data)


def _auto_export(root: Path) -> None:
    """Best-effort JSONL export after state-changing operations."""
    _runtime.auto_export(root)


def init(root: Path) -> None:
    """Initialize .cnogo/ directory with memory.db schema."""
    global _root
    _root = root
    _bootstrap_api.init_memory(root)


def is_initialized(root: Path | None = None) -> bool:
    """Check if memory engine is set up in this project."""
    return _bootstrap_api.is_initialized(_resolve_root(root))


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
    owner_actor: str = "",
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Create a new issue. Returns Issue with generated ID."""
    return _creation_api.create_issue(
        _resolve_root(root),
        title,
        issue_type=issue_type,
        parent=parent,
        feature_slug=feature_slug,
        plan_number=plan_number,
        phase=phase,
        priority=priority,
        labels=labels,
        description=description,
        metadata=metadata,
        owner_actor=owner_actor,
        actor=actor,
    )


def show(issue_id: str, *, root: Path | None = None) -> Issue | None:
    """Get full issue details including deps, labels, and recent events."""
    return _issues_api.show_issue(_resolve_root(root), issue_id)


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
    """Update issue fields. Emits 'updated' event."""
    return _issues_api.update_issue(
        _resolve_root(root),
        issue_id,
        title=title,
        description=description,
        priority=priority,
        assignee=assignee,
        metadata=metadata,
        comment=comment,
        actor=actor,
    )


def claim(
    issue_id: str,
    *,
    actor: str,
    root: Path | None = None,
) -> Issue:
    """Atomic claim: sets assignee + in_progress."""
    return _issues_api.claim_issue(_resolve_root(root), issue_id, actor=actor)


def _validate_transition(
    issue: Issue,
    from_state: str,
    to_state: str,
    actor_role: str,
) -> None:
    _lifecycle_api.validate_transition(issue, from_state, to_state, actor_role)


def report_done(
    issue_id: str,
    *,
    outputs: dict | None = None,
    actor: str,
    actor_role: str = "worker",
    root: Path | None = None,
) -> Issue:
    """Worker reports task completion. Sets state to 'done_by_worker'."""
    return _lifecycle_api.report_done_issue(
        _resolve_root(root),
        issue_id,
        outputs=outputs,
        actor=actor,
        actor_role=actor_role,
    )


def verify_and_close(
    issue_id: str,
    *,
    reason: str = "completed",
    comment: str | None = None,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Leader verifies and closes a task."""
    return _lifecycle_api.verify_and_close_issue(
        _resolve_root(root),
        issue_id,
        reason=reason,
        comment=comment,
        actor=actor,
    )


def close(
    issue_id: str,
    *,
    reason: str = "completed",
    comment: str | None = None,
    actor: str = "claude",
    actor_role: str = "leader",
    root: Path | None = None,
) -> Issue:
    """Close an issue."""
    return _lifecycle_api.close_issue(
        _resolve_root(root),
        issue_id,
        reason=reason,
        comment=comment,
        actor=actor,
        actor_role=actor_role,
    )


def reopen(
    issue_id: str,
    *,
    actor: str = "claude",
    root: Path | None = None,
) -> Issue:
    """Reopen a closed issue."""
    return _lifecycle_api.reopen_issue(_resolve_root(root), issue_id, actor=actor)


def release(
    issue_id: str,
    *,
    actor: str = "claude",
    actor_role: str = "leader",
    root: Path | None = None,
) -> Issue:
    """Release a claimed issue back to open/unassigned."""
    return _lifecycle_api.release_issue(
        _resolve_root(root),
        issue_id,
        actor=actor,
        actor_role=actor_role,
    )


def takeover_task(
    issue_id: str,
    *,
    to_actor: str,
    reason: str,
    actor: str = "leader",
    actor_role: str = "leader",
    root: Path | None = None,
) -> dict[str, Any]:
    """Leader-only takeover of a stalled task."""
    return _lifecycle_api.takeover_issue(
        _resolve_root(root),
        issue_id,
        to_actor=to_actor,
        reason=reason,
        actor=actor,
        actor_role=actor_role,
    )


def ready(
    *,
    assignee: str | None = None,
    feature_slug: str | None = None,
    label: str | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> list[Issue]:
    """Get unblocked, open issues ready for work."""
    return _queries_api.ready_issues(
        _resolve_root(root),
        assignee=assignee,
        feature_slug=feature_slug,
        label=label,
        limit=limit,
    )


def stalled_tasks(
    *,
    feature_slug: str | None = None,
    stale_minutes: int | None = None,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    """Return in-progress tasks older than stale threshold."""
    return _queries_api.stalled_task_list(
        _resolve_root(root),
        feature_slug=feature_slug,
        stale_minutes=stale_minutes,
    )


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
    return _queries_api.list_issue_records(
        _resolve_root(root),
        status=status,
        issue_type=issue_type,
        feature_slug=feature_slug,
        parent=parent,
        assignee=assignee,
        label=label,
        limit=limit,
    )


def stats(*, root: Path | None = None) -> dict:
    """Return counts: open, in_progress, closed, ready, blocked, by_type, by_feature."""
    return _queries_api.issue_stats(_resolve_root(root))


def get_phase(
    feature_slug: str,
    *,
    root: Path | None = None,
) -> str:
    """Get current workflow phase for a feature."""
    return _phases_api.get_feature_phase(_resolve_root(root), feature_slug)


def set_phase(
    feature_slug: str,
    phase: str,
    *,
    root: Path | None = None,
) -> int:
    """Set workflow phase for all issues in a feature."""
    return _phases_api.set_feature_phase(_resolve_root(root), feature_slug, phase)


def dep_add(
    issue_id: str,
    depends_on: str,
    *,
    dep_type: str = "blocks",
    actor: str = "claude",
    root: Path | None = None,
) -> None:
    """Add dependency. Raises on cycle detection."""
    _dependencies_api.add_dependency(
        _resolve_root(root),
        issue_id,
        depends_on,
        dep_type=dep_type,
        actor=actor,
    )


def dep_remove(
    issue_id: str,
    depends_on: str,
    *,
    actor: str = "claude",
    root: Path | None = None,
) -> None:
    """Remove dependency. Rebuilds blocked cache."""
    _dependencies_api.remove_dependency(
        _resolve_root(root),
        issue_id,
        depends_on,
        actor=actor,
    )


def blockers(
    issue_id: str,
    *,
    root: Path | None = None,
) -> list[Issue]:
    """Get issues blocking this one."""
    return _dependencies_api.blockers_for(_resolve_root(root), issue_id)


def blocks(
    issue_id: str,
    *,
    root: Path | None = None,
) -> list[Issue]:
    """Get issues this one blocks."""
    return _dependencies_api.blocks_for(_resolve_root(root), issue_id)


def _would_create_cycle(conn, issue_id: str, depends_on_id: str) -> bool:
    return _dependencies_api.would_create_cycle(conn, issue_id, depends_on_id)


def record_cost_event(
    issue_id: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_tokens: int = 0,
    model: str = "",
    cost_usd: float = 0.0,
    actor: str = "claude",
    root: Path | None = None,
) -> None:
    """Record a cost_report event for an issue."""
    _cost_tracking_api.record_cost_event(
        _resolve_root(root),
        issue_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_tokens=cache_tokens,
        model=model,
        cost_usd=cost_usd,
        actor=actor,
    )


def get_cost_summary(feature_slug: str, *, root: Path | None = None) -> dict[str, Any]:
    """Aggregate cost_report events for all issues in a feature."""
    return _cost_tracking_api.get_cost_summary(_resolve_root(root), feature_slug)
