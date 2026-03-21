"""Watch and health reporting for delivery runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.profiles import profile_watch_thresholds
from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .delivery_run import (
    TERMINAL_DELIVERY_RUN_STATUSES,
    DeliveryRun,
    delivery_run_dir,
    latest_delivery_run,
    load_delivery_run,
)
from .integration import ensure_run_coordination_state, sync_review_readiness
from .review import ensure_run_review_state, sync_review_state
from .ship import ensure_run_ship_state, sync_ship_state
from .work_order import build_work_order

_RUNS_DIR = Path(".cnogo") / "runs"
_SESSION_FILE = Path(".cnogo") / "worktree-session.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _session_dict(root: Path) -> dict[str, Any] | None:
    session_path = root / _SESSION_FILE
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _iter_run_paths(root: Path, *, feature_filter: str | None = None) -> list[Path]:
    runs_root = root / _RUNS_DIR
    if not runs_root.is_dir():
        return []
    feature_dirs: list[Path]
    if feature_filter:
        feature_dir = runs_root / feature_filter
        feature_dirs = [feature_dir] if feature_dir.is_dir() else []
    else:
        feature_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir())

    run_paths: list[Path] = []
    for feature_dir in feature_dirs:
        run_paths.extend(path for path in feature_dir.glob("*.json") if path.is_file())
    run_paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return run_paths


def list_delivery_runs(
    root: Path,
    *,
    feature_filter: str | None = None,
    statuses: set[str] | None = None,
    mode: str | None = None,
    include_terminal: bool = False,
) -> list[DeliveryRun]:
    """Load delivery runs with optional feature/status/mode filtering."""
    runs: list[DeliveryRun] = []
    for run_path in _iter_run_paths(root, feature_filter=feature_filter):
        run = load_delivery_run(root, run_path.parent.name, run_path.stem)
        if run is None:
            continue
        ensure_run_coordination_state(run)
        ensure_run_review_state(run)
        ensure_run_ship_state(run)
        sync_review_readiness(run)
        sync_review_state(run)
        sync_ship_state(run)
        if not include_terminal and run.status in TERMINAL_DELIVERY_RUN_STATUSES:
            continue
        if statuses and run.status not in statuses:
            continue
        if mode and run.mode != mode:
            continue
        runs.append(run)
    runs.sort(
        key=lambda run: parse_iso_timestamp(getattr(run, "updated_at", "")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return runs


def summarize_delivery_run(
    run: DeliveryRun,
    *,
    root: Path,
    session: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a compact operator-facing summary for a single delivery run."""
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    ensure_run_ship_state(run)
    sync_review_readiness(run)
    sync_review_state(run)
    sync_ship_state(run)
    now = now or _now_utc()
    updated_at = parse_iso_timestamp(run.updated_at)
    minutes_since_update = None
    if updated_at is not None:
        minutes_since_update = round((now - updated_at).total_seconds() / 60.0, 1)

    session_linked = bool(
        session
        and session.get("feature") == run.feature
        and isinstance(session.get("runId"), str)
        and session.get("runId") == run.run_id
    )
    return {
        "runId": run.run_id,
        "feature": run.feature,
        "workOrderId": run.feature,
        "planNumber": run.plan_number,
        "mode": run.mode,
        "status": run.status,
        "profileName": str(run.profile.get("name", "")).strip() if isinstance(run.profile, dict) else "",
        "profileVersion": str(run.profile.get("version", "")).strip() if isinstance(run.profile, dict) else "",
        "formulaName": str(run.formula.get("name", "")).strip() if isinstance(run.formula, dict) else "",
        "formulaVersion": str(run.formula.get("version", "")).strip() if isinstance(run.formula, dict) else "",
        "branch": run.branch,
        "integrationStatus": run.integration.get("status", "pending"),
        "reviewReadiness": run.review_readiness.get("status", "pending"),
        "reviewStatus": run.review.get("status", "pending"),
        "reviewVerdict": run.review.get("finalVerdict", "pending"),
        "shipStatus": run.ship.get("status", "pending"),
        "shipAttempts": run.ship.get("attempts", 0),
        "shipCommit": run.ship.get("commit", ""),
        "shipPrUrl": run.ship.get("prUrl", ""),
        "planVerifyPassed": run.review_readiness.get("planVerifyPassed"),
        "updatedAt": run.updated_at,
        "minutesSinceUpdate": minutes_since_update,
        "taskCounts": _task_counts(run),
        "sessionLinked": session_linked,
        "path": str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
    }


