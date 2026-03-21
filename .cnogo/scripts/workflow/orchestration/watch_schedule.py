"""Recurring watch patrol scheduling and state helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import (
    agent_team_settings,
    load_workflow_config,
    watch_settings_cfg,
)
from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .watch import watch_delivery_runs
from .watch_artifacts import (
    attention_queue_path,
    load_attention_queue,
    load_watch_report,
    persist_watch_report,
    watch_dir,
    watch_history_dir,
    watch_report_path,
)

WATCH_STATE_SCHEMA_VERSION = 1
_WATCH_STATE_FILE = "state.json"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _attention_result(queue: dict[str, Any] | None) -> str:
    items = queue.get("items", []) if isinstance(queue, dict) else []
    if not isinstance(items, list):
        return "ok"
    severities = {
        str(item.get("severity", "")).strip()
        for item in items
        if isinstance(item, dict)
    }
    if "fail" in severities:
        return "fail"
    if items:
        return "warn"
    return "ok"


def _prune_history(root: Path, *, history_limit: int) -> None:
    history_root = watch_history_dir(root)
    if history_limit <= 0 or not history_root.is_dir():
        return
    snapshots = sorted(history_root.glob("*.json"), reverse=True)
    for stale_path in snapshots[history_limit:]:
        try:
            stale_path.unlink()
        except FileNotFoundError:
            continue


def watch_state_path(root: Path) -> Path:
    return watch_dir(root) / _WATCH_STATE_FILE


def load_watch_state(root: Path) -> dict[str, Any] | None:
    return _read_json(watch_state_path(root))


def watch_schedule_status(
    root: Path,
    *,
    cfg: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = watch_settings_cfg(workflow_cfg)
    state = load_watch_state(root) or {}
    now_dt = now or _now_utc()
    last_patrol = parse_iso_timestamp(state.get("lastPatrolAt"))
    next_patrol = None
    if settings["enabled"]:
        if last_patrol is None:
            next_patrol = now_dt
        else:
            next_patrol = last_patrol + timedelta(minutes=settings["patrolIntervalMinutes"])
    due = bool(settings["enabled"] and next_patrol is not None and now_dt >= next_patrol)
    if not settings["enabled"]:
        reason = "Watch schedule is disabled in WORKFLOW.json."
    elif last_patrol is None:
        reason = "No recurring watch patrol has been recorded yet."
    elif due:
        reason = "Watch patrol interval has elapsed."
    else:
        reason = "Watch patrol is not due yet."
    attention = load_attention_queue(root)
    report = load_watch_report(root)
    return {
        "enabled": settings["enabled"],
        "patrolIntervalMinutes": settings["patrolIntervalMinutes"],
        "historyLimit": settings["historyLimit"],
        "attentionLimit": settings["attentionLimit"],
        "due": due,
        "reason": reason,
        "lastPatrolAt": state.get("lastPatrolAt", ""),
        "nextPatrolAt": _iso_utc(next_patrol) if next_patrol is not None else "",
        "lastResult": str(state.get("lastResult", _attention_result(attention))),
        "lastAttentionSummary": dict(state.get("lastAttentionSummary", {}))
        if isinstance(state.get("lastAttentionSummary"), dict)
        else dict(attention.get("summary", {})) if isinstance(attention, dict) else {},
        "lastDeltaSummary": dict(state.get("lastDeltaSummary", {}))
        if isinstance(state.get("lastDeltaSummary"), dict)
        else {},
        "lastSnapshotPath": str(state.get("lastSnapshotPath", "")),
        "statePath": str(watch_state_path(root)),
        "reportPath": str(watch_report_path(root)) if watch_report_path(root).exists() else "",
        "attentionPath": str(attention_queue_path(root)) if attention_queue_path(root).exists() else "",
        "reportCheckedAt": str(report.get("checkedAt", "")) if isinstance(report, dict) else "",
    }


def record_watch_patrol_state(
    root: Path,
    persisted: dict[str, Any],
    *,
    cfg: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = watch_settings_cfg(workflow_cfg)
    now_dt = now or _now_utc()
    report = persisted.get("report", {}) if isinstance(persisted.get("report"), dict) else {}
    attention = persisted.get("attention", {}) if isinstance(persisted.get("attention"), dict) else {}
    delta = persisted.get("delta", {}) if isinstance(persisted.get("delta"), dict) else {}
    snapshot = persisted.get("snapshot", {}) if isinstance(persisted.get("snapshot"), dict) else {}
    checked_at = parse_iso_timestamp(report.get("checkedAt")) or now_dt
    next_patrol = checked_at + timedelta(minutes=settings["patrolIntervalMinutes"]) if settings["enabled"] else None
    state = {
        "schemaVersion": WATCH_STATE_SCHEMA_VERSION,
        "enabled": settings["enabled"],
        "patrolIntervalMinutes": settings["patrolIntervalMinutes"],
        "historyLimit": settings["historyLimit"],
        "attentionLimit": settings["attentionLimit"],
        "lastPatrolAt": _iso_utc(checked_at),
        "nextPatrolAt": _iso_utc(next_patrol) if next_patrol is not None else "",
        "lastResult": _attention_result(attention),
        "lastAttentionSummary": dict(attention.get("summary", {}))
        if isinstance(attention.get("summary"), dict)
        else {},
        "lastDeltaSummary": dict(delta.get("summary", {}))
        if isinstance(delta.get("summary"), dict)
        else {},
        "lastReportPath": str(report.get("paths", {}).get("report", "")) if isinstance(report.get("paths"), dict) else "",
        "lastAttentionPath": str(attention.get("paths", {}).get("attention", ""))
        if isinstance(attention.get("paths"), dict)
        else "",
        "lastSnapshotPath": str(report.get("paths", {}).get("snapshot", ""))
        if isinstance(report.get("paths"), dict)
        else "",
    }
    _write_json(watch_state_path(root), state)
    _prune_history(root, history_limit=settings["historyLimit"])
    return state


def run_watch_tick(
    root: Path,
    *,
    stale_minutes: int | None = None,
    review_stale_minutes: int | None = None,
    include_terminal: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    cfg = load_workflow_config(root)
    status = watch_schedule_status(root, cfg=cfg)
    latest_report = load_watch_report(root)
    attention = load_attention_queue(root)
    if not force and (not status["enabled"] or not status["due"]):
        return {
            "executed": False,
            "reason": status["reason"],
            "schedule": status,
            "report": latest_report or {},
            "attention": attention or {},
            "delta": {},
            "snapshot": {},
        }

    stale_cfg = agent_team_settings(cfg).get("staleIndicatorMinutes", 10)
    stale_threshold = stale_minutes if isinstance(stale_minutes, int) and stale_minutes > 0 else stale_cfg
    review_threshold = (
        review_stale_minutes
        if isinstance(review_stale_minutes, int) and review_stale_minutes > 0
        else max(stale_threshold * 6, 60)
    )
    report = watch_delivery_runs(
        root,
        stale_minutes=stale_threshold,
        review_stale_minutes=review_threshold,
        include_terminal=include_terminal,
    )
    persisted = persist_watch_report(root, report)
    record_watch_patrol_state(root, persisted, cfg=cfg)
    schedule = watch_schedule_status(root, cfg=cfg)
    return {
        "executed": True,
        "reason": "Forced watch patrol executed." if force and not status["due"] else status["reason"],
        "schedule": schedule,
        "report": persisted.get("report", {}),
        "attention": persisted.get("attention", {}),
        "delta": persisted.get("delta", {}),
        "snapshot": persisted.get("snapshot", {}),
    }
