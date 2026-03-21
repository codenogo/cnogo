"""Quick-task validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_quick_contract(contract: Any, findings: list[Any], path: Path, *, finding_type: Any) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "Quick contract must be a JSON object.", str(path)))
        return
    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "Quick contract missing schemaVersion (recommended).", str(path)))
    goal = contract.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        findings.append(finding_type("ERROR", "Quick contract missing non-empty 'goal'.", str(path)))
    files = contract.get("files")
    if not isinstance(files, list) or not files:
        findings.append(finding_type("ERROR", "Quick contract missing non-empty 'files' array.", str(path)))
    verify = contract.get("verify")
    if not isinstance(verify, list) or not verify:
        findings.append(finding_type("ERROR", "Quick contract missing non-empty 'verify' array of commands.", str(path)))


def validate_quick_summary(contract: Any, findings: list[Any], path: Path, *, finding_type: Any) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "Quick summary contract must be a JSON object.", str(path)))
        return
    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "Quick summary missing 'schemaVersion'.", str(path)))
    outcome = contract.get("outcome")
    if not isinstance(outcome, str) or not outcome:
        findings.append(finding_type("ERROR", "Quick summary missing non-empty 'outcome'.", str(path)))
    changes = contract.get("changes")
    if not isinstance(changes, list) or not changes:
        findings.append(finding_type("ERROR", "Quick summary missing non-empty 'changes' list.", str(path)))
    verification = contract.get("verification")
    if not isinstance(verification, list) or not verification:
        findings.append(finding_type("ERROR", "Quick summary missing non-empty 'verification' list.", str(path)))


def validate_quick_tasks(
    root: Path,
    findings: list[Any],
    touched: Any,
    *,
    iter_quick_dirs: Any,
    quick_dir_re: Any,
    require: Any,
    load_json: Any,
    validate_quick_contract: Any,
    validate_quick_summary: Any,
    finding_type: Any,
) -> None:
    """Validate quick task directories and their contracts."""
    for quick_dir in iter_quick_dirs(root):
        if not touched(quick_dir):
            continue
        if not quick_dir_re.match(quick_dir.name):
            findings.append(
                finding_type(
                    "ERROR",
                    "Quick task directory must be NNN-slug (e.g. 001-fix-typo).",
                    str(quick_dir),
                )
            )
        plan_md = quick_dir / "PLAN.md"
        plan_json = quick_dir / "PLAN.json"
        if plan_md.exists():
            require(plan_json, findings, "Missing PLAN.json contract for quick PLAN.md")
            if plan_json.exists():
                try:
                    validate_quick_contract(load_json(plan_json), findings, plan_json)
                except Exception as exc:
                    findings.append(
                        finding_type("ERROR", f"Failed to parse quick plan contract: {exc}", str(plan_json))
                    )
        summary_md = quick_dir / "SUMMARY.md"
        summary_json = quick_dir / "SUMMARY.json"
        if summary_md.exists():
            require(summary_json, findings, "Missing SUMMARY.json contract for quick SUMMARY.md")
        if summary_json.exists():
            try:
                validate_quick_summary(load_json(summary_json), findings, summary_json)
            except Exception as exc:
                findings.append(
                    finding_type("ERROR", f"Failed to parse quick summary contract: {exc}", str(summary_json))
                )
