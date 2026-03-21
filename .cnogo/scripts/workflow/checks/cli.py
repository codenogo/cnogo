"""CLI parser and command dispatch helpers for workflow checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable


def build_parser(*, default_command_usage_since_days: int) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run package-aware workflow checks.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    verify = sub.add_parser("verify-ci", help="Run CI verification checks and write VERIFICATION-CI artifacts.")
    verify.add_argument("feature", help="Feature slug (docs/planning/work/features/<feature>/)")

    review = sub.add_parser("review", help="Run review checks and write REVIEW artifacts.")
    review.add_argument("--feature", help="Feature slug (overrides memory inference).")

    summarize = sub.add_parser(
        "summarize",
        help="Generate NN-SUMMARY artifacts from a plan contract and recorded execution evidence.",
    )
    summarize.add_argument("feature_pos", nargs="?", help="Feature slug (positional shorthand).")
    summarize.add_argument("plan_pos", nargs="?", help="Plan number (NN) (positional shorthand).")
    summarize.add_argument("--feature", help="Feature slug (docs/planning/work/features/<feature>/)")
    summarize.add_argument("--plan", help="Plan number (NN).")
    summarize.add_argument(
        "--outcome",
        choices=["auto", "complete", "partial", "failed"],
        default="auto",
        help="Override summary outcome; defaults to auto.",
    )
    summarize.add_argument("--note", action="append", default=[], help="Optional note to include in SUMMARY.json.")
    summarize.add_argument("--json", action="store_true", dest="json_output", help="Output the generated summary contract as JSON.")

    ship_ready = sub.add_parser(
        "ship-ready",
        help="Validate staged review completion and evidence freshness before /ship.",
    )
    ship_ready.add_argument("--feature", required=True, help="Feature slug (docs/planning/work/features/<feature>/)")
    ship_ready.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON.")

    entropy = sub.add_parser(
        "entropy",
        help="Run invariant scan and optionally write a background entropy-cleanup task.",
    )
    entropy.add_argument("--write-task", action="store_true", help="Write docs/planning/work/background/*-entropy-cleanup-TASK.md")
    entropy.add_argument("--max-files", type=int, help="Override max files per entropy cleanup task.")
    entropy.add_argument("--max-tasks", type=int, help="Override max cleanup tasks generated per run.")

    discover = sub.add_parser(
        "discover",
        help="Analyze command usage telemetry for missed token-savings opportunities.",
    )
    discover.add_argument("--since-days", type=int, default=default_command_usage_since_days, help="Telemetry lookback window in days.")
    discover.add_argument("--limit", type=int, default=10, help="Max rows per section.")
    discover.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    doctor = sub.add_parser("doctor", help="Run diagnostic health checks on the workflow environment.")
    doctor.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON.")

    return parser


def run_command(
    args: argparse.Namespace,
    *,
    root: Path,
    default_command_timeout_sec: int,
    load_workflow: Callable[[Path | None], dict[str, Any]],
    autobootstrap_packages_if_empty: Callable[..., dict[str, Any]],
    checks_runtime_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    infer_feature_from_state: Callable[[Path], str | None],
    discover_command_usage: Callable[..., dict[str, Any]],
    print_discover_text: Callable[[dict[str, Any]], None],
    cmd_doctor: Callable[[Path, dict[str, Any], bool], int],
    cmd_summarize: Callable[..., int],
    cmd_ship_ready: Callable[..., int],
    run_invariant_checks: Callable[..., list[Any]],
    entropy_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    summarize_invariants: Callable[[list[Any]], dict[str, int]],
    entropy_candidates: Callable[..., list[dict[str, Any]]],
    write_entropy_task: Callable[..., Path],
    packages_from_workflow: Callable[[dict[str, Any]], list[dict[str, Any]]],
    changed_relpaths: Callable[..., set[str]],
    changed_relpaths_against_base: Callable[[Path], set[str]],
    run_package_checks: Callable[..., list[dict[str, Any]]],
    write_verify_ci: Callable[[Path, str, list[dict[str, Any]], list[Any]], int],
    write_review: Callable[[Path, str | None, list[dict[str, Any]], list[Any]], int],
) -> int:
    workflow = load_workflow(root)
    workflow = autobootstrap_packages_if_empty(
        root,
        workflow,
        cmd=args.cmd,
        timeout_sec=default_command_timeout_sec,
    )
    checks_cfg = checks_runtime_cfg(workflow)
    check_scope_cfg = str(checks_cfg.get("checkScope", "auto"))
    ci_env = os.getenv("CI", "").strip().lower()
    in_ci = ci_env not in {"", "0", "false", "no"}
    if check_scope_cfg == "all":
        effective_check_scope = "all"
    elif check_scope_cfg == "changed":
        effective_check_scope = "changed"
    else:
        effective_check_scope = "all" if in_ci else "changed"

    changed_files_fallback = str(checks_cfg.get("changedFilesFallback", "none"))
    command_timeout_sec = int(checks_cfg.get("commandTimeoutSec", default_command_timeout_sec))
    output_compaction = checks_cfg.get("outputCompaction") if isinstance(checks_cfg.get("outputCompaction"), dict) else {}
    output_recovery = checks_cfg.get("outputRecovery") if isinstance(checks_cfg.get("outputRecovery"), dict) else {}
    token_telemetry_cfg = checks_cfg.get("tokenTelemetry") if isinstance(checks_cfg.get("tokenTelemetry"), dict) else {}
    token_telemetry_enabled = bool(token_telemetry_cfg.get("enabled", True))
    hook_opt_cfg = checks_cfg.get("hookOptimization") if isinstance(checks_cfg.get("hookOptimization"), dict) else {}

    feature_for_scope: str | None = None
    if args.cmd == "verify-ci":
        feature_for_scope = args.feature
    elif args.cmd == "review":
        feature_for_scope = args.feature or infer_feature_from_state(root)

    if args.cmd == "discover":
        report = discover_command_usage(
            root,
            log_file=str(hook_opt_cfg.get("logFile", ".cnogo/command-usage.jsonl")),
            since_days=max(0, int(args.since_days)),
            limit=max(1, int(args.limit)),
        )
        if args.format == "json":
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_discover_text(report)
        return 0

    if args.cmd == "doctor":
        return cmd_doctor(root, workflow, json_output=getattr(args, "json_output", False))

    if args.cmd == "summarize":
        feature = getattr(args, "feature", None) or getattr(args, "feature_pos", None)
        plan_number = getattr(args, "plan", None) or getattr(args, "plan_pos", None)
        if not feature or not plan_number:
            print(
                "workflow_checks.py summarize requires feature and plan "
                "(use positional `summarize <feature> <NN>` or `--feature/--plan`).",
                file=sys.stderr,
            )
            return 2
        return cmd_summarize(
            root,
            feature,
            plan_number,
            outcome=args.outcome,
            notes=list(args.note or []),
            json_output=getattr(args, "json_output", False),
        )

    if args.cmd == "ship-ready":
        return cmd_ship_ready(root, args.feature, json_output=getattr(args, "json_output", False))

    invariant_findings = run_invariant_checks(root, workflow, changed_files_fallback=changed_files_fallback)

    if args.cmd == "entropy":
        entropy_settings = entropy_cfg(workflow)
        if not entropy_settings.get("enabled", True):
            print("Entropy cleanup is disabled in WORKFLOW.json (entropy.enabled=false).")
            return 0
        max_files = args.max_files if isinstance(args.max_files, int) and args.max_files > 0 else int(entropy_settings.get("maxFilesPerTask", 3))
        max_tasks = args.max_tasks if isinstance(args.max_tasks, int) and args.max_tasks > 0 else int(entropy_settings.get("maxTasksPerRun", 3))
        summary = summarize_invariants(invariant_findings)
        print(
            json.dumps(
                {
                    "invariants": summary,
                    "candidates": entropy_candidates(
                        invariant_findings,
                        max_files_per_task=max_files,
                        max_tasks=max_tasks,
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        if args.write_task:
            task_path = write_entropy_task(
                root,
                invariant_findings,
                max_files_per_task=max_files,
                max_tasks=max_tasks,
            )
            print(f"Wrote entropy background task: {task_path}")
        return 1 if summary["fail"] > 0 else 0

    packages = packages_from_workflow(workflow)
    if not packages:
        print("⚠️ No packages configured in docs/planning/WORKFLOW.json (packages[]).")
        print("Proceeding with empty package set; checks will be recorded as skipped.")
        print("Optional setup: python3 .cnogo/scripts/workflow_detect.py --write-workflow")
        per_pkg: list[dict[str, Any]] = []
    else:
        changed: set[str] | None = None
        if effective_check_scope == "changed":
            changed = changed_relpaths(root, fallback=changed_files_fallback)
        elif in_ci and (feature_for_scope or args.cmd == "review"):
            scoped = changed_relpaths_against_base(root)
            if not scoped and changed_files_fallback != "none":
                scoped = changed_relpaths(root, fallback=changed_files_fallback)
            if scoped:
                changed = scoped
                scope_label = feature_for_scope or "review"
                print(
                    "CI feature-scoped package checks: "
                    f"{len(scoped)} changed file(s) against base for `{scope_label}`."
                )
            else:
                print("CI feature-scoped package checks unavailable; running all packages.")

        if effective_check_scope == "changed" and not changed:
            print("No local changes detected; package checks skipped (checkScope=changed).")
        per_pkg = run_package_checks(
            root,
            packages,
            changed_relpaths=changed,
            timeout_sec=command_timeout_sec,
            output_compaction=output_compaction,
            output_recovery=output_recovery,
            token_telemetry_enabled=token_telemetry_enabled,
        )

    if args.cmd == "verify-ci":
        return write_verify_ci(root, args.feature, per_pkg, invariant_findings)

    if args.cmd == "review":
        return write_review(root, feature_for_scope, per_pkg, invariant_findings)

    return 2
