"""Review artifact read/write helpers shared by checks and orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from workflow_render import render_review
    from workflow_utils import load_json, write_json
except ModuleNotFoundError:
    from ...workflow_render import render_review  # type: ignore
    from ...workflow_utils import load_json, write_json  # type: ignore

from .review import DELIVERY_REVIEW_STAGES


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_review_artifact_paths(
    root: Path,
    *,
    feature: str,
    review_path: str = "",
) -> tuple[Path, Path]:
    review_json = root / review_path if review_path else root / "docs" / "planning" / "work" / "features" / feature / "REVIEW.json"
    review_md = review_json.with_suffix(".md")
    return review_json, review_md


def load_review_contract(
    root: Path,
    *,
    feature: str,
    review_path: str = "",
    load_json_fn: Callable[[Path], Any] = load_json,
) -> tuple[dict[str, Any] | None, Path, Path]:
    review_json, review_md = resolve_review_artifact_paths(root, feature=feature, review_path=review_path)
    if not review_json.exists():
        return None, review_json, review_md
    payload = load_json_fn(review_json)
    if not isinstance(payload, dict):
        raise ValueError(f"Review contract at {review_json} must be a JSON object")
    return payload, review_json, review_md


def default_review_contract(*, feature: str, branch: str = "", timestamp: str | None = None) -> dict[str, Any]:
    ts = timestamp or _now_iso()
    return {
        "schemaVersion": 4,
        "timestamp": ts,
        "feature": feature,
        "branch": branch,
        "automated": [
            {"name": "lint", "result": "skipped"},
            {"name": "types", "result": "skipped"},
            {"name": "tests", "result": "skipped"},
        ],
        "packages": [],
        "invariants": {"summary": {"pass": 0, "warn": 0, "fail": 0}, "findings": []},
        "tokenTelemetry": {"checksRun": 0, "savedTokens": 0, "savingsPct": 0.0},
        "impactAnalysis": {"enabled": False},
        "reviewers": [],
        "securityFindings": [],
        "performanceFindings": [],
        "patternCompliance": [],
        "stageReviews": [
            {
                "stage": "spec-compliance",
                "status": "pending",
                "findings": [],
                "evidence": [],
                "notes": "",
            },
            {
                "stage": "code-quality",
                "status": "pending",
                "findings": [],
                "evidence": [],
                "notes": "",
            },
        ],
        "principleNotes": [],
        "automatedVerdict": "pending",
        "verdict": "pending",
        "blockers": [],
        "warnings": [],
    }


def merge_run_review_into_contract(
    contract: dict[str, Any],
    run: Any,
    *,
    timestamp: str | None = None,
) -> dict[str, Any]:
    merged = dict(contract)
    ts = timestamp or _now_iso()
    merged["timestamp"] = ts
    merged["feature"] = getattr(run, "feature", merged.get("feature"))
    merged["branch"] = getattr(run, "branch", merged.get("branch", ""))

    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    reviewers = review_state.get("reviewers")
    if isinstance(reviewers, list):
        merged["reviewers"] = [value for value in reviewers if isinstance(value, str) and value.strip()]
    automated_verdict = review_state.get("automatedVerdict")
    if isinstance(automated_verdict, str) and automated_verdict.strip():
        merged["automatedVerdict"] = automated_verdict
    final_verdict = review_state.get("finalVerdict")
    if isinstance(final_verdict, str) and final_verdict.strip():
        merged["verdict"] = final_verdict

    stages = review_state.get("stages")
    if isinstance(stages, list):
        existing = {
            item.get("stage"): item
            for item in merged.get("stageReviews", [])
            if isinstance(item, dict) and isinstance(item.get("stage"), str)
        }
        new_stage_reviews: list[dict[str, Any]] = []
        by_run_stage = {
            item.get("stage"): item
            for item in stages
            if isinstance(item, dict) and isinstance(item.get("stage"), str)
        }
        for stage_name in DELIVERY_REVIEW_STAGES:
            base = dict(existing.get(stage_name, {"stage": stage_name}))
            state = by_run_stage.get(stage_name, {})
            if isinstance(state, dict):
                base["status"] = state.get("status", base.get("status", "pending"))
                findings = state.get("findings")
                if isinstance(findings, list):
                    base["findings"] = findings
                evidence = state.get("evidence")
                if isinstance(evidence, list):
                    base["evidence"] = evidence
                notes = state.get("notes")
                if isinstance(notes, list):
                    base["notes"] = "\n".join(note for note in notes if isinstance(note, str) and note.strip())
                elif isinstance(notes, str):
                    base["notes"] = notes
            new_stage_reviews.append(base)
        merged["stageReviews"] = new_stage_reviews

    return merged


def write_review_artifact(
    review_json_path: Path,
    review_md_path: Path,
    contract: dict[str, Any],
    *,
    write_json_fn: Callable[[Path, Any], None] = write_json,
    write_text_fn: Callable[[Path, str], None] = _write_text,
    render_review_fn: Callable[[dict[str, Any]], str] = render_review,
) -> tuple[Path, Path]:
    write_json_fn(review_json_path, contract)
    write_text_fn(review_md_path, render_review_fn(contract).strip() + "\n")
    return review_json_path, review_md_path


def persist_review_artifact_from_run(
    root: Path,
    run: Any,
    *,
    load_json_fn: Callable[[Path], Any] = load_json,
    write_json_fn: Callable[[Path, Any], None] = write_json,
    write_text_fn: Callable[[Path, str], None] = _write_text,
    render_review_fn: Callable[[dict[str, Any]], str] = render_review,
) -> tuple[dict[str, Any], Path, Path]:
    existing_contract, review_json_path, review_md_path = load_review_contract(
        root,
        feature=str(getattr(run, "feature", "") or ""),
        review_path=str(getattr(run, "review_path", "") or ""),
        load_json_fn=load_json_fn,
    )
    contract = existing_contract or default_review_contract(
        feature=str(getattr(run, "feature", "") or ""),
        branch=str(getattr(run, "branch", "") or ""),
    )
    merged = merge_run_review_into_contract(contract, run)
    write_review_artifact(
        review_json_path,
        review_md_path,
        merged,
        write_json_fn=write_json_fn,
        write_text_fn=write_text_fn,
        render_review_fn=render_review_fn,
    )
    return merged, review_json_path, review_md_path
