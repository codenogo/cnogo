"""Summary runtime helpers for workflow checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def load_plan_contract_for_summary(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    normalize_plan_number: Callable[[Any], str],
    load_json: Callable[[Path], Any],
) -> tuple[Path, dict[str, Any]]:
    normalized = normalize_plan_number(plan_number)
    plan_path = root / "docs" / "planning" / "work" / "features" / feature / f"{normalized}-PLAN.json"
    plan = load_json(plan_path)
    if not isinstance(plan, dict):
        raise ValueError(f"Plan contract must be a JSON object: {plan_path}")
    return plan_path, plan


def head_commit_metadata(
    root: Path,
    *,
    run_shell: Callable[..., tuple[int, str]],
) -> dict[str, str]:
    rc_hash, commit_hash = run_shell("git rev-parse --short HEAD", cwd=root, timeout_sec=30)
    if rc_hash != 0:
        return {}
    rc_msg, message = run_shell("git log -1 --pretty=%s", cwd=root, timeout_sec=30)
    return {
        "hash": commit_hash.strip(),
        "message": message.strip() if rc_msg == 0 else "",
    }


def summary_changed_files(
    root: Path,
    *,
    git_name_only: Callable[[Path, str], list[str]],
    changed_relpaths: Callable[[Path], set[str]],
) -> tuple[list[str], str]:
    working_tree = sorted(
        set(git_name_only(root, "git diff --name-only --diff-filter=ACMR HEAD"))
    )
    if working_tree:
        return working_tree, "git:working-tree"
    changed = sorted(
        set(git_name_only(root, "git diff-tree --no-commit-id --name-only --diff-filter=ACMR -r HEAD"))
    )
    if changed:
        return changed, "git:HEAD"
    fallback = sorted(changed_relpaths(root))
    if fallback:
        return fallback, "git:fallback"
    return [], "git:none"


def cmd_summarize(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    outcome: str,
    notes: list[str] | None,
    json_output: bool,
    write_summary: Callable[..., dict[str, Any]],
    normalize_plan_number: Callable[[Any], str],
) -> int:
    contract = write_summary(root, feature, plan_number, outcome=outcome, notes=notes or [])
    summary_path = root / "docs" / "planning" / "work" / "features" / feature / f"{normalize_plan_number(plan_number)}-SUMMARY.json"
    if json_output:
        print(json.dumps(contract, indent=2, sort_keys=True))
    else:
        print(f"Wrote {summary_path}")
    return 0
