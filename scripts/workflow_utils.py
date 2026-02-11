#!/usr/bin/env python3
"""
Shared utilities for workflow scripts.

Consolidates duplicated functions (repo_root, load_json, write_json, load_workflow)
into a single module. All stdlib-only, no external dependencies.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

_repo_root_cache: Path | None = None


def repo_root() -> Path:
    """Return the repository root via git, with cwd fallback."""
    global _repo_root_cache
    if _repo_root_cache is not None:
        return _repo_root_cache
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        _repo_root_cache = Path(out)
    except Exception:
        _repo_root_cache = Path.cwd()
    return _repo_root_cache


def load_json(path: Path) -> Any:
    """Load and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Write data to a JSON file with 2-space indent and trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_workflow() -> dict[str, Any]:
    """Load docs/planning/WORKFLOW.json relative to repo root."""
    root = repo_root()
    p = root / "docs" / "planning" / "WORKFLOW.json"
    if not p.exists():
        return {}
    try:
        cfg = load_json(p)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}
