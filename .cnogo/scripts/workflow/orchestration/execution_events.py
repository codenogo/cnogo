"""Execution event logging for the autonomous run loop.

Append-only JSONL log at .cnogo/execution-log.jsonl.
Each event: {"ts", "actor", "feature", "event", ...data}.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.runtime_root import runtime_path


_LOG_FILENAME = "execution-log.jsonl"
_HEARTBEAT_PREFIX = "agent-heartbeat-task-"
_MAX_LOG_LINES = 10_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_path(root: Path) -> Path:
    return runtime_path(root, _LOG_FILENAME)


def log_execution_event(
    root: Path,
    *,
    actor: str,
    feature: str,
    event: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one event to the execution log. Returns the event dict."""
    entry: dict[str, Any] = {
        "ts": _now_iso(),
        "actor": actor,
        "feature": feature,
        "event": event,
    }
    if data:
        entry.update(data)
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return entry


def read_execution_log(
    root: Path,
    *,
    feature: str | None = None,
    event: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Read recent events from the execution log, newest first."""
    path = log_path(root)
    if not path.exists():
        return []
    lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return []
    entries: list[dict[str, Any]] = []
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        if feature and str(entry.get("feature", "")).strip() != feature:
            continue
        if event and str(entry.get("event", "")).strip() != event:
            continue
        entries.append(entry)
        if len(entries) >= limit:
            break
    return entries


def truncate_log(root: Path, *, keep: int = _MAX_LOG_LINES) -> int:
    """Truncate the log to the most recent N lines. Returns lines removed."""
    path = log_path(root)
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except Exception:
        return 0
    if len(lines) <= keep:
        return 0
    removed = len(lines) - keep
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(lines[removed:])
    return removed


# --- Agent heartbeat files ---


def heartbeat_path(worktree: Path, task_index: int) -> Path:
    return worktree / ".cnogo" / f"{_HEARTBEAT_PREFIX}{task_index}.json"


def write_heartbeat(
    worktree: Path,
    *,
    task_index: int,
    agent_id: str,
    last_action: str,
) -> dict[str, Any]:
    """Write a heartbeat file for an implementer agent."""
    entry = {
        "agentId": agent_id,
        "taskIndex": task_index,
        "lastAction": last_action,
        "updatedAt": _now_iso(),
    }
    path = heartbeat_path(worktree, task_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    return entry


def read_heartbeat(worktree: Path, task_index: int) -> dict[str, Any] | None:
    """Read a heartbeat file. Returns None if missing or unreadable."""
    path = heartbeat_path(worktree, task_index)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def list_heartbeats(worktree: Path) -> list[dict[str, Any]]:
    """List all heartbeat files in a worktree."""
    cnogo_dir = worktree / ".cnogo"
    if not cnogo_dir.is_dir():
        return []
    heartbeats: list[dict[str, Any]] = []
    for path in sorted(cnogo_dir.glob(f"{_HEARTBEAT_PREFIX}*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                heartbeats.append(data)
        except Exception:
            continue
    return heartbeats


def is_heartbeat_stale(heartbeat: dict[str, Any], *, stale_minutes: int = 15) -> bool:
    """Check if a heartbeat is older than the threshold."""
    updated = str(heartbeat.get("updatedAt", "")).strip()
    if not updated:
        return True
    try:
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - ts
        return age.total_seconds() > stale_minutes * 60
    except Exception:
        return True


# --- Loop status rendering ---


def render_loop_status(
    root: Path,
    *,
    include_events: int = 5,
) -> str:
    """Render unified loop status for CLI display."""
    from .lane import list_feature_lanes, feature_lane_health
    from .delivery_run import latest_delivery_run

    lines: list[str] = []
    lanes = list_feature_lanes(root)
    active = [lane for lane in lanes if lane.status not in {"released", "completed"}]

    lines.append(f"Run Loop: {len(active)} active lane(s), {len(lanes)} total")
    lines.append("")

    for lane in active:
        health = feature_lane_health(root, lane)
        stale_flag = " (STALE)" if health.get("stale") else ""
        lines.append(f"Feature: {lane.feature} [{lane.status}]{stale_flag}")
        lines.append(f"  Lane: {lane.lane_id} (owner: {lane.lease_owner})")
        if lane.worktree_path:
            lines.append(f"  Worktree: {lane.worktree_path}")

        run = latest_delivery_run(root, lane.feature)
        if run is not None:
            tasks = getattr(run, "tasks", []) or []
            total = len(tasks)
            completed = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "completed")
            active_tasks = [t for t in tasks if isinstance(t, dict) and t.get("status") in {"ready", "in_progress"}]
            lines.append(f"  Tasks: {completed}/{total} complete, {len(active_tasks)} active")
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                idx = task.get("taskIndex", "?")
                status = task.get("status", "?")
                title = str(task.get("title", "")).strip()[:60]
                icon = {"completed": "done", "ready": "ready", "in_progress": "running", "failed": "FAILED"}.get(status, status)
                assignee = f" (@{task.get('assignee', '')})" if task.get("assignee") else ""
                lines.append(f"    [{idx}] {icon}: {title}{assignee}")

                # Check heartbeat if worktree exists
                wt = str(task.get("worktreePath", "")).strip()
                if wt and status == "in_progress":
                    hb = read_heartbeat(Path(wt), int(idx)) if wt else None
                    if hb is None:
                        hb = read_heartbeat(Path(lane.worktree_path), int(idx)) if lane.worktree_path else None
                    if hb:
                        stale = is_heartbeat_stale(hb)
                        action = str(hb.get("lastAction", "")).strip()[:50]
                        flag = " STALE" if stale else ""
                        lines.append(f"         heartbeat: {action}{flag}")

            # Review/ship state
            review = getattr(run, "review", {}) or {}
            ship = getattr(run, "ship", {}) or {}
            if str(review.get("status", "")).strip() not in {"", "pending"}:
                lines.append(f"  Review: {review.get('status')} (verdict: {review.get('finalVerdict', 'pending')})")
            if str(ship.get("status", "")).strip() not in {"", "pending"}:
                lines.append(f"  Ship: {ship.get('status')}")
        lines.append("")

    # Recent events
    events = read_execution_log(root, limit=include_events)
    if events:
        lines.append("Recent Events:")
        for ev in events:
            ts = str(ev.get("ts", "")).strip()
            ts_short = ts[11:19] if len(ts) >= 19 else ts
            actor = str(ev.get("actor", "")).strip()
            feature = str(ev.get("feature", "")).strip()
            event_name = str(ev.get("event", "")).strip()
            lines.append(f"  {ts_short} [{feature}] {event_name} ({actor})")
        lines.append("")

    return "\n".join(lines)
