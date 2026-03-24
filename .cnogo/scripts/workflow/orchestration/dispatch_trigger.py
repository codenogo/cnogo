"""Event-driven dispatch triggers.

Inspired by the Reactor pattern: instead of polling on a fixed interval,
state transitions write trigger files that the scheduler picks up on its
next tick to run dispatch immediately.

Trigger files are at .cnogo/dispatch-triggers/<feature>.json. Each contains
the feature slug, reason for the trigger, and timestamp. The scheduler
checks for triggers at the start of each tick and clears them after dispatch.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.atomic_write import atomic_write_json
from scripts.workflow.shared.runtime_root import runtime_path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _trigger_dir(root: Path) -> Path:
    return runtime_path(root, "dispatch-triggers")


def touch_dispatch_trigger(root: Path, feature: str, *, reason: str) -> Path:
    """Write a dispatch trigger file for a feature.

    Called when a state transition makes a feature eligible for the next
    dispatch stage (e.g., review-ready → auto-review, ship-ready → auto-ship).
    """
    path = _trigger_dir(root) / f"{feature}.json"
    atomic_write_json(path, {
        "feature": feature,
        "reason": reason,
        "ts": _now_iso(),
    }, sort_keys=False)
    return path


def consume_dispatch_triggers(root: Path) -> list[dict[str, Any]]:
    """Read and delete all pending dispatch triggers.

    Returns the list of trigger payloads. Triggers are consumed (deleted)
    atomically — each trigger is removed as soon as it's read.
    """
    trigger_dir = _trigger_dir(root)
    if not trigger_dir.is_dir():
        return []
    triggers: list[dict[str, Any]] = []
    for path in sorted(trigger_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                triggers.append(data)
            path.unlink()
        except Exception:
            # Corrupt trigger — delete it anyway.
            try:
                path.unlink()
            except OSError:
                pass
    return triggers


def has_pending_triggers(root: Path) -> bool:
    """Check if any dispatch triggers are pending (without consuming them)."""
    trigger_dir = _trigger_dir(root)
    if not trigger_dir.is_dir():
        return False
    return any(trigger_dir.glob("*.json"))
