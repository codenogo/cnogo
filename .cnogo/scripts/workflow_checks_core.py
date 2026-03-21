#!/usr/bin/env python3
"""
Package-aware check runner for this workflow pack.

Reads docs/planning/WORKFLOW.json packages[].commands and runs checks per package:
- verify-ci: writes VERIFICATION-CI.md/json under a feature folder
- review: writes REVIEW.md/json under feature folder if inferable from memory, else under work/review/
- summarize: writes NN-SUMMARY.md/json from plan + execution evidence
- ship-ready: validates staged-review completeness + freshness for /ship
- entropy: scans for invariant drift and can write background cleanup tasks
- discover: analyzes hook telemetry for missed token-savings opportunities

No external dependencies.
"""

from __future__ import annotations

try:
    import _bootstrap  # noqa: F401
except ImportError:
    pass  # imported as module; caller manages sys.path

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

try:
    from workflow_utils import load_json, repo_root, write_json
except ModuleNotFoundError:
    from .workflow_utils import load_json, repo_root, write_json  # type: ignore

from scripts.workflow.shared.config import enforcement_level as _shared_enforcement_level
from scripts.workflow.checks import config as _checks_config_helpers
from scripts.workflow.checks import context as _context_helpers
from scripts.workflow.checks import cli as _cli_helpers
from scripts.workflow.checks import doctor as _doctor_helpers
from scripts.workflow.checks import entropy as _entropy_helpers
from scripts.workflow.checks import invariants as _invariant_helpers
from scripts.workflow.checks import package_checks as _package_check_helpers
from scripts.workflow.checks import review as _review_helpers
from scripts.workflow.checks import runtime as _runtime_helpers
from scripts.workflow.checks import ship_ready as _ship_ready_helpers
from scripts.workflow.checks import summary as _summary_helpers
from scripts.workflow.checks import summary_runtime as _summary_runtime_helpers
from scripts.workflow.shared.packages import package_has_changes as _shared_package_has_changes
from scripts.workflow.shared.plans import normalize_plan_number as _shared_normalize_plan_number

DEFAULT_COMMAND_TIMEOUT_SEC = _runtime_helpers.DEFAULT_COMMAND_TIMEOUT_SEC
DEFAULT_OUTPUT_COMPACT_MAX_LINES = _runtime_helpers.DEFAULT_OUTPUT_COMPACT_MAX_LINES
DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES = _runtime_helpers.DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES
DEFAULT_OUTPUT_COMPACT_PASS_LINES = _runtime_helpers.DEFAULT_OUTPUT_COMPACT_PASS_LINES
DEFAULT_TEE_MIN_CHARS = _runtime_helpers.DEFAULT_TEE_MIN_CHARS
DEFAULT_TEE_MAX_FILES = _runtime_helpers.DEFAULT_TEE_MAX_FILES
DEFAULT_TEE_MAX_FILE_SIZE = _runtime_helpers.DEFAULT_TEE_MAX_FILE_SIZE
DEFAULT_COMMAND_USAGE_SINCE_DAYS = _runtime_helpers.DEFAULT_COMMAND_USAGE_SINCE_DAYS

now_iso = _runtime_helpers.now_iso
write_text = _runtime_helpers.write_text


def run_shell(cmd: str, cwd: Path, *, timeout_sec: int = DEFAULT_COMMAND_TIMEOUT_SEC) -> tuple[int, str]:
    return _runtime_helpers.run_shell(cmd, cwd, timeout_sec=timeout_sec)


_estimate_tokens = _runtime_helpers.estimate_tokens
_strip_ansi = _runtime_helpers.strip_ansi
_relative_display_path = _runtime_helpers.relative_display_path
compact_check_output = _runtime_helpers.compact_check_output

_write_recovery_output = _runtime_helpers.write_recovery_output


summarize_token_telemetry = _runtime_helpers.summarize_token_telemetry
_parse_iso_timestamp = _runtime_helpers.parse_iso_timestamp

_discover_command_usage = _runtime_helpers.discover_command_usage


