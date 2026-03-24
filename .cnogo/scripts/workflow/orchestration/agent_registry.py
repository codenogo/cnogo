"""Persistent agent registry for tracking spawned agents.

Inspired by Erlang/OTP Process.monitor — provides a persistent record of
which agents are alive, so orphaned agents can be detected and cleaned up
even if the supervisor session is lost.

Registry file: .cnogo/agent-registry.json
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


def _registry_path(root: Path) -> Path:
    return runtime_path(root, "agent-registry.json")


def _load_registry(root: Path) -> dict[str, Any]:
    path = _registry_path(root)
    if not path.exists():
        return {"agents": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and "agents" in data else {"agents": {}}
    except Exception:
        return {"agents": {}}


def _save_registry(root: Path, registry: dict[str, Any]) -> None:
    registry["updatedAt"] = _now_iso()
    atomic_write_json(_registry_path(root), registry)


def register_agent(
    root: Path,
    *,
    name: str,
    kind: str,
    feature: str,
    spawned_by: str,
    task_index: int | None = None,
    deadline_minutes: int = 90,
) -> dict[str, Any]:
    """Register a spawned agent in the persistent registry."""
    registry = _load_registry(root)
    now = _now_iso()
    deadline_dt = datetime.now(timezone.utc) + __import__("datetime").timedelta(minutes=deadline_minutes)
    entry: dict[str, Any] = {
        "kind": kind,
        "feature": feature,
        "spawnedAt": now,
        "spawnedBy": spawned_by,
        "status": "running",
        "lastHeartbeat": now,
        "deadline": deadline_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if task_index is not None:
        entry["taskIndex"] = task_index
    registry["agents"][name] = entry
    _save_registry(root, registry)
    return entry


def deregister_agent(root: Path, *, name: str, status: str = "completed") -> None:
    """Remove an agent from the registry (on completion or cleanup)."""
    registry = _load_registry(root)
    if name in registry["agents"]:
        registry["agents"][name]["status"] = status
        registry["agents"][name]["completedAt"] = _now_iso()
    _save_registry(root, registry)


def heartbeat_agent(root: Path, *, name: str) -> None:
    """Update an agent's heartbeat timestamp."""
    registry = _load_registry(root)
    if name in registry["agents"]:
        registry["agents"][name]["lastHeartbeat"] = _now_iso()
        _save_registry(root, registry)


def list_agents(root: Path, *, status: str | None = None) -> list[dict[str, Any]]:
    """List registered agents, optionally filtered by status."""
    registry = _load_registry(root)
    agents: list[dict[str, Any]] = []
    for name, entry in registry.get("agents", {}).items():
        if status is not None and entry.get("status") != status:
            continue
        agents.append({"name": name, **entry})
    return agents


def sweep_orphaned_agents(root: Path, *, stale_minutes: int = 60) -> list[dict[str, Any]]:
    """Find and deregister agents that have exceeded their deadline or are stale.

    An agent is orphaned if:
    1. Its deadline has passed, OR
    2. Its lastHeartbeat is older than stale_minutes

    Returns the list of swept agents.
    """
    registry = _load_registry(root)
    now = datetime.now(timezone.utc)
    swept: list[dict[str, Any]] = []

    for name, entry in list(registry.get("agents", {}).items()):
        if entry.get("status") != "running":
            continue

        # Check deadline.
        deadline_str = entry.get("deadline", "")
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
                if now > deadline:
                    entry["status"] = "orphaned"
                    entry["orphanReason"] = "deadline_exceeded"
                    entry["orphanedAt"] = _now_iso()
                    swept.append({"name": name, **entry})
                    continue
            except (ValueError, TypeError):
                pass

        # Check heartbeat staleness.
        heartbeat_str = entry.get("lastHeartbeat", "")
        if heartbeat_str:
            try:
                heartbeat = datetime.fromisoformat(heartbeat_str.replace("Z", "+00:00"))
                age_minutes = (now - heartbeat).total_seconds() / 60
                if age_minutes > stale_minutes:
                    entry["status"] = "orphaned"
                    entry["orphanReason"] = "stale_heartbeat"
                    entry["orphanedAt"] = _now_iso()
                    swept.append({"name": name, **entry})
                    continue
            except (ValueError, TypeError):
                pass

    if swept:
        _save_registry(root, registry)
    return swept
