#!/usr/bin/env python3
"""
Package-aware check runner for this workflow pack.

Reads docs/planning/WORKFLOW.json packages[].commands and runs checks per package:
- verify-ci: writes VERIFICATION-CI.md/json under a feature folder
- review: writes REVIEW.md/json under feature folder if inferable from memory, else under work/review/

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_utils import load_json, load_workflow as _load_workflow_util, repo_root, write_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_shell(cmd: str, cwd: Path) -> tuple[int, str]:
    # WORKFLOW.json is a trusted file (equivalent to Makefile) — shell=True is intentional.
    try:
        out = subprocess.check_output(cmd, cwd=cwd, shell=True, stderr=subprocess.STDOUT).decode(errors="replace")
        return 0, out
    except subprocess.CalledProcessError as e:
        out = (e.output or b"").decode(errors="replace")
        return int(e.returncode or 1), out


def git_branch(root: Path) -> str:
    rc, out = run_shell("git branch --show-current", cwd=root)
    return out.strip() if rc == 0 else ""


def infer_feature_from_state(root: Path) -> str | None:
    """Infer the active feature slug from memory engine, with branch fallback."""
    # Try memory engine first
    try:
        import sys
        sys.path.insert(0, str(root))
        from scripts.memory import is_initialized, list_issues
        if is_initialized(root):
            # Look for in-progress epics first, then open epics
            for status in ("in_progress", "open"):
                epics = list_issues(
                    issue_type="epic", status=status, root=root
                )
                for epic in epics:
                    if epic.feature_slug:
                        return epic.feature_slug
    except Exception:
        pass
    # Fallback: parse branch name (e.g. feature/foo-bar -> foo-bar)
    branch = git_branch(root)
    if branch and "/" in branch:
        slug = branch.split("/", 1)[1]
        if slug and slug not in {"main", "master", "develop"}:
            return slug
    return None


@dataclass
class CheckResult:
    name: str
    result: str  # pass|fail|skipped|warn
    details: str = ""
    cmd: str | None = None


def load_workflow(root: Path | None = None) -> dict[str, Any]:
    return _load_workflow_util()


def packages_from_workflow(wf: dict[str, Any]) -> list[dict[str, Any]]:
    pkgs = wf.get("packages")
    if not isinstance(pkgs, list):
        return []
    out: list[dict[str, Any]] = []
    for p in pkgs:
        if isinstance(p, dict) and isinstance(p.get("path"), str):
            out.append(p)
    return out


def run_package_checks(root: Path, pkgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for p in pkgs:
        path = str(p.get("path") or ".")
        kind = str(p.get("kind") or "other")
        name = str(p.get("name") or Path(path).name or path)
        cmds = p.get("commands") if isinstance(p.get("commands"), dict) else {}

        pkg_dir = (root / path).resolve()
        pkg_res: dict[str, Any] = {"name": name, "path": path, "kind": kind, "checks": []}

        for check_name in ["lint", "typecheck", "test"]:
            cmd = cmds.get(check_name)
            if not isinstance(cmd, str) or not cmd.strip():
                pkg_res["checks"].append({"name": check_name, "result": "skipped", "cmd": None})
                continue
            rc, out = run_shell(cmd, cwd=pkg_dir)
            pkg_res["checks"].append(
                {
                    "name": check_name,
                    "result": "pass" if rc == 0 else "fail",
                    "cmd": cmd,
                    "exitCode": rc,
                    "output": out[-2000:],  # keep tail for readability
                }
            )

        results.append(pkg_res)
    return results


def summarize_checksets(per_pkg: list[dict[str, Any]]) -> dict[str, str]:
    """
    Aggregate overall lint/tests/types results.
    """
    summary = {"lint": "skipped", "typecheck": "skipped", "tests": "skipped"}
    mapping = {"lint": "lint", "typecheck": "typecheck", "test": "tests"}

    for pkg in per_pkg:
        for c in pkg.get("checks", []):
            nm = c.get("name")
            res = c.get("result")
            if nm not in mapping:
                continue
            key = mapping[nm]
            if res == "fail":
                summary[key] = "fail"
            elif res == "pass" and summary[key] != "fail":
                summary[key] = "pass"
            elif summary[key] == "skipped" and res == "skipped":
                summary[key] = "skipped"
    return summary


def write_verify_ci(root: Path, feature: str, per_pkg: list[dict[str, Any]]) -> int:
    base = root / "docs" / "planning" / "work" / "features" / feature
    ts = now_iso()
    agg = summarize_checksets(per_pkg)

    contract = {
        "schemaVersion": 1,
        "feature": feature,
        "timestamp": ts,
        "checks": [
            {"name": "lint", "result": agg["lint"]},
            {"name": "types", "result": agg["typecheck"]},
            {"name": "tests", "result": agg["tests"]},
        ],
        "packages": per_pkg,
        "notes": [],
    }
    write_json(base / "VERIFICATION-CI.json", contract)

    md_lines = [
        f"# Verification (CI): {feature}",
        "",
        f"**Timestamp:** {ts}",
        "",
        "## Summary",
        "",
        f"- Lint: **{agg['lint']}**",
        f"- Types: **{agg['typecheck']}**",
        f"- Tests: **{agg['tests']}**",
        "",
        "## Per-Package Results",
        "",
    ]
    for pkg in per_pkg:
        md_lines.append(f"### {pkg['name']} (`{pkg['path']}`)")
        for c in pkg.get("checks", []):
            md_lines.append(f"- {c.get('name')}: **{c.get('result')}**" + (f" (`{c.get('cmd')}`)" if c.get("cmd") else ""))
        md_lines.append("")
    write_text(base / "VERIFICATION-CI.md", "\n".join(md_lines).strip() + "\n")

    # exit code: fail if any fail
    return 1 if any(c["result"] == "fail" for pkg in per_pkg for c in pkg.get("checks", [])) else 0


def write_review(root: Path, feature: str | None, per_pkg: list[dict[str, Any]]) -> int:
    ts = now_iso()
    branch = git_branch(root)
    agg = summarize_checksets(per_pkg)

    verdict = "pass"
    if "fail" in agg.values():
        verdict = "fail"
    elif any(v == "skipped" for v in agg.values()):
        verdict = "warn"

    contract = {
        "schemaVersion": 1,
        "timestamp": ts,
        "feature": feature,
        "branch": branch,
        "automated": [
            {"name": "lint", "result": agg["lint"]},
            {"name": "types", "result": agg["typecheck"]},
            {"name": "tests", "result": agg["tests"]},
        ],
        "packages": per_pkg,
        "verdict": verdict,
        "blockers": [],
        "warnings": [],
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
        "",
        "## Per-Package Results",
        "",
    ]
    for pkg in per_pkg:
        md_lines.append(f"### {pkg['name']} (`{pkg['path']}`)")
        for c in pkg.get("checks", []):
            md_lines.append(f"- {c.get('name')}: **{c.get('result')}**" + (f" (`{c.get('cmd')}`)" if c.get("cmd") else ""))
        md_lines.append("")
    md_lines.append(f"## Verdict\n\n**{verdict.upper()}**\n")

    # Enforced section (validator checks for presence)
    md_lines.append("## Karpathy Checklist")
    md_lines.append("")
    md_lines.append("| Principle | Status | Notes |")
    md_lines.append("|----------|--------|------|")
    md_lines.append("| Think Before Coding | ⬜ | |")
    md_lines.append("| Simplicity First | ⬜ | |")
    md_lines.append("| Surgical Changes | ⬜ | |")
    md_lines.append("| Goal-Driven Execution | ⬜ | |")
    md_lines.append("")

    write_text(md_path, "\n".join(md_lines).strip() + "\n")

    return 1 if verdict == "fail" else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run package-aware workflow checks.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify-ci", help="Run CI verification checks and write VERIFICATION-CI artifacts.")
    v.add_argument("feature", help="Feature slug (docs/planning/work/features/<feature>/)")

    r = sub.add_parser("review", help="Run review checks and write REVIEW artifacts.")
    r.add_argument("--feature", help="Feature slug (overrides memory inference).")

    args = parser.parse_args()
    root = repo_root()
    wf = load_workflow(root)
    pkgs = packages_from_workflow(wf)
    if not pkgs:
        print("⚠️ No packages configured in docs/planning/WORKFLOW.json (packages[]).")
        print("Run: python3 scripts/workflow_detect.py --write-workflow")
        return 0

    per_pkg = run_package_checks(root, pkgs)

    if args.cmd == "verify-ci":
        return write_verify_ci(root, args.feature, per_pkg)

    if args.cmd == "review":
        feature = args.feature or infer_feature_from_state(root)
        return write_review(root, feature, per_pkg)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