_print_discover_text = _runtime_helpers.print_discover_text


def git_branch(root: Path) -> str:
    return _context_helpers.git_branch(root, run_shell=run_shell)


def infer_feature_from_state(root: Path) -> str | None:
    return _context_helpers.infer_feature_from_state(root, git_branch_fn=git_branch)


@dataclass
class CheckResult:
    name: str
    result: str  # pass|fail|skipped|warn
    details: str = ""
    cmd: str | None = None


InvariantFinding = _invariant_helpers.InvariantFinding


REVIEW_SCHEMA_VERSION = 4


load_workflow = _checks_config_helpers.load_workflow
packages_from_workflow = _checks_config_helpers.packages_from_workflow
_invariants_cfg = _checks_config_helpers.invariants_cfg
_entropy_cfg = _checks_config_helpers.entropy_cfg

_checks_runtime_cfg = partial(
    _checks_config_helpers.checks_runtime_cfg,
    default_command_timeout_sec=DEFAULT_COMMAND_TIMEOUT_SEC,
    default_output_compact_max_lines=DEFAULT_OUTPUT_COMPACT_MAX_LINES,
    default_output_compact_fail_tail_lines=DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES,
    default_output_compact_pass_lines=DEFAULT_OUTPUT_COMPACT_PASS_LINES,
    default_tee_min_chars=DEFAULT_TEE_MIN_CHARS,
    default_tee_max_files=DEFAULT_TEE_MAX_FILES,
    default_tee_max_file_size=DEFAULT_TEE_MAX_FILE_SIZE,
)



def _git_name_only(root: Path, cmd: str) -> list[str]:
    return _invariant_helpers.git_name_only(root, cmd, run_shell=run_shell)


def _changed_relpaths(root: Path, *, fallback: str = "none") -> set[str]:
    return _invariant_helpers.changed_relpaths(root, fallback=fallback, run_shell=run_shell)


def _git_ref_exists(root: Path, ref: str) -> bool:
    return _invariant_helpers.git_ref_exists(root, ref, run_shell=run_shell)


def _changed_relpaths_against_base(root: Path) -> set[str]:
    return _invariant_helpers.changed_relpaths_against_base(root, run_shell=run_shell)


def _changed_files(root: Path, *, fallback: str = "none") -> list[Path]:
    return _invariant_helpers.changed_files(root, fallback=fallback, run_shell=run_shell)


def _repo_files(root: Path) -> list[Path]:
    return _invariant_helpers.repo_files(root)


def _target_files_for_invariants(
    root: Path,
    cfg: dict[str, Any],
    *,
    changed_files_fallback: str = "none",
) -> list[Path]:
    return _invariant_helpers.target_files_for_invariants(
        root,
        cfg,
        changed_files_fallback=changed_files_fallback,
        run_shell=run_shell,
    )


def _command_prefers_repo_root(pkg_path: str, cmd: str) -> bool:
    return _invariant_helpers.command_prefers_repo_root(pkg_path, cmd)


def _is_spotless_not_configured(cmd: str, output: str) -> bool:
    return _invariant_helpers.is_spotless_not_configured(cmd, output)


def _path_matches_patterns(relpath: str, patterns: list[str]) -> bool:
    return _invariant_helpers.path_matches_patterns(relpath, patterns)


def run_invariant_checks(
    root: Path,
    wf: dict[str, Any],
    *,
    changed_files_fallback: str = "none",
) -> list[InvariantFinding]:
    return _invariant_helpers.run_invariant_checks(
        root,
        wf,
        changed_files_fallback=changed_files_fallback,
        invariants_cfg=_invariants_cfg,
        run_shell=run_shell,
    )


summarize_invariants = _invariant_helpers.summarize_invariants
_package_has_changes = _shared_package_has_changes


