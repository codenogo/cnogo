"""Ship lifecycle state for delivery runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.workflow.shared.formulas import (
    formula_ship_require_pull_request,
    formula_ship_require_tracking,
)

DELIVERY_SHIP_STATUSES = frozenset(
    {
        "pending",
        "ready",
        "in_progress",
        "completed",
        "failed",
        "blocked",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str) and str(value).strip()]


def ensure_run_ship_state(run: Any) -> Any:
    ship = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    status = ship.get("status", "pending")
    if status not in DELIVERY_SHIP_STATUSES:
        status = "pending"
    attempts = ship.get("attempts", 0)
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0:
        attempts = 0
    run.ship = {
        "status": status,
        "attempts": attempts,
        "startedAt": str(ship.get("startedAt", "")),
        "completedAt": str(ship.get("completedAt", "")),
        "failedAt": str(ship.get("failedAt", "")),
        "commit": str(ship.get("commit", "")),
        "branch": str(ship.get("branch", "")),
        "prUrl": str(ship.get("prUrl", "")),
        "lastError": str(ship.get("lastError", "")),
        "notes": _as_str_list(ship.get("notes")),
        "updatedAt": str(ship.get("updatedAt", _now_iso())),
    }
    return run


def sync_ship_state(run: Any) -> Any:
    ensure_run_ship_state(run)
    review = run.review if isinstance(getattr(run, "review", None), dict) else {}
    review_readiness = (
        run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    )
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    ship = run.ship

    completed_at = str(ship.get("completedAt", "") or "")
    failed_at = str(ship.get("failedAt", "") or "")
    started_at = str(ship.get("startedAt", "") or "")
    final_verdict = str(review.get("finalVerdict", "pending"))
    review_status = str(review.get("status", "pending"))
    readiness_status = str(review_readiness.get("status", "pending"))
    integration_status = str(integration.get("status", "pending"))

    if completed_at or ship.get("status") == "completed":
        status = "completed"
        if not completed_at:
            ship["completedAt"] = _now_iso()
    elif failed_at or ship.get("status") == "failed":
        status = "failed"
        if not failed_at:
            ship["failedAt"] = _now_iso()
    elif started_at or ship.get("status") == "in_progress":
        status = "in_progress"
    elif final_verdict == "fail":
        status = "blocked"
    elif (
        review_status == "completed"
        and final_verdict in {"pass", "warn"}
        and readiness_status == "ready"
        and integration_status in {"merged", "cleaned"}
    ):
        status = "ready"
    else:
        status = "pending"

    ship["status"] = status
    ship["updatedAt"] = _now_iso()
    if status == "completed":
        run.status = "completed"
    return run


def start_ship(run: Any, *, note: str | None = None) -> Any:
    sync_ship_state(run)
    status = str(run.ship.get("status", "pending"))
    if status not in {"ready", "failed", "in_progress"}:
        raise ValueError(f"Ship cannot start from status {status!r}")
    if status != "in_progress":
        run.ship["attempts"] = int(run.ship.get("attempts", 0)) + 1
        run.ship["startedAt"] = _now_iso()
    run.ship["completedAt"] = ""
    run.ship["failedAt"] = ""
    run.ship["lastError"] = ""
    if note:
        run.ship.setdefault("notes", []).append(note)
    run.ship["status"] = "in_progress"
    run.ship["updatedAt"] = _now_iso()
    return sync_ship_state(run)


def complete_ship(
    run: Any,
    *,
    commit: str,
    branch: str = "",
    pr_url: str = "",
    note: str | None = None,
) -> Any:
    sync_ship_state(run)
    status = str(run.ship.get("status", "pending"))
    if status not in {"ready", "in_progress", "failed", "completed"}:
        raise ValueError(f"Ship cannot complete from status {status!r}")
    run_formula = run.formula if isinstance(getattr(run, "formula", None), dict) else {}
    if formula_ship_require_tracking(run_formula) and not str(branch).strip():
        raise ValueError("Ship completion requires a tracked branch for this formula.")
    if formula_ship_require_pull_request(run_formula) and not str(pr_url).strip():
        raise ValueError("Ship completion requires a PR URL for this formula.")
    if status != "completed" and not run.ship.get("startedAt"):
        run.ship["attempts"] = int(run.ship.get("attempts", 0)) + 1
        run.ship["startedAt"] = _now_iso()
    run.ship["status"] = "completed"
    run.ship["commit"] = str(commit).strip()
    if branch:
        run.ship["branch"] = str(branch).strip()
    if pr_url:
        run.ship["prUrl"] = str(pr_url).strip()
    run.ship["completedAt"] = _now_iso()
    run.ship["failedAt"] = ""
    run.ship["lastError"] = ""
    if note:
        run.ship.setdefault("notes", []).append(note)
    run.ship["updatedAt"] = _now_iso()
    return sync_ship_state(run)


def fail_ship(run: Any, *, error: str = "", note: str | None = None) -> Any:
    sync_ship_state(run)
    status = str(run.ship.get("status", "pending"))
    if status not in {"ready", "in_progress", "failed"}:
        raise ValueError(f"Ship cannot fail from status {status!r}")
    if not run.ship.get("startedAt"):
        run.ship["attempts"] = int(run.ship.get("attempts", 0)) + 1
        run.ship["startedAt"] = _now_iso()
    run.ship["status"] = "failed"
    run.ship["failedAt"] = _now_iso()
    run.ship["completedAt"] = ""
    run.ship["lastError"] = str(error).strip()
    if note:
        run.ship.setdefault("notes", []).append(note)
    run.ship["updatedAt"] = _now_iso()
    return sync_ship_state(run)
