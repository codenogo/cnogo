"""Review contract generation helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

from scripts.workflow.shared.config import load_workflow_config
from scripts.workflow.shared.formulas import (
    formula_auto_spawn_configured_reviewers,
    formula_required_reviewers,
)
from scripts.workflow.orchestration.review_artifacts import write_review_artifact


def configured_reviewers(root: Path) -> list[str]:
    wf = load_workflow_config(root)
    teams = wf.get("agentTeams")
    if not isinstance(teams, dict):
        return []
    if teams.get("enabled") is False:
        return []
    compositions = teams.get("defaultCompositions")
    if not isinstance(compositions, dict):
        return []
    reviewers = compositions.get("review")
    if not isinstance(reviewers, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for reviewer in reviewers:
        if not isinstance(reviewer, str) or not reviewer.strip():
            continue
        name = reviewer.strip()
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _merge_reviewers(*reviewer_lists: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for reviewers in reviewer_lists:
        for reviewer in reviewers:
            if not isinstance(reviewer, str) or not reviewer.strip():
                continue
            value = reviewer.strip()
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
    return out


def graph_impact_section(root: Path, changed_relpaths: set[str]) -> dict[str, Any]:
    try:
        import sys
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from scripts.context import ContextGraph

        graph = ContextGraph(repo_path=root)
        try:
            result = graph.review_impact(sorted(changed_relpaths))
            return {"enabled": True, **result}
        finally:
            graph.close()
    except Exception as exc:
        return {"enabled": False, "error": str(exc)}


def _review_ready_or_started(run: Any) -> bool:
    review_readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    return review_readiness.get("status") == "ready" or review_state.get("status") in {"in_progress", "completed"}


def _resolve_review_delivery_run(root: Path, *, feature: str | None) -> tuple[Any | None, str | None]:
    if not feature:
        return None, None
    try:
        from scripts.memory import latest_delivery_run
    except Exception as exc:
        return None, f"Unable to load Delivery Run support for review: {exc}"

    run = latest_delivery_run(feature, root=root)
    if run is None:
        return None, (
            f"Review requires a Delivery Run for feature {feature!r}. "
            "Create or resume one with `python3 .cnogo/scripts/workflow_memory.py run-create "
            f"{feature} <NN>` or `/implement {feature} <NN>`."
        )
    if not _review_ready_or_started(run):
        readiness = run.review_readiness.get("status", "pending") if isinstance(getattr(run, "review_readiness", None), dict) else "pending"
        review_status = run.review.get("status", "pending") if isinstance(getattr(run, "review", None), dict) else "pending"
        return None, (
            "Review cannot start until the linked Delivery Run is review-ready "
            f"(reviewReadiness.status={readiness!r}, review.status={review_status!r})."
        )
    return run, None


def _delivery_run_snapshot(run: Any) -> dict[str, Any]:
    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    review_readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    return {
        "runId": getattr(run, "run_id", ""),
        "planNumber": getattr(run, "plan_number", ""),
        "mode": getattr(run, "mode", ""),
        "status": getattr(run, "status", ""),
        "integrationStatus": integration.get("status", "pending"),
        "reviewReadiness": review_readiness.get("status", "pending"),
        "reviewStatus": review_state.get("status", "pending"),
        "reviewVerdict": review_state.get("finalVerdict", "pending"),
    }


def _sync_linked_delivery_run(
    root: Path,
    *,
    feature: str | None,
    contract: dict[str, Any],
    review_json_path: Path | None,
) -> None:
    if not feature or review_json_path is None:
        return
    try:
        from scripts.memory import latest_delivery_run, sync_delivery_run_review

        run = latest_delivery_run(feature, root=root)
        if run is None:
            return
        sync_delivery_run_review(
            run,
            review_contract=contract,
            review_path=str(review_json_path.relative_to(root)),
            root=root,
        )
    except Exception:
        return


def write_review(
    root: Path,
    feature: str | None,
    per_pkg: list[dict[str, Any]],
    invariant_findings: list[Any],
    *,
    review_schema_version: int,
    now_iso: Callable[[], str],
    git_branch: Callable[[Path], str],
    summarize_checksets: Callable[[list[dict[str, Any]]], dict[str, str]],
    summarize_invariants: Callable[[list[Any]], dict[str, int]],
    summarize_token_telemetry: Callable[[list[dict[str, Any]]], dict[str, Any]],
    changed_relpaths: Callable[[Path], set[str]],
    write_json: Callable[[Path, dict[str, Any]], None],
    write_text: Callable[[Path, str], None],
) -> int:
    ts = now_iso()
    branch = git_branch(root)
    agg = summarize_checksets(per_pkg)
    inv = summarize_invariants(invariant_findings)
    tokens = summarize_token_telemetry(per_pkg)
    linked_run, gating_error = _resolve_review_delivery_run(root, feature=feature)
    if gating_error:
        print(gating_error, file=sys.stderr)
        return 1
    run_formula = (
        linked_run.formula
        if linked_run is not None and isinstance(getattr(linked_run, "formula", None), dict)
        else {}
    )
    reviewers = _merge_reviewers(
        configured_reviewers(root) if formula_auto_spawn_configured_reviewers(run_formula) else [],
        formula_required_reviewers(run_formula),
    )

    automated_verdict = "pass"
    if "fail" in agg.values() or inv["fail"] > 0:
        automated_verdict = "fail"
    elif any(v == "skipped" for v in agg.values()) or inv["warn"] > 0:
        automated_verdict = "warn"

    blockers = [
        {
            "file": finding.file,
            "line": finding.line,
            "issue": finding.message,
            "severity": "high",
            "rule": finding.rule,
        }
        for finding in invariant_findings
        if finding.severity == "fail"
    ]
    warnings = [
        {
            "file": finding.file,
            "line": finding.line,
            "issue": finding.message,
            "severity": "medium",
            "rule": finding.rule,
        }
        for finding in invariant_findings
        if finding.severity != "fail"
    ]

    contract = {
        "schemaVersion": review_schema_version,
        "timestamp": ts,
        "feature": feature,
        "branch": branch,
        "automated": [
            {"name": "lint", "result": agg["lint"]},
            {"name": "types", "result": agg["typecheck"]},
            {"name": "tests", "result": agg["tests"]},
        ],
        "packages": per_pkg,
        "invariants": {
            "summary": inv,
            "findings": [
                {
                    "rule": finding.rule,
                    "severity": finding.severity,
                    "file": finding.file,
                    "line": finding.line,
                    "message": finding.message,
                }
                for finding in invariant_findings[:200]
            ],
        },
        "tokenTelemetry": tokens,
        "impactAnalysis": graph_impact_section(root, changed_relpaths(root)),
        "reviewers": reviewers,
        "deliveryRun": _delivery_run_snapshot(linked_run) if linked_run is not None else None,
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
        "automatedVerdict": automated_verdict,
        "verdict": "pending",
        "blockers": blockers[:100],
        "warnings": warnings[:200],
    }

    review_json_path: Path | None = None
    review_md_path: Path | None = None
    if feature:
        out_base = root / "docs" / "planning" / "work" / "features" / feature
        review_json_path = out_base / "REVIEW.json"
        review_md_path = out_base / "REVIEW.md"
    else:
        out_base = root / "docs" / "planning" / "work" / "review"
        review_json_path = out_base / f"{ts}-REVIEW.json"
        review_md_path = out_base / f"{ts}-REVIEW.md"

    if review_json_path is None or review_md_path is None:
        raise ValueError("Unable to resolve review artifact paths.")
    write_review_artifact(
        review_json_path,
        review_md_path,
        contract,
        write_json_fn=write_json,
        write_text_fn=write_text,
    )
    _sync_linked_delivery_run(
        root,
        feature=feature,
        contract=contract,
        review_json_path=review_json_path,
    )
    return 1 if automated_verdict == "fail" else 0