def _task_counts(run: DeliveryRun) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in run.tasks:
        counts[task.status] = counts.get(task.status, 0) + 1
    return counts


def _finding(
    *,
    kind: str,
    severity: str,
    run: DeliveryRun | None = None,
    message: str,
    next_action: str,
    minutes_stale: float | None = None,
    path: str = "",
) -> dict[str, Any]:
    payload = {
        "kind": kind,
        "severity": severity,
        "message": message,
        "nextAction": next_action,
    }
    if run is not None:
        payload.update(
            {
                "feature": run.feature,
                "workOrderId": run.feature,
                "runId": run.run_id,
                "planNumber": run.plan_number,
                "mode": run.mode,
                "status": run.status,
                "integrationStatus": run.integration.get("status", "pending"),
                "reviewReadiness": run.review_readiness.get("status", "pending"),
                "reviewStatus": run.review.get("status", "pending"),
                "reviewVerdict": run.review.get("finalVerdict", "pending"),
                "shipStatus": run.ship.get("status", "pending"),
                "path": str(path or (delivery_run_dir(Path.cwd(), run.feature) / f"{run.run_id}.json")),
            }
        )
    elif path:
        payload["path"] = path
    if minutes_stale is not None:
        payload["minutesStale"] = minutes_stale
    return payload


def _load_review_artifact(root: Path, run: DeliveryRun) -> tuple[dict[str, Any] | None, Path | None]:
    review_path = str(getattr(run, "review_path", "") or "")
    artifact_path = ""
    if isinstance(getattr(run, "review", None), dict):
        artifact_path = str(run.review.get("artifactPath", "") or "")
    resolved = artifact_path or review_path
    if not resolved:
        return None, None
    review_file = Path(resolved)
    if not review_file.is_absolute():
        review_file = root / review_file
    if not review_file.exists():
        return None, review_file
    try:
        payload = json.loads(review_file.read_text(encoding="utf-8"))
    except Exception:
        return None, review_file
    return payload if isinstance(payload, dict) else None, review_file


