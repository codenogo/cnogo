#!/usr/bin/env python3
"""Public memory API wrappers with repo-root resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..workflow.orchestration import (
    DELIVERY_INTEGRATION_STATUSES,
    DELIVERY_REVIEW_READINESS_STATUSES,
    DELIVERY_REVIEW_STAGE_STATUSES,
    DELIVERY_REVIEW_STATUSES,
    DELIVERY_REVIEW_VERDICTS,
    DeliveryRun,
    complete_ship as _complete_ship_impl,
    create_delivery_run as _create_delivery_run_impl,
    ensure_run_coordination_state as _ensure_run_coordination_state_impl,
    ensure_run_review_state as _ensure_run_review_state_impl,
    ensure_run_ship_state as _ensure_run_ship_state_impl,
    ensure_delivery_run as _ensure_delivery_run_impl,
    fail_ship as _fail_ship_impl,
    latest_delivery_run as _latest_delivery_run_impl,
    list_delivery_runs as _list_delivery_runs_impl,
    load_delivery_run as _load_delivery_run_impl,
    record_plan_verification as _record_plan_verification_impl,
    refresh_task_frontier as _refresh_task_frontier_impl,
    save_delivery_run as _save_delivery_run_impl,
    set_review_stage as _set_review_stage_impl,
    set_review_verdict as _set_review_verdict_impl,
    summarize_delivery_run as _summarize_delivery_run_impl,
    sync_integration_state as _sync_integration_state_impl,
    sync_review_from_artifact as _sync_review_from_artifact_impl,
    sync_review_from_contract as _sync_review_from_contract_impl,
    sync_review_readiness as _sync_review_readiness_impl,
    sync_review_state as _sync_review_state_impl,
    sync_ship_state as _sync_ship_state_impl,
    sync_run_with_worktree_session as _sync_run_with_worktree_session_impl,
    start_review as _start_review_impl,
    start_ship as _start_ship_impl,
    update_delivery_task_status as _update_delivery_task_status_impl,
    watch_delivery_runs as _watch_delivery_runs_impl,
)
from ..workflow.orchestration.review_artifacts import (
    persist_review_artifact_from_run as _persist_review_artifact_from_run_impl,
)
from ..workflow.shared.config import agent_team_settings as _agent_team_settings_cfg
from ..workflow.shared.config import load_workflow_config as _load_workflow_config
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


def create_delivery_run(
    *,
    feature: str,
    plan_number: str,
    plan_path: Path,
    task_descriptions: list[dict[str, Any]],
    mode: str,
    run_id: str | None = None,
    started_by: str = "claude",
    branch: str = "",
    recommendation: dict[str, Any] | None = None,
    formula: dict[str, Any] | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    return _create_delivery_run_impl(
        _resolve_root(root),
        feature=feature,
        plan_number=plan_number,
        plan_path=plan_path,
        task_descriptions=task_descriptions,
        mode=mode,
        run_id=run_id,
        started_by=started_by,
        branch=branch,
        recommendation=recommendation,
        formula=formula,
    )


def ensure_delivery_run(
    *,
    feature: str,
    plan_number: str,
    plan_path: Path,
    task_descriptions: list[dict[str, Any]],
    mode: str,
    run_id: str | None = None,
    started_by: str = "claude",
    branch: str = "",
    recommendation: dict[str, Any] | None = None,
    formula: dict[str, Any] | None = None,
    resume_latest: bool = True,
    root: Path | None = None,
) -> DeliveryRun:
    return _ensure_delivery_run_impl(
        _resolve_root(root),
        feature=feature,
        plan_number=plan_number,
        plan_path=plan_path,
        task_descriptions=task_descriptions,
        mode=mode,
        run_id=run_id,
        started_by=started_by,
        branch=branch,
        recommendation=recommendation,
        formula=formula,
        resume_latest=resume_latest,
    )


def load_delivery_run(feature: str, run_id: str, *, root: Path | None = None) -> DeliveryRun | None:
    loaded = _load_delivery_run_impl(_resolve_root(root), feature, run_id)
    if loaded is not None:
        _ensure_run_coordination_state_impl(loaded)
        _ensure_run_review_state_impl(loaded)
        _ensure_run_ship_state_impl(loaded)
        _sync_review_readiness_impl(loaded)
        _sync_review_state_impl(loaded)
        _sync_ship_state_impl(loaded)
    return loaded


def latest_delivery_run(feature: str, *, root: Path | None = None) -> DeliveryRun | None:
    loaded = _latest_delivery_run_impl(_resolve_root(root), feature)
    if loaded is not None:
        _ensure_run_coordination_state_impl(loaded)
        _ensure_run_review_state_impl(loaded)
        _ensure_run_ship_state_impl(loaded)
        _sync_review_readiness_impl(loaded)
        _sync_review_state_impl(loaded)
        _sync_ship_state_impl(loaded)
    return loaded


def save_delivery_run(run: DeliveryRun, *, root: Path | None = None) -> Path:
    _ensure_run_coordination_state_impl(run)
    _ensure_run_review_state_impl(run)
    _ensure_run_ship_state_impl(run)
    _sync_review_state_impl(run)
    _sync_ship_state_impl(run)
    return _save_delivery_run_impl(run, _resolve_root(root))


def refresh_delivery_run(run: DeliveryRun, *, root: Path | None = None) -> DeliveryRun:
    refreshed = _refresh_task_frontier_impl(run)
    _save_delivery_run_impl(refreshed, _resolve_root(root))
    return refreshed


def update_delivery_task_status(
    run: DeliveryRun,
    *,
    task_index: int,
    status: str,
    assignee: str | None = None,
    branch: str | None = None,
    worktree_path: str | None = None,
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _update_delivery_task_status_impl(
        run,
        task_index=task_index,
        status=status,
        assignee=assignee,
        branch=branch,
        worktree_path=worktree_path,
        note=note,
    )
    _save_delivery_run_impl(updated, _resolve_root(root))
    return updated


def sync_delivery_run_with_session(
    run: DeliveryRun,
    session: Any,
    *,
    root: Path | None = None,
) -> DeliveryRun:
    synced = _sync_run_with_worktree_session_impl(run, session)
    _save_delivery_run_impl(synced, _resolve_root(root))
    return synced


def sync_delivery_run_integration(
    run: DeliveryRun,
    *,
    session: Any | None = None,
    merge_result: Any | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    synced = _sync_integration_state_impl(run, session=session, merge_result=merge_result)
    _save_delivery_run_impl(synced, _resolve_root(root))
    return synced


def record_delivery_run_plan_verification(
    run: DeliveryRun,
    *,
    passed: bool,
    commands: list[str] | None = None,
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _record_plan_verification_impl(run, passed=passed, commands=commands, note=note)
    _save_delivery_run_impl(updated, _resolve_root(root))
    return updated


def _save_delivery_run_with_review_artifact(run: DeliveryRun, *, root: Path | None = None) -> DeliveryRun:
    resolved_root = _resolve_root(root)
    contract, review_json_path, _ = _persist_review_artifact_from_run_impl(resolved_root, run)
    rel_path = str(review_json_path.relative_to(resolved_root))
    _sync_review_from_contract_impl(run, contract, review_path=rel_path)
    _save_delivery_run_impl(run, resolved_root)
    return run


def start_delivery_run_review(
    run: DeliveryRun,
    *,
    reviewers: list[str] | None = None,
    automated_verdict: str | None = None,
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _start_review_impl(
        run,
        reviewers=reviewers,
        automated_verdict=automated_verdict,
        note=note,
    )
    return _save_delivery_run_with_review_artifact(updated, root=root)


def update_delivery_run_review_stage(
    run: DeliveryRun,
    *,
    stage: str,
    status: str,
    findings: list[Any] | None = None,
    evidence: list[Any] | None = None,
    notes: list[str] | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _set_review_stage_impl(
        run,
        stage=stage,
        status=status,
        findings=findings,
        evidence=evidence,
        notes=notes,
    )
    return _save_delivery_run_with_review_artifact(updated, root=root)


def set_delivery_run_review_verdict(
    run: DeliveryRun,
    *,
    verdict: str,
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _set_review_verdict_impl(run, verdict=verdict, note=note)
    return _save_delivery_run_with_review_artifact(updated, root=root)


def start_delivery_run_ship(
    run: DeliveryRun,
    *,
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _start_ship_impl(run, note=note)
    _save_delivery_run_impl(updated, _resolve_root(root))
    return updated


def complete_delivery_run_ship(
    run: DeliveryRun,
    *,
    commit: str,
    branch: str = "",
    pr_url: str = "",
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _complete_ship_impl(
        run,
        commit=commit,
        branch=branch,
        pr_url=pr_url,
        note=note,
    )
    _save_delivery_run_impl(updated, _resolve_root(root))
    return updated


def fail_delivery_run_ship(
    run: DeliveryRun,
    *,
    error: str = "",
    note: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    updated = _fail_ship_impl(run, error=error, note=note)
    _save_delivery_run_impl(updated, _resolve_root(root))
    return updated


def sync_delivery_run_review(
    run: DeliveryRun,
    *,
    review_contract: dict[str, Any] | None = None,
    review_path: str | None = None,
    root: Path | None = None,
) -> DeliveryRun:
    resolved_root = _resolve_root(root)
    if review_contract is None:
        updated = _sync_review_from_artifact_impl(run, root=resolved_root)
    else:
        updated = _sync_review_from_contract_impl(
            run,
            review_contract,
            review_path=review_path or "",
        )
    _save_delivery_run_impl(updated, resolved_root)
    return updated


def list_delivery_runs(
    *,
    feature_slug: str | None = None,
    statuses: set[str] | None = None,
    mode: str | None = None,
    include_terminal: bool = False,
    root: Path | None = None,
) -> list[DeliveryRun]:
    return _list_delivery_runs_impl(
        _resolve_root(root),
        feature_filter=feature_slug,
        statuses=statuses,
        mode=mode,
        include_terminal=include_terminal,
    )


def summarize_delivery_run(
    run: DeliveryRun,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    return _summarize_delivery_run_impl(run, root=_resolve_root(root))


def watch_delivery_runs(
    *,
    feature_slug: str | None = None,
    stale_minutes: int | None = None,
    review_stale_minutes: int | None = None,
    include_terminal: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = _resolve_root(root)
    cfg = _load_workflow_config(resolved_root)
    stale_cfg = _agent_team_settings_cfg(cfg).get("staleIndicatorMinutes", 10)
    stale_threshold = stale_minutes if isinstance(stale_minutes, int) and stale_minutes > 0 else stale_cfg
    review_threshold = (
        review_stale_minutes
        if isinstance(review_stale_minutes, int) and review_stale_minutes > 0
        else max(stale_threshold * 6, 60)
    )
    return _watch_delivery_runs_impl(
        resolved_root,
        feature_filter=feature_slug,
        stale_minutes=stale_threshold,
        review_stale_minutes=review_threshold,
        include_terminal=include_terminal,
    )
