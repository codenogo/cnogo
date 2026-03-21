"""Review lifecycle state for delivery runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DELIVERY_REVIEW_STATUSES = frozenset(
    {
        "pending",
        "ready",
        "in_progress",
        "completed",
        "blocked",
    }
)

DELIVERY_REVIEW_STAGE_STATUSES = frozenset({"pending", "pass", "warn", "fail"})
DELIVERY_REVIEW_VERDICTS = frozenset({"pending", "pass", "warn", "fail"})
DELIVERY_REVIEW_STAGES = ("spec-compliance", "code-quality")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str) and str(value).strip()]


def _default_stage(stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "status": "pending",
        "findings": [],
        "evidence": [],
        "notes": [],
        "updatedAt": _now_iso(),
    }


def _normalize_stage(stage_name: str, payload: Any) -> dict[str, Any]:
    stage = _default_stage(stage_name)
    if not isinstance(payload, dict):
        return stage
    status = payload.get("status")
    if status in DELIVERY_REVIEW_STAGE_STATUSES:
        stage["status"] = status
    findings = payload.get("findings")
    if isinstance(findings, list):
        stage["findings"] = findings
    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        stage["evidence"] = evidence
    notes = payload.get("notes")
    if isinstance(notes, str) and notes.strip():
        stage["notes"] = [notes.strip()]
    elif isinstance(notes, list):
        stage["notes"] = _as_str_list(notes)
    updated_at = payload.get("updatedAt")
    if isinstance(updated_at, str) and updated_at.strip():
        stage["updatedAt"] = updated_at
    return stage


def ensure_run_review_state(run: Any) -> Any:
    review = run.review if isinstance(getattr(run, "review", None), dict) else {}
    normalized_stages: list[dict[str, Any]] = []
    existing_by_stage: dict[str, Any] = {}
    for item in review.get("stages", []) if isinstance(review.get("stages"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("stage"), str):
            existing_by_stage[item["stage"]] = item
    for stage_name in DELIVERY_REVIEW_STAGES:
        normalized_stages.append(_normalize_stage(stage_name, existing_by_stage.get(stage_name)))

    automated_verdict = review.get("automatedVerdict", "pending")
    if automated_verdict not in DELIVERY_REVIEW_VERDICTS:
        automated_verdict = "pending"
    final_verdict = review.get("finalVerdict", "pending")
    if final_verdict not in DELIVERY_REVIEW_VERDICTS:
        final_verdict = "pending"
    status = review.get("status", "pending")
    if status not in DELIVERY_REVIEW_STATUSES:
        status = "pending"

    run.review = {
        "status": status,
        "reviewers": _as_str_list(review.get("reviewers")),
        "automatedVerdict": automated_verdict,
        "finalVerdict": final_verdict,
        "stages": normalized_stages,
        "reviewStartedAt": str(review.get("reviewStartedAt", "")),
        "reviewCompletedAt": str(review.get("reviewCompletedAt", "")),
        "artifactTimestamp": str(review.get("artifactTimestamp", "")),
        "artifactUpdatedAt": str(review.get("artifactUpdatedAt", "")),
        "artifactPath": str(review.get("artifactPath", "")),
        "syncedAt": str(review.get("syncedAt", "")),
        "notes": _as_str_list(review.get("notes")),
        "updatedAt": str(review.get("updatedAt", _now_iso())),
    }
    return run


def _stage_complete(stage: dict[str, Any]) -> bool:
    return stage.get("status") in {"pass", "warn", "fail"}


def sync_review_state(run: Any) -> Any:
    ensure_run_review_state(run)

    review_readiness = (
        run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    )
    readiness_status = str(review_readiness.get("status", "pending"))
    stages = run.review.get("stages", [])
    if not isinstance(stages, list):
        stages = []
    any_started = bool(run.review.get("reviewStartedAt"))
    any_started = any_started or any(
        isinstance(stage, dict)
        and (
            stage.get("status") != "pending"
            or bool(stage.get("findings"))
            or bool(stage.get("evidence"))
            or bool(stage.get("notes"))
        )
        for stage in stages
    )
    any_started = any_started or bool(run.review.get("artifactTimestamp"))
    any_started = any_started or (
        run.review.get("automatedVerdict") in {"pass", "warn", "fail"}
        or bool(run.review.get("reviewers"))
    )

    final_verdict = run.review.get("finalVerdict", "pending")
    stages_complete = bool(stages) and all(
        isinstance(stage, dict) and _stage_complete(stage) for stage in stages
    )

    if final_verdict in {"pass", "warn", "fail"} and stages_complete:
        status = "completed"
        if not run.review.get("reviewCompletedAt"):
            run.review["reviewCompletedAt"] = _now_iso()
    elif readiness_status in {"blocked", "failed"}:
        status = "blocked"
    elif any_started:
        status = "in_progress"
    elif readiness_status == "ready":
        status = "ready"
    else:
        status = "pending"

    if any_started and not run.review.get("reviewStartedAt"):
        run.review["reviewStartedAt"] = _now_iso()

    run.review["status"] = status
    run.review["updatedAt"] = _now_iso()
    return run


def start_review(
    run: Any,
    *,
    reviewers: list[str] | None = None,
    automated_verdict: str | None = None,
    note: str | None = None,
) -> Any:
    ensure_run_review_state(run)
    if reviewers:
        existing = list(run.review.get("reviewers", []))
        seen = {value for value in existing if isinstance(value, str)}
        for reviewer in reviewers:
            if isinstance(reviewer, str) and reviewer.strip() and reviewer.strip() not in seen:
                existing.append(reviewer.strip())
                seen.add(reviewer.strip())
        run.review["reviewers"] = existing
    if automated_verdict in DELIVERY_REVIEW_VERDICTS:
        run.review["automatedVerdict"] = automated_verdict
    if note:
        run.review.setdefault("notes", []).append(note)
    if not run.review.get("reviewStartedAt"):
        run.review["reviewStartedAt"] = _now_iso()
    return sync_review_state(run)


def set_review_stage(
    run: Any,
    *,
    stage: str,
    status: str,
    findings: list[Any] | None = None,
    evidence: list[Any] | None = None,
    notes: list[str] | None = None,
) -> Any:
    if stage not in DELIVERY_REVIEW_STAGES:
        raise ValueError(f"Unsupported review stage: {stage!r}")
    if status not in DELIVERY_REVIEW_STAGE_STATUSES:
        raise ValueError(f"Unsupported review stage status: {status!r}")
    ensure_run_review_state(run)
    for stage_entry in run.review.get("stages", []):
        if stage_entry.get("stage") != stage:
            continue
        stage_entry["status"] = status
        if findings is not None:
            stage_entry["findings"] = findings
        if evidence is not None:
            stage_entry["evidence"] = evidence
        if notes is not None:
            stage_entry["notes"] = [note for note in notes if isinstance(note, str) and note.strip()]
        stage_entry["updatedAt"] = _now_iso()
        break
    return sync_review_state(run)


def set_review_verdict(
    run: Any,
    *,
    verdict: str,
    note: str | None = None,
) -> Any:
    if verdict not in DELIVERY_REVIEW_VERDICTS:
        raise ValueError(f"Unsupported review verdict: {verdict!r}")
    ensure_run_review_state(run)
    run.review["finalVerdict"] = verdict
    if note:
        run.review.setdefault("notes", []).append(note)
    if verdict == "pending":
        run.review["reviewCompletedAt"] = ""
    return sync_review_state(run)


def sync_review_from_contract(
    run: Any,
    review_contract: dict[str, Any],
    *,
    review_path: str = "",
) -> Any:
    ensure_run_review_state(run)
    timestamp = review_contract.get("timestamp")
    verdict = review_contract.get("verdict")
    automated_verdict = review_contract.get("automatedVerdict")
    reviewers = review_contract.get("reviewers")
    stage_reviews = review_contract.get("stageReviews")

    if isinstance(timestamp, str) and timestamp.strip():
        run.review["artifactTimestamp"] = timestamp
        run.review["artifactUpdatedAt"] = timestamp
    if isinstance(review_path, str) and review_path.strip():
        run.review["artifactPath"] = review_path
    if automated_verdict in DELIVERY_REVIEW_VERDICTS:
        run.review["automatedVerdict"] = automated_verdict
    if verdict in DELIVERY_REVIEW_VERDICTS:
        run.review["finalVerdict"] = verdict
    if isinstance(reviewers, list):
        run.review["reviewers"] = _as_str_list(reviewers)
    if isinstance(stage_reviews, list):
        by_stage = {
            item.get("stage"): item
            for item in stage_reviews
            if isinstance(item, dict) and isinstance(item.get("stage"), str)
        }
        run.review["stages"] = [
            _normalize_stage(stage_name, by_stage.get(stage_name))
            for stage_name in DELIVERY_REVIEW_STAGES
        ]
    if not run.review.get("reviewStartedAt") and isinstance(timestamp, str) and timestamp.strip():
        run.review["reviewStartedAt"] = timestamp
    run.review["syncedAt"] = _now_iso()
    return sync_review_state(run)


def sync_review_from_artifact(run: Any, *, root: Path) -> Any:
    review_path = str(getattr(run, "review_path", "") or "")
    if not review_path:
        raise ValueError(f"Run {getattr(run, 'run_id', '')} does not have a review_path")
    review_file = Path(review_path)
    if not review_file.is_absolute():
        review_file = root / review_file
    if not review_file.exists():
        raise FileNotFoundError(f"Review contract not found: {review_file}")
    raw = json.loads(review_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Review contract at {review_file} must be a JSON object")
    return sync_review_from_contract(run, raw, review_path=str(review_file.relative_to(root)))