def watch_delivery_runs(
    root: Path,
    *,
    feature_filter: str | None = None,
    stale_minutes: int = 10,
    review_stale_minutes: int = 60,
    include_terminal: bool = False,
) -> dict[str, Any]:
    """Produce a queue + finding view over all active delivery runs."""
    now = _now_utc()
    session = _session_dict(root)
    runs = list_delivery_runs(
        root,
        feature_filter=feature_filter,
        include_terminal=include_terminal,
    )
    findings: list[dict[str, Any]] = []
    summaries = [summarize_delivery_run(run, root=root, session=session, now=now) for run in runs]

    for run, summary in zip(runs, summaries):
        thresholds = profile_watch_thresholds(
            run.profile if isinstance(getattr(run, "profile", None), dict) else {},
            stale_minutes=stale_minutes,
            review_stale_minutes=review_stale_minutes,
        )
        run_stale_minutes = thresholds["staleMinutes"]
        run_review_stale_minutes = thresholds["reviewStaleMinutes"]
        minutes_since_update = summary.get("minutesSinceUpdate")
        integration_status = run.integration.get("status", "pending")
        review_status = run.review_readiness.get("status", "pending")
        review_state = run.review.get("status", "pending") if isinstance(getattr(run, "review", None), dict) else "pending"
        review_verdict = run.review.get("finalVerdict", "pending") if isinstance(getattr(run, "review", None), dict) else "pending"
        ship_state = run.ship.get("status", "pending") if isinstance(getattr(run, "ship", None), dict) else "pending"
        session_linked = bool(summary.get("sessionLinked"))
        review_contract, review_file = _load_review_artifact(root, run)

        if run.mode == "team" and run.status in {"active", "blocked"} and integration_status not in {"merged", "cleaned"} and not session_linked:
            findings.append(
                _finding(
                    kind="team_run_missing_session",
                    severity="warn",
                    run=run,
                    message="Active team delivery run has no linked worktree session.",
                    next_action=f"Inspect with `python3 .cnogo/scripts/workflow_memory.py run-show {run.feature} --run-id {run.run_id}` and resume `/team implement {run.feature} {run.plan_number}` if needed.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if minutes_since_update is not None and minutes_since_update >= run_stale_minutes and run.status in {"active", "blocked"}:
            findings.append(
                _finding(
                    kind="stale_active_run",
                    severity="warn",
                    run=run,
                    message=f"Delivery run has not moved for {minutes_since_update:.1f} minutes while {run.status}.",
                    next_action=f"Check `python3 .cnogo/scripts/workflow_memory.py session-status --json` and `python3 .cnogo/scripts/workflow_memory.py run-show {run.feature} --run-id {run.run_id}`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if integration_status == "awaiting_merge" and minutes_since_update is not None and minutes_since_update >= run_stale_minutes:
            findings.append(
                _finding(
                    kind="awaiting_merge_stale",
                    severity="warn",
                    run=run,
                    message=f"Integration is awaiting merge and has been idle for {minutes_since_update:.1f} minutes.",
                    next_action="Run `python3 .cnogo/scripts/workflow_memory.py session-merge` or resume team integration.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if integration_status == "conflicted":
            severity = "fail" if minutes_since_update is not None and minutes_since_update >= run_stale_minutes else "warn"
            conflict_task = run.integration.get("conflictTaskIndex")
            findings.append(
                _finding(
                    kind="integration_conflict",
                    severity=severity,
                    run=run,
                    message=f"Integration is conflicted at task {conflict_task}.",
                    next_action="Resolve the merge conflict, then rerun `python3 .cnogo/scripts/workflow_memory.py session-merge`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if review_status == "awaiting_verification" and minutes_since_update is not None and minutes_since_update >= run_stale_minutes:
            findings.append(
                _finding(
                    kind="awaiting_verification_stale",
                    severity="warn",
                    run=run,
                    message=f"Run is merged but plan verification has not been recorded for {minutes_since_update:.1f} minutes.",
                    next_action=f"Record verification with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify {run.feature} pass --run-id {run.run_id}` or `fail`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if review_status == "ready" and review_state == "ready" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="ready_for_review_stale",
                    severity="warn",
                    run=run,
                    message=f"Run has been ready for review for {minutes_since_update:.1f} minutes.",
                    next_action=f"Continue with `/review {run.feature}` or inspect `REVIEW.json` generation inputs.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if review_state == "in_progress" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="review_in_progress_stale",
                    severity="warn",
                    run=run,
                    message=f"Review has been in progress without movement for {minutes_since_update:.1f} minutes.",
                    next_action=f"Resume `/review {run.feature}` or sync latest artifact state with `python3 .cnogo/scripts/workflow_memory.py run-review-sync {run.feature} --run-id {run.run_id}`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if review_state == "completed" and review_verdict == "fail" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="review_failed_followup_stale",
                    severity="warn",
                    run=run,
                    message=f"Review failed {minutes_since_update:.1f} minutes ago and still needs follow-up implementation work.",
                    next_action=f"Address review blockers, then update the run via `python3 .cnogo/scripts/workflow_memory.py run-review-stage-set {run.feature} <stage> <status>` and `run-review-verdict`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if ship_state == "ready" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="ready_to_ship_stale",
                    severity="warn",
                    run=run,
                    message=f"Run has been ready to ship for {minutes_since_update:.1f} minutes.",
                    next_action=f"Continue with `/ship {run.feature}` or start ship tracking with `python3 .cnogo/scripts/workflow_memory.py run-ship-start {run.feature} --run-id {run.run_id}`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if ship_state == "in_progress" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="ship_in_progress_stale",
                    severity="warn",
                    run=run,
                    message=f"Ship has been in progress without movement for {minutes_since_update:.1f} minutes.",
                    next_action=f"Finish with `python3 .cnogo/scripts/workflow_memory.py run-ship-complete {run.feature} <commit>` or record failure with `run-ship-fail`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if ship_state == "failed" and minutes_since_update is not None and minutes_since_update >= run_review_stale_minutes:
            findings.append(
                _finding(
                    kind="ship_failed_stale",
                    severity="warn",
                    run=run,
                    message=f"Ship failed {minutes_since_update:.1f} minutes ago and still needs follow-up.",
                    next_action=f"Retry with `/ship {run.feature}` or restart tracking via `python3 .cnogo/scripts/workflow_memory.py run-ship-start {run.feature} --run-id {run.run_id}`.",
                    minutes_stale=minutes_since_update,
                    path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                )
            )

        if review_state in {"in_progress", "completed"}:
            if review_file is None:
                findings.append(
                    _finding(
                        kind="review_artifact_missing",
                        severity="fail" if review_state == "completed" else "warn",
                        run=run,
                        message="Delivery Run review state exists, but there is no linked REVIEW.json artifact.",
                        next_action=f"Recreate or sync review artifacts with `python3 .cnogo/scripts/workflow_memory.py run-review-sync {run.feature} --run-id {run.run_id}`.",
                        minutes_stale=minutes_since_update,
                        path=str(delivery_run_dir(root, run.feature) / f"{run.run_id}.json"),
                    )
                )
            elif review_contract is None:
                findings.append(
                    _finding(
                        kind="review_artifact_unreadable",
                        severity="fail" if review_state == "completed" else "warn",
                        run=run,
                        message="Linked REVIEW.json exists but could not be read as a JSON object.",
                        next_action=f"Repair {review_file} and re-sync the Delivery Run review state.",
                        minutes_stale=minutes_since_update,
                        path=str(review_file),
                    )
                )
            else:
                contract_verdict = str(review_contract.get("verdict", "pending"))
                contract_timestamp = str(review_contract.get("timestamp", "") or "")
                run_timestamp = str(run.review.get("artifactTimestamp", "") or "")
                if contract_verdict != str(review_verdict) or (run_timestamp and contract_timestamp != run_timestamp):
                    findings.append(
                        _finding(
                            kind="review_artifact_drift",
                            severity="fail" if review_state == "completed" else "warn",
                            run=run,
                            message="Delivery Run review state is out of sync with the linked REVIEW.json artifact.",
                            next_action=f"Sync with `python3 .cnogo/scripts/workflow_memory.py run-review-sync {run.feature} --run-id {run.run_id}` or rewrite the review artifact from the run state.",
                            minutes_stale=minutes_since_update,
                            path=str(review_file),
                        )
                    )

    if session is not None:
        session_feature = session.get("feature")
        session_run_id = session.get("runId")
        if isinstance(session_feature, str) and session_feature.strip():
            if isinstance(session_run_id, str) and session_run_id.strip():
                linked = load_delivery_run(root, session_feature.strip(), session_run_id.strip())
                if linked is None:
                    findings.append(
                        _finding(
                            kind="session_missing_run",
                            severity="fail",
                            message=(
                                "Active worktree session references a delivery run that does not exist."
                            ),
                            next_action="Recreate or relink the run before resuming team execution.",
                            path=str(root / _SESSION_FILE),
                        )
                    )
            else:
                latest = latest_delivery_run(root, session_feature.strip())
                if latest is None:
                    findings.append(
                        _finding(
                            kind="session_without_run",
                            severity="warn",
                            message="Active worktree session has no linked delivery run.",
                            next_action=f"Create or resume one with `python3 .cnogo/scripts/workflow_memory.py run-create {session_feature.strip()} <NN> --mode team`.",
                            path=str(root / _SESSION_FILE),
                        )
                    )

    severity_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "warn"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    for run in runs:
        status_counts[run.status] = status_counts.get(run.status, 0) + 1

    findings_by_feature: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        feature = str(finding.get("feature", "")).strip()
        if not feature:
            continue
        findings_by_feature.setdefault(feature, []).append(dict(finding))

    work_orders: list[dict[str, Any]] = []
    seen_features: set[str] = set()
    for run in runs:
        feature = run.feature
        if feature in seen_features:
            continue
        seen_features.add(feature)
        work_orders.append(
            build_work_order(
                root,
                feature,
                current_run=run,
                attention_items=findings_by_feature.get(feature, []),
            ).to_dict()
        )
    for feature in sorted(findings_by_feature.keys() - seen_features):
        work_orders.append(
            build_work_order(
                root,
                feature,
                attention_items=findings_by_feature.get(feature, []),
            ).to_dict()
        )

    return {
        "checkedAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "thresholds": {
            "staleMinutes": stale_minutes,
            "reviewStaleMinutes": review_stale_minutes,
        },
        "runs": summaries,
        "workOrders": work_orders,
        "findings": findings,
        "summary": {
            "totalRuns": len(runs),
            "totalWorkOrders": len(work_orders),
            "statusCounts": status_counts,
            "findingCounts": severity_counts,
            "activeSession": {
                "feature": session.get("feature"),
                "runId": session.get("runId"),
            }
            if session is not None
            else None,
        },
    }
