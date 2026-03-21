"""CLI parser and output helpers for workflow validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate workflow planning artifacts.")
    parser.add_argument("--root", default=".", help="Repo root (defaults to current directory).")
    parser.add_argument("--staged", action="store_true", help="Validate only areas touched by staged changes.")
    parser.add_argument("--feature", help="Validate only one feature slug under docs/planning/work/features/.")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    parser.add_argument("--save-baseline", action="store_true", help="Save current warnings as baseline.")
    parser.add_argument("--diff-baseline", action="store_true", help="Diff current warnings against saved baseline.")
    return parser


def run_cli(
    args: argparse.Namespace,
    *,
    repo_root: Callable[[Path], Path],
    validate_repo: Callable[[Path], list[Any]],
    finding_to_warning: Callable[[Any], dict[str, Any]],
    save_baseline: Callable[[list[dict[str, Any]], Path], Path],
    load_baseline: Callable[[Path], list[dict[str, Any]] | None],
    diff_baselines: Callable[[list[dict[str, Any]], list[dict[str, Any]]], dict[str, list[dict[str, Any]]]],
    save_latest: Callable[[list[dict[str, Any]], Path], None],
) -> int:
    root = repo_root(Path(args.root))
    feature_filter = args.feature.strip() if isinstance(args.feature, str) and args.feature.strip() else None
    findings = validate_repo(root, staged_only=args.staged, feature_filter=feature_filter)
    warnings = [finding_to_warning(finding) for finding in findings]

    if args.save_baseline:
        path = save_baseline(warnings, root)
        print(f"Baseline saved: {path} ({len(warnings)} warnings)")
        return 0

    if args.diff_baseline:
        baseline = load_baseline(root)
        if baseline is None:
            print("No baseline found. Run with --save-baseline first.")
            return 1
        result = diff_baselines(baseline, warnings)
        print("## Validation Diff")
        print(f"\nNew warnings ({len(result['new'])}):")
        for warning in result["new"]:
            loc = f" ({warning['file']})" if warning.get("file") else ""
            print(f"  [{warning['level']}]{loc} {warning['message']}")
        print(f"\nResolved warnings ({len(result['resolved'])}):")
        for warning in result["resolved"]:
            loc = f" ({warning['file']})" if warning.get("file") else ""
            print(f"  [{warning['level']}]{loc} {warning['message']}")
        print(f"\nUnchanged warnings ({len(result['unchanged'])}):")
        for warning in result["unchanged"]:
            loc = f" ({warning['file']})" if warning.get("file") else ""
            print(f"  [{warning['level']}]{loc} {warning['message']}")
        save_latest(warnings, root)
        return 1 if result["new"] else 0

    if args.json:
        print(
            json.dumps(
                [
                    {"level": finding.level, "message": finding.message, "path": finding.path}
                    for finding in findings
                ],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        if not findings:
            print("✅ Workflow validation passed")
        else:
            for finding in findings:
                print(finding.format())

    save_latest(warnings, root)
    errors = [finding for finding in findings if finding.level == "ERROR"]
    return 1 if errors else 0
