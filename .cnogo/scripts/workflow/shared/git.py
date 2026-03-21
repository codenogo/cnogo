"""Shared git/repo helpers for workflow tooling."""

from __future__ import annotations

import subprocess
from pathlib import Path


def repo_root(start: Path) -> Path:
    """Resolve repo root from a user-supplied path."""
    candidate = start.resolve()
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=candidate,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return Path(output)
    except Exception:
        return candidate


def is_git_repo(root: Path) -> bool:
    try:
        subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def staged_files(root: Path) -> list[Path]:
    output = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=root,
        stderr=subprocess.DEVNULL,
    ).decode()
    files: list[Path] = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            files.append(root / line)
    return files
