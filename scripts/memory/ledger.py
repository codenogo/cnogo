#!/usr/bin/env python3
"""Run coordination ledger for cnogo team lifecycle.

Manages .cnogo/run.json — a lightweight coordination file that tracks
the current team run's state (phase, issue states, etc.).

All timestamps are UTC ISO-8601. Atomic writes prevent torn reads.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CNOGO_DIR = ".cnogo"
_RUN_FILE = "run.json"


def generate_run_id(feature: str) -> str:
    """Generate a unique run ID: {feature}-{YYYYMMDD}-{HHMMSS}."""
    now = datetime.now(timezone.utc)
    return f"{feature}-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"


def load_ledger(root: Path) -> dict[str, Any] | None:
    """Read .cnogo/run.json. Returns None if missing."""
    path = root / _CNOGO_DIR / _RUN_FILE
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def save_ledger(root: Path, data: dict[str, Any]) -> None:
    """Atomic write of .cnogo/run.json."""
    path = root / _CNOGO_DIR / _RUN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=f"{_RUN_FILE}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def create_ledger(
    root: Path,
    *,
    run_id: str,
    feature: str,
    team_id: str,
    epic_id: str,
) -> dict[str, Any]:
    """Create a new run ledger with phase='setup'."""
    now = datetime.now(timezone.utc).isoformat()
    data: dict[str, Any] = {
        "run_id": run_id,
        "feature": feature,
        "phase": "setup",
        "team_id": team_id,
        "epic_id": epic_id,
        "plan_ids": [],
        "issue_states": {},
        "outputs_hash": "",
        "created_at": now,
        "updated_at": now,
    }
    save_ledger(root, data)
    return data


def update_ledger(root: Path, **fields: Any) -> dict[str, Any]:
    """Load, merge fields, set updated_at, save, return."""
    data = load_ledger(root)
    if data is None:
        data = {}
    data.update(fields)
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_ledger(root, data)
    return data
