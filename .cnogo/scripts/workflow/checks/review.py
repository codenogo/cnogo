"""Review contract generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scripts.workflow.shared.config import load_workflow_config


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
    reviewers = configured_reviewers(root)

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

    if feature:
        out_base = root / "docs" / "planning" / "work" / "features" / feature
        write_json(out_base / "REVIEW.json", contract)
        md_path = out_base / "REVIEW.md"
    else:
        out_base = root / "docs" / "planning" / "work" / "review"
        write_json(out_base / f"{ts}-REVIEW.json", contract)
        md_path = out_base / f"{ts}-REVIEW.md"

    md_lines = [
        "# Review Report",
        "",
        f"**Timestamp:** {ts}",
        f"**Branch:** {branch or '[unknown]'}",
        f"**Feature:** {feature or '[none]'}",
        "",
        "## Automated Checks (Package-Aware)",
        "",
        f"- Lint: **{agg['lint']}**",
        f"- Types: **{agg['typecheck']}**",
        f"- Tests: **{agg['tests']}**",
        f"- Invariants: **{inv['fail']} fail / {inv['warn']} warn**",
        (
            f"- Token savings: **{tokens['savedTokens']} tokens** "
            f"({tokens['savingsPct']}%, {tokens['checksRun']} checks)"
        ),
        "",
        "## Per-Package Results",
        "",
    ]
    for pkg in per_pkg:
        md_lines.append(f"### {pkg['name']} (`{pkg['path']}`)")
        for check in pkg.get("checks", []):
            suffix = ""
            if check.get("cmd"):
                cwd = check.get("cwd")
                cwd_part = f", cwd `{cwd}`" if isinstance(cwd, str) and cwd else ""
                suffix = f" (`{check.get('cmd')}`{cwd_part})"
            md_lines.append(f"- {check.get('name')}: **{check.get('result')}**{suffix}")
            token_telemetry = check.get("tokenTelemetry")
            if isinstance(token_telemetry, dict) and check.get("result") != "skipped":
                md_lines.append(
                    f"  - tokenTelemetry: in={token_telemetry.get('inputTokens', 0)} "
                    f"out={token_telemetry.get('outputTokens', 0)} "
                    f"saved={token_telemetry.get('savedTokens', 0)} "
                    f"({token_telemetry.get('savingsPct', 0.0)}%)"
                )
            full = check.get("fullOutputPath")
            if isinstance(full, str) and full:
                md_lines.append(f"  - full output: `{full}`")
        md_lines.append("")

    if invariant_findings:
        md_lines.append("## Invariant Findings")
        md_lines.append("")
        for finding in invariant_findings[:100]:
            md_lines.append(f"- [{finding.severity}] `{finding.file}:{finding.line}` {finding.message} ({finding.rule})")
        if len(invariant_findings) > 100:
            md_lines.append(f"- ... {len(invariant_findings) - 100} more")
        md_lines.append("")
    if reviewers:
        md_lines.append("## Reviewer Agents")
        md_lines.append("")
        for reviewer in reviewers:
            md_lines.append(f"- `{reviewer}`")
        md_lines.append("")
    md_lines.append(f"## Automated Gate\n\n**{automated_verdict.upper()}**\n")
    md_lines.append("## Final Verdict\n\n**PENDING**\n")

    md_lines.append("## Manual Review")
    md_lines.append("")
    md_lines.append("> Review criteria: see `.claude/skills/code-review.md`")
    md_lines.append(">")
    md_lines.append("> Fill stage reviews in order: `stageReviews[0]=spec-compliance`, then `stageReviews[1]=code-quality`.")
    md_lines.append(">")
    md_lines.append("> Fill `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]` in REVIEW.json.")
    md_lines.append("")

    write_text(md_path, "\n".join(md_lines).strip() + "\n")
    return 1 if automated_verdict == "fail" else 0
