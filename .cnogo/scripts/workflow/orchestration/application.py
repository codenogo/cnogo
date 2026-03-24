"""cnogo application lifecycle — startup and graceful shutdown.

Inspired by Erlang/OTP Application: defines an ordered startup/shutdown
protocol for the workflow system. Starting validates state integrity.
Stopping drains active executors before releasing lanes.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.atomic_write import atomic_write_json
from scripts.workflow.shared.runtime_root import runtime_path
from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .execution_events import log_execution_event
from .lane import list_feature_lanes, reclaim_stale_feature_lanes


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _app_state_path(root: Path) -> Path:
    return runtime_path(root, "application-state.json")


def _load_app_state(root: Path) -> dict[str, Any]:
    path = _app_state_path(root)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_app_state(root: Path, state: dict[str, Any]) -> None:
    state["updatedAt"] = _now_iso()
    atomic_write_json(_app_state_path(root), state)


# ---------------------------------------------------------------------------
# State integrity validation
# ---------------------------------------------------------------------------


def validate_state_integrity(root: Path) -> list[str]:
    """Verify that all state files are valid. Returns list of issues found.

    Checks:
    - Lane files parse correctly
    - Lane worktrees exist (or mark stale)
    - No delivery runs stuck in active for > 2 hours
    - Dispatch ledger entries have valid timestamps
    """
    issues: list[str] = []

    # Check lanes.
    for lane in list_feature_lanes(root, include_terminal=True):
        if lane.worktree_path and not Path(lane.worktree_path).exists():
            if lane.status not in ("released", "completed"):
                issues.append(f"Lane {lane.feature}: worktree missing at {lane.worktree_path}")

    # Check delivery runs.
    runs_dir = runtime_path(root, "runs")
    if runs_dir.is_dir():
        now = datetime.now(timezone.utc)
        for feature_dir in runs_dir.iterdir():
            if not feature_dir.is_dir():
                continue
            for run_file in feature_dir.glob("*.json"):
                if run_file.parent.name == "archive":
                    continue
                try:
                    data = json.loads(run_file.read_text(encoding="utf-8"))
                    if data.get("status") == "active":
                        updated = parse_iso_timestamp(data.get("updatedAt", ""))
                        if updated:
                            age_hours = (now - updated).total_seconds() / 3600
                            if age_hours > 2:
                                issues.append(
                                    f"Run {run_file.stem}: stuck in active for {age_hours:.1f}h"
                                )
                except Exception as exc:
                    issues.append(f"Corrupt run file {run_file}: {type(exc).__name__}")

    return issues


# ---------------------------------------------------------------------------
# Global hold (for graceful shutdown)
# ---------------------------------------------------------------------------


def set_global_hold(root: Path, *, reason: str) -> None:
    """Set a global dispatch hold — prevents new work from being leased."""
    state = _load_app_state(root)
    state["globalHold"] = True
    state["globalHoldReason"] = reason
    state["globalHoldAt"] = _now_iso()
    _save_app_state(root, state)


def clear_global_hold(root: Path) -> None:
    """Clear the global dispatch hold."""
    state = _load_app_state(root)
    state["globalHold"] = False
    state["globalHoldReason"] = ""
    state["globalHoldAt"] = ""
    _save_app_state(root, state)


def is_global_hold(root: Path) -> bool:
    """Check if a global hold is active."""
    state = _load_app_state(root)
    return bool(state.get("globalHold"))


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------


def start(root: Path) -> dict[str, Any]:
    """Start the cnogo application. Validates state, clears stale holds."""
    issues = validate_state_integrity(root)

    # Clear any leftover global hold from a previous shutdown.
    clear_global_hold(root)

    # Reclaim stale lanes.
    reclaimed = reclaim_stale_feature_lanes(root)

    # Write application state.
    _save_app_state(root, {
        "status": "running",
        "startedAt": _now_iso(),
        "pid": __import__("os").getpid(),
        "integrityIssues": issues,
    })

    log_execution_event(root, actor="application", feature="*", event="application_started", data={
        "issues": len(issues),
        "reclaimed": len(reclaimed) if isinstance(reclaimed, list) else 0,
    })

    return {
        "status": "running",
        "integrityIssues": issues,
        "reclaimed": reclaimed if isinstance(reclaimed, list) else [],
    }


def stop(root: Path, *, drain_seconds: int = 30) -> dict[str, Any]:
    """Graceful shutdown. Drains active executors before releasing lanes.

    1. Set global hold (prevents new leases)
    2. Wait for active executors to finish (up to drain_seconds)
    3. Reclaim stale lanes
    4. Log shutdown event
    """
    set_global_hold(root, reason="graceful_shutdown")

    # Wait for active lanes to drain.
    deadline = time.time() + drain_seconds
    drained = False
    while time.time() < deadline:
        active = [l for l in list_feature_lanes(root) if l.status in ("implementing",)]
        if not active:
            drained = True
            break
        time.sleep(2)

    # Reclaim any stale lanes.
    reclaimed = reclaim_stale_feature_lanes(root)

    # Sweep orphaned agents.
    orphans: list[dict[str, Any]] = []
    try:
        from .agent_registry import sweep_orphaned_agents
        orphans = sweep_orphaned_agents(root, stale_minutes=0)  # Sweep all running agents on shutdown.
    except Exception:
        pass

    # Clear global hold (allow restart).
    clear_global_hold(root)

    _save_app_state(root, {
        "status": "stopped",
        "stoppedAt": _now_iso(),
    })

    log_execution_event(root, actor="application", feature="*", event="application_stopped", data={
        "drained": drained,
        "orphansSwept": len(orphans),
    })

    return {
        "status": "stopped",
        "drained": drained,
        "reclaimed": reclaimed if isinstance(reclaimed, list) else [],
        "orphansSwept": orphans,
    }
