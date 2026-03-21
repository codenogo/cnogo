"""Integration and review-readiness state for delivery runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .review import sync_review_state

DELIVERY_INTEGRATION_STATUSES = frozenset(
    {
        "pending",
        "awaiting_merge",
        "merging",
        "conflicted",
        "merged",
        "cleaned",
    }
)

DELIVERY_REVIEW_READINESS_STATUSES = frozenset(
    {
        "pending",
        "blocked",
        "awaiting_verification",
        "ready",
        "failed",
    }
)

_MERGED_TASK_STATUSES = frozenset({"merged"})
_AWAITING_MERGE_TASK_STATUSES = frozenset({"done", "verified"})
_ACTIVE_TASK_STATUSES = frozenset({"pending", "ready", "in_progress"})
_TASKS_REQUIRING_INTEGRATION = frozenset(
    {"ready", "in_progress", "done", "verified", "merged", "failed", "pending"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_int_list(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, int)]


def _as_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


def _session_value(session: Any, key: str, default: Any = None) -> Any:
    if session is None:
        return default
    if isinstance(session, dict):
        return session.get(key, default)
    return getattr(session, key, default)


def ensure_run_coordination_state(run: Any) -> Any:
    """Ensure integration/review state maps exist with stable additive defaults."""
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    review = (
        run.review_readiness
        if isinstance(getattr(run, "review_readiness", None), dict)
        else {}
    )

    run.integration = {
        "status": str(integration.get("status", "pending")),
        "mergedTaskIndices": _as_int_list(integration.get("mergedTaskIndices")),
        "awaitingMergeTaskIndices": _as_int_list(integration.get("awaitingMergeTaskIndices")),
        "activeTaskIndices": _as_int_list(integration.get("activeTaskIndices")),
        "conflictTaskIndex": integration.get("conflictTaskIndex")
        if isinstance(integration.get("conflictTaskIndex"), int) or integration.get("conflictTaskIndex") is None
        else None,
        "conflictFiles": _as_str_list(integration.get("conflictFiles")),
        "lastSessionPhase": str(integration.get("lastSessionPhase", "")),
        "updatedAt": str(integration.get("updatedAt", _now_iso())),
    }
    run.review_readiness = {
        "status": str(review.get("status", "pending")),
        "planVerifyPassed": review.get("planVerifyPassed")
        if isinstance(review.get("planVerifyPassed"), bool) or review.get("planVerifyPassed") is None
        else None,
        "verifiedAt": str(review.get("verifiedAt", "")),
        "verifiedCommands": _as_str_list(review.get("verifiedCommands")),
        "notes": _as_str_list(review.get("notes")),
        "updatedAt": str(review.get("updatedAt", _now_iso())),
    }
    return run


def sync_review_readiness(run: Any) -> Any:
    """Derive review-readiness from integration state plus verification evidence."""
    ensure_run_coordination_state(run)

    integration_status = run.integration.get("status", "pending")
    plan_verify_passed = run.review_readiness.get("planVerifyPassed")

    if plan_verify_passed is False:
        status = "failed"
    elif integration_status == "conflicted" or getattr(run, "status", "") == "failed":
        status = "blocked"
    elif plan_verify_passed is True and integration_status in {"merged", "cleaned"}:
        status = "ready"
    elif integration_status in {"merged", "cleaned"}:
        status = "awaiting_verification"
        run.status = "active"
    else:
        status = "pending"

    run.review_readiness["status"] = status
    run.review_readiness["updatedAt"] = _now_iso()

    if status == "ready":
        run.status = "ready_for_review"
    elif plan_verify_passed is False:
        run.status = "failed"
    return sync_review_state(run)


def sync_integration_state(
    run: Any,
    *,
    session: Any | None = None,
    merge_result: Any | None = None,
) -> Any:
    """Refresh integration state from task status, session phase, and merge results."""
    ensure_run_coordination_state(run)

    merged_task_indices = sorted(
        task.task_index for task in getattr(run, "tasks", []) if task.status in _MERGED_TASK_STATUSES
    )
    awaiting_merge_indices = sorted(
        task.task_index
        for task in getattr(run, "tasks", [])
        if task.status in _AWAITING_MERGE_TASK_STATUSES
    )
    active_task_indices = sorted(
        task.task_index
        for task in getattr(run, "tasks", [])
        if task.status in _ACTIVE_TASK_STATUSES
    )
    conflict_task_index = next(
        (task.task_index for task in getattr(run, "tasks", []) if task.status == "failed"),
        None,
    )
    conflict_files: list[str] = []

    session_phase = str(_session_value(session, "phase", "") or "")
    worktrees = _session_value(session, "worktrees", [])
    if isinstance(worktrees, list):
        for worktree in worktrees:
            status = _session_value(worktree, "status", "")
            if status != "conflict":
                continue
            if conflict_task_index is None:
                maybe_index = _session_value(worktree, "task_index", None)
                if maybe_index is None:
                    maybe_index = _session_value(worktree, "taskIndex", None)
                if isinstance(maybe_index, int):
                    conflict_task_index = maybe_index
            conflict_files.extend(_as_str_list(_session_value(worktree, "conflict_files", None)))
            conflict_files.extend(_as_str_list(_session_value(worktree, "conflictFiles", None)))

    merged_from_session = _as_int_list(_session_value(session, "merged_so_far", None))
    if not merged_from_session:
        merged_from_session = _as_int_list(_session_value(session, "mergedSoFar", None))
    if merged_from_session:
        merged_task_indices = sorted(set(merged_task_indices).union(merged_from_session))

    if merge_result is not None:
        merged_task_indices = sorted(
            set(merged_task_indices).union(_as_int_list(getattr(merge_result, "merged_indices", None)))
        )
        maybe_conflict_index = getattr(merge_result, "conflict_index", None)
        if isinstance(maybe_conflict_index, int):
            conflict_task_index = maybe_conflict_index
        conflict_files.extend(_as_str_list(getattr(merge_result, "conflict_files", None)))

    integration_candidate_tasks = [
        task for task in getattr(run, "tasks", []) if task.status in _TASKS_REQUIRING_INTEGRATION
    ]
    integration_task_count = len(integration_candidate_tasks)

    if session_phase == "cleaned":
        status = "cleaned"
    elif conflict_task_index is not None or conflict_files:
        status = "conflicted"
    elif integration_task_count and len(merged_task_indices) == integration_task_count:
        status = "merged"
    elif session_phase == "merging" or merged_task_indices:
        status = "merging"
    elif awaiting_merge_indices:
        status = "awaiting_merge"
    else:
        status = "pending"

    run.integration = {
        "status": status,
        "mergedTaskIndices": merged_task_indices,
        "awaitingMergeTaskIndices": awaiting_merge_indices,
        "activeTaskIndices": active_task_indices,
        "conflictTaskIndex": conflict_task_index,
        "conflictFiles": sorted(set(conflict_files)),
        "lastSessionPhase": session_phase,
        "updatedAt": _now_iso(),
    }
    return sync_review_readiness(run)


def record_plan_verification(
    run: Any,
    *,
    passed: bool,
    commands: list[str] | None = None,
    note: str | None = None,
) -> Any:
    """Record plan verification outcome and refresh review readiness."""
    ensure_run_coordination_state(run)
    run.review_readiness["planVerifyPassed"] = passed
    run.review_readiness["verifiedAt"] = _now_iso()
    run.review_readiness["verifiedCommands"] = [str(command) for command in (commands or []) if str(command).strip()]
    if note:
        run.review_readiness.setdefault("notes", []).append(note)
    run.review_readiness["updatedAt"] = _now_iso()
    return sync_review_readiness(run)


def prepare_review_readiness(
    run: Any,
    *,
    integration_status: str | None = None,
    note: str | None = None,
) -> Any:
    """Finalize integration state for review and recompute review readiness.

    This is the explicit public transition for branch-native or already-merged
    team work after plan verification has passed. It intentionally avoids
    relying on an active worktree session.
    """
    ensure_run_coordination_state(run)

    if run.review_readiness.get("planVerifyPassed") is not True:
        raise ValueError(
            "Review cannot be prepared until plan verification has passed."
        )

    current_status = str(run.integration.get("status", "pending"))
    if current_status == "conflicted":
        raise ValueError(
            "Review cannot be prepared while integration.status == 'conflicted'."
        )

    target_status = integration_status.strip() if isinstance(integration_status, str) else ""
    if not target_status:
        target_status = current_status
        if target_status not in {"merged", "cleaned"}:
            target_status = "cleaned"

    if target_status not in DELIVERY_INTEGRATION_STATUSES:
        raise ValueError(
            f"Unknown integration status {target_status!r}; "
            f"expected one of {sorted(DELIVERY_INTEGRATION_STATUSES)}."
        )
    if target_status not in {"merged", "cleaned"}:
        raise ValueError(
            "Review readiness requires integration.status == 'merged' or 'cleaned'."
        )

    run.integration["status"] = target_status
    if target_status == "cleaned":
        run.integration["lastSessionPhase"] = "cleaned"
    run.integration["updatedAt"] = _now_iso()

    if note:
        run.review_readiness.setdefault("notes", []).append(str(note))
    run.review_readiness["updatedAt"] = _now_iso()
    return sync_review_readiness(run)