def run_package_checks(
    root: Path,
    pkgs: list[dict[str, Any]],
    *,
    changed_relpaths: set[str] | None = None,
    timeout_sec: int = DEFAULT_COMMAND_TIMEOUT_SEC,
    output_compaction: dict[str, Any] | None = None,
    output_recovery: dict[str, Any] | None = None,
    token_telemetry_enabled: bool = True,
) -> list[dict[str, Any]]:
    return _package_check_helpers.run_package_checks(
        root,
        pkgs,
        changed_relpaths=changed_relpaths,
        timeout_sec=timeout_sec,
        output_compaction=output_compaction,
        output_recovery=output_recovery,
        token_telemetry_enabled=token_telemetry_enabled,
        default_output_compact_max_lines=DEFAULT_OUTPUT_COMPACT_MAX_LINES,
        default_output_compact_fail_tail_lines=DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES,
        default_output_compact_pass_lines=DEFAULT_OUTPUT_COMPACT_PASS_LINES,
        default_tee_min_chars=DEFAULT_TEE_MIN_CHARS,
        default_tee_max_files=DEFAULT_TEE_MAX_FILES,
        default_tee_max_file_size=DEFAULT_TEE_MAX_FILE_SIZE,
        package_has_changes=_package_has_changes,
        command_prefers_repo_root=_command_prefers_repo_root,
        is_spotless_not_configured=_is_spotless_not_configured,
        run_shell=run_shell,
        compact_check_output=compact_check_output,
        write_recovery_output=_write_recovery_output,
        estimate_tokens=_estimate_tokens,
        relative_display_path=_relative_display_path,
    )


summarize_checksets = _package_check_helpers.summarize_checksets


write_verify_ci = partial(
    _package_check_helpers.write_verify_ci,
    now_iso=now_iso,
    summarize_invariants=summarize_invariants,
    summarize_token_telemetry=summarize_token_telemetry,
    write_json=write_json,
    write_text=write_text,
)


_normalize_plan_number = _shared_normalize_plan_number

_load_plan_contract_for_summary = partial(
    _summary_runtime_helpers.load_plan_contract_for_summary,
    normalize_plan_number=_normalize_plan_number,
    load_json=load_json,
)


def _head_commit_metadata(root: Path) -> dict[str, str]:
    return _summary_runtime_helpers.head_commit_metadata(root, run_shell=run_shell)


def _summary_changed_files(root: Path) -> tuple[list[str], str]:
    return _summary_runtime_helpers.summary_changed_files(
        root,
        git_name_only=_git_name_only,
        changed_relpaths=lambda repo_root: _changed_relpaths(repo_root, fallback="head"),
    )


_load_memory_task_issues = partial(
    _summary_helpers.load_memory_task_issues,
    normalize_plan_number=_normalize_plan_number,
)
_task_outputs = _summary_helpers.task_outputs
_task_verification_payload = _summary_helpers.task_verification_payload

_build_task_verification_entries = partial(
    _summary_helpers.build_task_verification_entries,
    normalize_plan_number=_normalize_plan_number,
    load_memory_task_issues_fn=_load_memory_task_issues,
)


_build_plan_verification_entries = _summary_helpers.build_plan_verification_entries
_build_summary_changes = _summary_helpers.build_summary_changes
_resolve_summary_outcome = _summary_helpers.resolve_summary_outcome


def write_summary(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    outcome: str = "auto",
    notes: list[str] | None = None,
) -> dict[str, Any]:
    try:
        from workflow_render import render_summary
    except ModuleNotFoundError:
        from .workflow_render import render_summary  # type: ignore
    return _summary_helpers.write_summary(
        root,
        feature,
        plan_number,
        outcome=outcome,
        notes=notes,
        normalize_plan_number=_normalize_plan_number,
        load_plan_contract=_load_plan_contract_for_summary,
        summary_changed_files=_summary_changed_files,
        head_commit_metadata=_head_commit_metadata,
        load_memory_task_issues_fn=_load_memory_task_issues,
        relative_display_path=_relative_display_path,
        now_iso=now_iso,
        write_json=write_json,
        write_text=write_text,
        render_summary=render_summary,
    )


