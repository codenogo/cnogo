"""Implementation-lifecycle helpers for delivery runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .delivery_run import DeliveryRun, refresh_task_frontier, update_delivery_task_status
from .integration import record_plan_verification
from .review import sync_review_state
from .ship import sync_ship_state

DELIVERY_NEXT_ACTION_KINDS = frozenset(
    {
        "begin_task",
        "resolve_failure",
        "merge_team_session",
        "resolve_merge_conflict",
        "run_plan_verify",
        "prepare_review",
        "start_review",
        "continue_review",
        "start_ship",
        "continue_ship",
        "blocked",
        "complete",
        "wait",
    }
)

_SERIAL_VERIFY_READY_TASKS = frozenset({"done", "verified", "merged", "skipped", "cancelled"})
_SERIAL_AUTO_MERGE_TASKS = frozenset({"done", "verified"})
_TEAM_AUTO_MERGE_TASKS = frozenset({"pending", "ready", "in_progress", "done", "verified"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ready_tasks(run: DeliveryRun) -> list[Any]:
    return [task for task in run.tasks if task.status == "ready"]


def _failed_tasks(run: DeliveryRun) -> list[Any]:
    return [task for task in run.tasks if task.status == "failed"]


def _serial_ready_for_verification(run: DeliveryRun) -> bool:
    if run.mode != "serial" or not run.tasks:
        return False
    statuses = {task.status for task in run.tasks}
    if not statuses or not statuses.issubset(_SERIAL_VERIFY_READY_TASKS):
        return False
    return run.review_readiness.get("planVerifyPassed") is None


def begin_task_execution(
    run: DeliveryRun,
    *,
    task_index: int,
    actor: str = "",
    branch: str | None = None,
    worktree_path: str | None = None,
    note: str | None = None,
) -> DeliveryRun:
    branch_value = branch
    if branch_value is None and run.mode == "serial" and getattr(run, "branch", ""):
        branch_value = run.branch
    return update_delivery_task_status(
        run,
        task_index=task_index,
        status="in_progress",
        assignee=actor or None,
        branch=branch_value,
        worktree_path=worktree_path,
        note=note,
    )


def complete_task_execution(
    run: DeliveryRun,
    *,
    task_index: int,
    actor: str = "",
    verify_commands: list[str] | None = None,
    note: str | None = None,
) -> DeliveryRun:
    note_parts = [note] if note else []
    if verify_commands:
        compact = [str(command).strip() for command in verify_commands if str(command).strip()]
        if compact:
            note_parts.append("verify: " + " | ".join(compact))
    return update_delivery_task_status(
        run,
        task_index=task_index,
        status="done",
        assignee=actor or None,
        note=" ".join(part for part in note_parts if part) or None,
    )


def fail_task_execution(
    run: DeliveryRun,
    *,
    task_index: int,
    actor: str = "",
    error: str | None = None,
    note: str | None = None,
) -> DeliveryRun:
    return update_delivery_task_status(
        run,
        task_index=task_index,
        status="failed",
        assignee=actor or None,
        note=note or error,
    )


def prepare_run_for_plan_verification(run: DeliveryRun) -> DeliveryRun:
    if run.mode == "serial":
        changed = False
        for task in run.tasks:
            if task.status in _SERIAL_AUTO_MERGE_TASKS:
                task.status = "merged"
                task.updated_at = _now_iso()
                changed = True
        if changed:
            return refresh_task_frontier(run)
    return refresh_task_frontier(run)


def record_plan_verification_for_execution(
    run: DeliveryRun,
    *,
    passed: bool,
    commands: list[str] | None = None,
    note: str | None = None,
) -> DeliveryRun:
    prepared = prepare_run_for_plan_verification(run)
    if passed and prepared.mode == "team":
        changed = False
        for task in prepared.tasks:
            if task.status in _TEAM_AUTO_MERGE_TASKS:
                task.status = "merged"
                task.updated_at = _now_iso()
                changed = True
        if changed:
            prepared = refresh_task_frontier(prepared)
    return record_plan_verification(
        prepared,
        passed=passed,
        commands=commands,
        note=note,
    )


def next_delivery_run_action(run: DeliveryRun) -> dict[str, Any]:
    refresh_task_frontier(run)
    ready_tasks = _ready_tasks(run)
    if ready_tasks:
        first = ready_tasks[0]
        return {
            "kind": "begin_task",
            "reason": "Ready task frontier is available.",
            "taskIndices": [task.task_index for task in ready_tasks],
            "taskIndex": first.task_index,
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-task-begin {run.feature} {first.task_index} --run-id {run.run_id}"
            ),
        }

    failed_tasks = _failed_tasks(run)
    if failed_tasks:
        first = failed_tasks[0]
        return {
            "kind": "resolve_failure",
            "reason": "One or more tasks are failed and need intervention before execution can continue.",
            "taskIndices": [task.task_index for task in failed_tasks],
            "taskIndex": first.task_index,
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-task-begin {run.feature} {first.task_index} --run-id {run.run_id}"
            ),
        }

    integration_status = str(run.integration.get("status", "pending"))
    review_readiness = str(run.review_readiness.get("status", "pending"))
    review_status = str(run.review.get("status", "pending"))
    ship_status = str(run.ship.get("status", "pending"))

    if run.mode == "team":
        if integration_status == "conflicted":
            return {
                "kind": "resolve_merge_conflict",
                "reason": "Team execution is blocked on an integration conflict.",
                "command": "python3 .cnogo/scripts/workflow_memory.py session-status --json",
            }
        if integration_status in {"awaiting_merge", "merging"}:
            return {
                "kind": "merge_team_session",
                "reason": "Completed team tasks need leader-owned integration before verification.",
                "command": "python3 .cnogo/scripts/workflow_memory.py session-apply --json",
            }

    if _serial_ready_for_verification(run) or review_readiness == "awaiting_verification":
        return {
            "kind": "run_plan_verify",
            "reason": "Implementation is complete; plan verification is the next gate.",
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-plan-verify {run.feature} pass --run-id {run.run_id}"
            ),
        }

    if (
        run.review_readiness.get("planVerifyPassed") is True
        and review_readiness == "pending"
        and integration_status in {"pending", "awaiting_merge", "merging"}
    ):
        return {
            "kind": "prepare_review",
            "reason": "Plan verification passed; finalize integration state before review starts.",
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-review-ready {run.feature} --run-id {run.run_id}"
            ),
        }

    if review_readiness == "ready":
        if review_status in {"pending", "ready"}:
            return {
                "kind": "start_review",
                "reason": "Plan verification passed and the run is ready for review.",
                "command": f"/review {run.feature}",
            }
        if review_status == "in_progress":
            return {
                "kind": "continue_review",
                "reason": "Review is already in progress for this run.",
                "command": (
                    "python3 .cnogo/scripts/workflow_memory.py "
                    f"run-show {run.feature} --run-id {run.run_id} --json"
                ),
            }

    if ship_status == "ready":
        return {
            "kind": "start_ship",
            "reason": "Review is complete and the run is ready to ship.",
            "command": f"/ship {run.feature}",
        }
    if ship_status == "in_progress":
        return {
            "kind": "continue_ship",
            "reason": "Ship is already in progress for this run.",
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-show {run.feature} --run-id {run.run_id} --json"
            ),
        }

    if ship_status == "completed" or run.status == "completed":
        return {
            "kind": "complete",
            "reason": "Delivery Run lifecycle is complete.",
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-show {run.feature} --run-id {run.run_id} --json"
            ),
        }

    if run.status in {"blocked", "failed"}:
        return {
            "kind": "blocked",
            "reason": "The run is blocked and needs manual intervention.",
            "command": (
                "python3 .cnogo/scripts/workflow_memory.py "
                f"run-show {run.feature} --run-id {run.run_id} --json"
            ),
        }

    return {
        "kind": "wait",
        "reason": "No ready task or lifecycle transition is available yet.",
        "command": (
            "python3 .cnogo/scripts/workflow_memory.py "
            f"run-show {run.feature} --run-id {run.run_id} --json"
        ),
    }
