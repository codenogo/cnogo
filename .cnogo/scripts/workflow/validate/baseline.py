"""Baseline snapshot helpers for workflow validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_BASELINE_FILE = "validate-baseline.json"
_LATEST_FILE = "validate-latest.json"
_CNOGO_DIR = ".cnogo"


def finding_to_warning(finding: Any) -> dict[str, Any]:
    file_part = getattr(finding, "path", "") or ""
    raw = f"{getattr(finding, 'level', '')}|{file_part}|{getattr(finding, 'message', '')}"
    sig = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return {
        "level": getattr(finding, "level", ""),
        "file": getattr(finding, "path", None),
        "message": getattr(finding, "message", ""),
        "signature": sig,
    }


def save_baseline(warnings: list[dict[str, Any]], root: Path) -> Path:
    out_dir = root / _CNOGO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _BASELINE_FILE
    sorted_warnings = sorted(warnings, key=lambda warning: warning.get("signature", ""))
    path.write_text(
        json.dumps(sorted_warnings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_baseline(root: Path) -> list[dict[str, Any]] | None:
    path = root / _CNOGO_DIR / _BASELINE_FILE
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    except (json.JSONDecodeError, OSError):
        return None


def save_latest(warnings: list[dict[str, Any]], root: Path) -> None:
    out_dir = root / _CNOGO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / _LATEST_FILE
    sorted_warnings = sorted(warnings, key=lambda warning: warning.get("signature", ""))
    path.write_text(
        json.dumps(sorted_warnings, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def diff_baselines(
    baseline: list[dict[str, Any]],
    current: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    base_sigs = {warning["signature"]: warning for warning in baseline}
    curr_sigs = {warning["signature"]: warning for warning in current}

    new = [warning for sig, warning in curr_sigs.items() if sig not in base_sigs]
    resolved = [warning for sig, warning in base_sigs.items() if sig not in curr_sigs]
    unchanged = [warning for sig, warning in curr_sigs.items() if sig in base_sigs]

    return {"new": new, "resolved": resolved, "unchanged": unchanged}
