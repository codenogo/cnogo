"""Context inference helpers for workflow checks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable


def git_branch(root: Path, *, run_shell: Callable[..., tuple[int, str]]) -> str:
    rc, output = run_shell("git branch --show-current", cwd=root)
    return output.strip() if rc == 0 else ""


def infer_feature_from_state(
    root: Path,
    *,
    git_branch_fn: Callable[[Path], str],
) -> str | None:
    """Infer the active feature slug from memory engine, with branch fallback."""
    try:
        sys.path.insert(0, str(root))
        from scripts.memory import is_initialized, list_issues

        if is_initialized(root):
            for status in ("in_progress", "open"):
                epics = list_issues(issue_type="epic", status=status, root=root)
                for epic in epics:
                    if epic.feature_slug:
                        return epic.feature_slug
    except Exception:
        pass

    branch = git_branch_fn(root)
    if branch and "/" in branch:
        slug = branch.split("/", 1)[1]
        if slug and slug not in {"main", "master", "develop"}:
            return slug
    return None
