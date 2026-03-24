"""Hybrid internal scheduler for patrol and work-order maintenance."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.atomic_write import atomic_write_json
from scripts.workflow.shared.config import load_workflow_config, scheduler_settings_cfg
from scripts.workflow.shared.runtime_root import runtime_path
from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .watch_schedule import run_watch_tick
from .dispatcher import dispatch_ready_work, sync_shape_feedback
from .work_order import sync_all_work_orders

SCHEDULER_STATE_SCHEMA_VERSION = 1
SCHEDULER_JOB_NAMES = ("watch_patrol", "work_order_sync", "dispatch_ready", "feedback_sync")

_SCHEDULER_DIR = Path(".cnogo") / "scheduler"
_STATE_FILE = "state.json"
_PID_FILE = "worker.pid"
_LOCK_FILE = "lock"
_EVENTS_FILE = "events.jsonl"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scheduler_dir(root: Path) -> Path:
    return runtime_path(root, "scheduler")


def scheduler_state_path(root: Path) -> Path:
    return scheduler_dir(root) / _STATE_FILE


def scheduler_pid_path(root: Path) -> Path:
    return scheduler_dir(root) / _PID_FILE


def scheduler_lock_path(root: Path) -> Path:
    return scheduler_dir(root) / _LOCK_FILE


def scheduler_events_path(root: Path) -> Path:
    return scheduler_dir(root) / _EVENTS_FILE


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(path, payload)


def _append_event(root: Path, payload: dict[str, Any]) -> None:
    path = scheduler_events_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def load_scheduler_state(root: Path) -> dict[str, Any] | None:
    return _read_json(scheduler_state_path(root))


def _load_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None
    return value if value > 0 else None


def _pid_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _lock_stale(path: Path, *, tick_interval_minutes: int) -> bool:
    try:
        age_seconds = time.time() - path.stat().st_mtime
    except FileNotFoundError:
        return False
    return age_seconds > max(tick_interval_minutes * 120, 300)


def _acquire_lock(root: Path, *, tick_interval_minutes: int) -> bool:
    path = scheduler_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and _lock_stale(path, tick_interval_minutes=tick_interval_minutes):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_iso_utc(_now_utc()))
    return True


def _release_lock(root: Path) -> None:
    try:
        scheduler_lock_path(root).unlink()
    except FileNotFoundError:
        pass


def scheduler_status(root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    cfg = load_workflow_config(root)
    settings = scheduler_settings_cfg(cfg)
    state = load_scheduler_state(root) or {}
    now_dt = now or _now_utc()
    last_run = parse_iso_timestamp(state.get("lastRunAt"))
    next_run = None
    if settings["enabled"]:
        next_run = now_dt if last_run is None else last_run + timedelta(minutes=settings["tickIntervalMinutes"])
    pid = _load_pid(scheduler_pid_path(root))
    supervisor_active = _pid_alive(pid)
    due = bool(settings["enabled"] and next_run is not None and now_dt >= next_run)
    reason = "Scheduler is disabled in WORKFLOW.json."
    if settings["enabled"]:
        if supervisor_active:
            reason = "Scheduler supervisor is active."
        elif last_run is None:
            reason = "No scheduler tick has been recorded yet."
        elif due:
            reason = "Scheduler tick interval has elapsed."
        else:
            reason = "Scheduler is not due yet."
    return {
        "enabled": settings["enabled"],
        "mode": settings["mode"],
        "tickIntervalMinutes": settings["tickIntervalMinutes"],
        "opportunisticCommands": list(settings["opportunisticCommands"]),
        "due": due,
        "reason": reason,
        "supervisorActive": supervisor_active,
        "workerPid": pid or 0,
        "lastRunAt": str(state.get("lastRunAt", "")),
        "nextRunAt": _iso_utc(next_run) if next_run is not None else "",
        "lastResult": str(state.get("lastResult", "")),
        "lastJobs": list(state.get("lastJobs", [])) if isinstance(state.get("lastJobs"), list) else [],
        "lastEvent": dict(state.get("lastEvent", {})) if isinstance(state.get("lastEvent"), dict) else {},
        "statePath": str(scheduler_state_path(root)),
        "pidPath": str(scheduler_pid_path(root)),
        "lockPath": str(scheduler_lock_path(root)),
        "eventsPath": str(scheduler_events_path(root)),
    }


def _record_state(
    root: Path,
    *,
    settings: dict[str, Any],
    jobs: list[str],
    result: str,
    last_event: dict[str, Any],
    ran_at: datetime,
) -> dict[str, Any]:
    next_run = ran_at + timedelta(minutes=settings["tickIntervalMinutes"]) if settings["enabled"] else None
    state = {
        "schemaVersion": SCHEDULER_STATE_SCHEMA_VERSION,
        "enabled": settings["enabled"],
        "mode": settings["mode"],
        "tickIntervalMinutes": settings["tickIntervalMinutes"],
        "opportunisticCommands": list(settings["opportunisticCommands"]),
        "lastRunAt": _iso_utc(ran_at),
        "nextRunAt": _iso_utc(next_run) if next_run is not None else "",
        "lastResult": result,
        "lastJobs": list(jobs),
        "lastEvent": last_event,
    }
    _write_json(scheduler_state_path(root), state)
    return state


def run_scheduler_once(
    root: Path,
    *,
    jobs: list[str] | None = None,
    force: bool = False,
    triggered_by: str = "manual",
    allow_when_supervisor: bool = False,
) -> dict[str, Any]:
    cfg = load_workflow_config(root)
    settings = scheduler_settings_cfg(cfg)
    status = scheduler_status(root)
    if not force and not settings["enabled"]:
        return {"executed": False, "reason": "Scheduler disabled.", "status": status, "jobs": []}
    if status["supervisorActive"] and not allow_when_supervisor and triggered_by != "supervisor":
        return {
            "executed": False,
            "reason": "Supervisor is active; opportunistic tick suppressed.",
            "status": status,
            "jobs": [],
        }
    if not force and not status["due"]:
        return {"executed": False, "reason": status["reason"], "status": status, "jobs": []}
    if not _acquire_lock(root, tick_interval_minutes=settings["tickIntervalMinutes"]):
        return {"executed": False, "reason": "Scheduler lock is already held.", "status": status, "jobs": []}

    selected_jobs = [job for job in (jobs or list(SCHEDULER_JOB_NAMES)) if job in SCHEDULER_JOB_NAMES]
    ran_at = _now_utc()
    job_results: dict[str, Any] = {}
    try:
        for job in selected_jobs:
            if job == "watch_patrol":
                job_results[job] = run_watch_tick(root, force=True)
            elif job == "work_order_sync":
                synced = sync_all_work_orders(root)
                job_results[job] = {"workOrders": [order.to_dict() for order in synced], "count": len(synced)}
            elif job == "dispatch_ready":
                job_results[job] = dispatch_ready_work(root)
            elif job == "feedback_sync":
                job_results[job] = sync_shape_feedback(root)
        event = {
            "timestamp": _iso_utc(ran_at),
            "triggeredBy": triggered_by,
            "jobs": selected_jobs,
            "result": "ok",
        }
        _append_event(root, event)
        state = _record_state(root, settings=settings, jobs=selected_jobs, result="ok", last_event=event, ran_at=ran_at)
        return {"executed": True, "reason": "Scheduler jobs executed.", "status": state, "jobs": job_results}
    finally:
        _release_lock(root)


def start_scheduler_supervisor(root: Path) -> dict[str, Any]:
    status = scheduler_status(root)
    if status["supervisorActive"]:
        return status
    pid_path = scheduler_pid_path(root)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    script = root / ".cnogo" / "scripts" / "workflow_memory.py"
    process = subprocess.Popen(
        [sys.executable, str(script), "_scheduler-worker"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    event = {
        "timestamp": _iso_utc(_now_utc()),
        "triggeredBy": "scheduler-start",
        "jobs": [],
        "result": "started",
        "pid": process.pid,
    }
    _append_event(root, event)
    state = load_scheduler_state(root) or {}
    state["lastEvent"] = event
    _write_json(scheduler_state_path(root), state)
    return scheduler_status(root)


def stop_scheduler_supervisor(root: Path) -> dict[str, Any]:
    pid_path = scheduler_pid_path(root)
    pid = _load_pid(pid_path)
    if _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    try:
        pid_path.unlink()
    except FileNotFoundError:
        pass
    event = {
        "timestamp": _iso_utc(_now_utc()),
        "triggeredBy": "scheduler-stop",
        "jobs": [],
        "result": "stopped",
        "pid": pid or 0,
    }
    _append_event(root, event)
    state = load_scheduler_state(root) or {}
    state["lastEvent"] = event
    _write_json(scheduler_state_path(root), state)
    return scheduler_status(root)


def scheduler_worker_loop(root: Path) -> int:
    pid_path = scheduler_pid_path(root)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        while True:
            run_scheduler_once(
                root,
                force=False,
                triggered_by="supervisor",
                allow_when_supervisor=True,
            )
            settings = scheduler_settings_cfg(load_workflow_config(root))
            time.sleep(max(settings["tickIntervalMinutes"] * 60, 5))
    finally:
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass
