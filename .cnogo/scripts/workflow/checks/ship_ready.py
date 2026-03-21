"""Ship-ready gate helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import enforcement_level, load_workflow_config


def parse_iso_ts(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    val = raw.strip()
    if val.endswith("Z"):
        val = val[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(val)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def latest_summary_timestamp(
    feature_dir: Path,
    *,
    load_json: Any,
) -> datetime | None:
    latest: datetime | None = None
    for summary_json in sorted(feature_dir.glob("*-SUMMARY.json")):
        ts: datetime | None = None
        try:
            payload = load_json(summary_json)
            if isinstance(payload, dict):
                ts = parse_iso_ts(payload.get("timestamp"))
        except Exception:
            ts = None
        if ts is None:
            try:
                ts = datetime.fromtimestamp(summary_json.stat().st_mtime, tz=timezone.utc)
            except OSError:
                ts = None
        if ts is not None and (latest is None or ts > latest):
            latest = ts
    return latest


def cmd_ship_ready(
    root: Path,
    feature: str,
    *,
    load_json: Any,
    subprocess_module: Any,
    json_output: bool = False,
) -> int:
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    wf = load_workflow_config(root)
    two_stage_level = enforcement_level(wf, "twoStageReview", default="error")
    verify_level = enforcement_level(wf, "verificationBeforeCompletion", default="error")
    checks: list[dict[str, str]] = []

    def add_check(name: str, ok: bool, details: str, level: str = "error") -> None:
        if ok:
            checks.append({"name": name, "status": "pass", "details": "ok"})
            return
        if level == "off":
            checks.append({"name": name, "status": "pass", "details": f"{details} (policy off)"})
            return
        status = "fail" if level == "error" else "warn"
        checks.append({"name": name, "status": status, "details": details})

    add_check(
        "feature_dir_exists",
        feature_dir.is_dir(),
        f"Feature directory not found: {feature_dir}",
        "error",
    )
    if not feature_dir.is_dir():
        if json_output:
            print(json.dumps({"feature": feature, "checks": checks}, indent=2))
        else:
            print(f"ship-ready: feature directory not found for `{feature}`")
        return 1

    try:
        phase_result = subprocess_module.run(
            ["python3", ".cnogo/scripts/workflow_memory.py", "phase-get", feature],
            capture_output=True, text=True, timeout=10, cwd=str(root),
        )
        phase_line = phase_result.stdout.strip()
        current_phase = phase_line.split(":")[-1].strip() if ":" in phase_line else ""
        phase_ok = current_phase in ("review", "ship")
        add_check(
            "phase_check",
            phase_ok,
            f"Feature phase is '{current_phase}'; expected 'review' or 'ship'.",
            "warn",
        )
    except Exception:
        checks.append({"name": "phase_check", "status": "pass", "details": "skipped (memory unavailable)"})

    review_json = feature_dir / "REVIEW.json"
    add_check("review_contract_exists", review_json.exists(), "Missing REVIEW.json contract.", "error")
    if not review_json.exists():
        if json_output:
            print(json.dumps({"feature": feature, "checks": checks}, indent=2))
        else:
            print(f"ship-ready: missing REVIEW.json for `{feature}`")
        return 1

    review_data: dict[str, Any] = {}
    try:
        parsed = load_json(review_json)
        if isinstance(parsed, dict):
            review_data = parsed
        else:
            raise ValueError("REVIEW.json is not a JSON object.")
    except Exception as exc:
        checks.append({"name": "review_contract_parse", "status": "fail", "details": str(exc)})
        if json_output:
            print(json.dumps({"feature": feature, "checks": checks}, indent=2))
        else:
            print(f"ship-ready: invalid REVIEW.json: {exc}")
        return 1

    schema_version = review_data.get("schemaVersion")
    add_check(
        "review_schema_v4",
        isinstance(schema_version, int) and not isinstance(schema_version, bool) and schema_version >= 4,
        "REVIEW.json schemaVersion must be >=4 for staged review enforcement.",
        two_stage_level,
    )

    stage_reviews = review_data.get("stageReviews")
    expected_stages = ["spec-compliance", "code-quality"]
    stages_ok = isinstance(stage_reviews, list) and len(stage_reviews) >= 2
    add_check(
        "stage_reviews_present",
        stages_ok,
        "REVIEW.json must include stageReviews[spec-compliance, code-quality].",
        two_stage_level,
    )

    if stages_ok and isinstance(stage_reviews, list):
        order_ok = True
        completion_ok = True
        evidence_ok = True
        no_failed_stage = True
        for idx, expected in enumerate(expected_stages):
            item = stage_reviews[idx]
            if not isinstance(item, dict):
                order_ok = False
                completion_ok = False
                evidence_ok = False
                no_failed_stage = False
                continue
            if item.get("stage") != expected:
                order_ok = False
            status = item.get("status")
            if status not in {"pass", "warn", "fail"}:
                completion_ok = False
                no_failed_stage = False
            elif status == "fail":
                no_failed_stage = False
            evidence = item.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                evidence_ok = False
        add_check(
            "stage_review_order",
            order_ok,
            "stageReviews must be ordered as spec-compliance then code-quality.",
            two_stage_level,
        )
        add_check(
            "stage_review_complete",
            completion_ok,
            "Both stage reviews must be completed with status pass|warn|fail before ship.",
            two_stage_level,
        )
        add_check(
            "stage_review_no_fail",
            no_failed_stage,
            "Stage review status cannot be fail before ship; resolve blockers or downgrade to warn with rationale.",
            two_stage_level,
        )
        add_check(
            "stage_review_evidence",
            evidence_ok,
            "Each completed stage review must include non-empty evidence entries.",
            verify_level,
        )

    review_ts = parse_iso_ts(review_data.get("timestamp"))
    latest_summary_ts = latest_summary_timestamp(feature_dir, load_json=load_json)
    freshness_ok = (
        review_ts is not None
        and latest_summary_ts is not None
        and review_ts >= latest_summary_ts
    )
    add_check(
        "fresh_review_after_latest_summary",
        freshness_ok,
        "REVIEW.json timestamp must be at/after latest SUMMARY.json timestamp.",
        verify_level,
    )

    has_fail = any(check["status"] == "fail" for check in checks)
    if json_output:
        print(json.dumps({"feature": feature, "checks": checks}, indent=2))
    else:
        icons = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        print(f"ship-ready checks for `{feature}`")
        for check in checks:
            icon = icons.get(check["status"], "?")
            print(f"  {icon} {check['name']}: {check['details']}")
    return 1 if has_fail else 0