_configured_reviewers = _review_helpers.configured_reviewers
_graph_impact_section = _review_helpers.graph_impact_section


def write_review(
    root: Path,
    feature: str | None,
    per_pkg: list[dict[str, Any]],
    invariant_findings: list[InvariantFinding],
) -> int:
    return _review_helpers.write_review(
        root,
        feature,
        per_pkg,
        invariant_findings,
        review_schema_version=REVIEW_SCHEMA_VERSION,
        now_iso=now_iso,
        git_branch=git_branch,
        summarize_checksets=summarize_checksets,
        summarize_invariants=summarize_invariants,
        summarize_token_telemetry=summarize_token_telemetry,
        changed_relpaths=lambda repo_root: _changed_relpaths(repo_root),
        write_json=write_json,
        write_text=write_text,
    )


_parse_iso_ts = _ship_ready_helpers.parse_iso_ts
_latest_summary_timestamp = partial(_ship_ready_helpers.latest_summary_timestamp, load_json=load_json)
_enforcement_level = _shared_enforcement_level

_cmd_ship_ready = partial(
    _ship_ready_helpers.cmd_ship_ready,
    load_json=load_json,
    subprocess_module=subprocess,
)


def _cmd_summarize(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    outcome: str = "auto",
    notes: list[str] | None = None,
    json_output: bool = False,
) -> int:
    return _summary_runtime_helpers.cmd_summarize(
        root,
        feature,
        plan_number,
        outcome=outcome,
        notes=notes,
        json_output=json_output,
        write_summary=write_summary,
        normalize_plan_number=_normalize_plan_number,
    )


_slugify = _entropy_helpers.slugify

_entropy_candidates = _entropy_helpers.entropy_candidates


write_entropy_task = partial(
    _entropy_helpers.write_entropy_task,
    now_iso=now_iso,
    write_text=write_text,
)


def _autobootstrap_packages_if_empty(
    root: Path,
    wf: dict[str, Any],
    *,
    cmd: str,
    timeout_sec: int,
) -> dict[str, Any]:
    return _entropy_helpers.autobootstrap_packages_if_empty(
        root,
        wf,
        cmd=cmd,
        timeout_sec=timeout_sec,
        packages_from_workflow=packages_from_workflow,
        run_shell=run_shell,
        load_workflow=load_workflow,
    )


def _cmd_doctor(root: Path, wf: dict, json_output: bool = False) -> int:
    _ = wf
    return _doctor_helpers.cmd_doctor(
        root,
        run_shell=run_shell,
        subprocess_module=subprocess,
        sys_executable=sys.executable,
        json_output=json_output,
    )


def main() -> int:
    parser = _cli_helpers.build_parser(default_command_usage_since_days=DEFAULT_COMMAND_USAGE_SINCE_DAYS)
    args = parser.parse_args()
    root = repo_root()
    return _cli_helpers.run_command(
        args,
        root=root,
        default_command_timeout_sec=DEFAULT_COMMAND_TIMEOUT_SEC,
        load_workflow=load_workflow,
        autobootstrap_packages_if_empty=_autobootstrap_packages_if_empty,
        checks_runtime_cfg=_checks_runtime_cfg,
        infer_feature_from_state=infer_feature_from_state,
        discover_command_usage=_discover_command_usage,
        print_discover_text=_print_discover_text,
        cmd_doctor=_cmd_doctor,
        cmd_summarize=_cmd_summarize,
        cmd_ship_ready=_cmd_ship_ready,
        run_invariant_checks=run_invariant_checks,
        entropy_cfg=_entropy_cfg,
        summarize_invariants=summarize_invariants,
        entropy_candidates=_entropy_candidates,
        write_entropy_task=write_entropy_task,
        packages_from_workflow=packages_from_workflow,
        changed_relpaths=_changed_relpaths,
        changed_relpaths_against_base=_changed_relpaths_against_base,
        run_package_checks=run_package_checks,
        write_verify_ci=write_verify_ci,
        write_review=write_review,
    )


if __name__ == "__main__":
    raise SystemExit(main())
