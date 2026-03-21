"""Durable execution state for feature-plan delivery runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .integration import ensure_run_coordination_state, sync_integration_state
from .review import ensure_run_review_state, sync_review_state

DELIVERY_RUN_SCHEMA_VERSION = 1

DELIVERY_RUN_STATUSES = frozenset(
    {
        "created",
        "active",
        "blocked",
        "ready_for_review",
        "completed",
        "failed",
        "cancelled",
    }
)
TERMINAL_DELIVERY_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})

DELIVERY_TASK_STATUSES = frozenset(
    {
        "pending",
        "ready",
        "in_progress",
        "done",
        "verified",
        "merged",
        "failed",
        "skipped",
        "cancelled",
    }
)

_RUNS_DIR = Path(".cnogo") / "runs"
_TASK_READY_PREDECESSORS = frozenset({"done", "verified", "merged", "skipped", "cancelled"})
_RUN_READY_FOR_REVIEW_TASKS = frozenset({"done", "verified", "merged", "skipped", "cancelled"})
_RUN_COMPLETED_TASKS = frozenset({"merged", "skipped", "cancelled"})
_WORKTREE_TO_TASK_STATUS = {
    "created": "ready",
    "executing": "in_progress",
    "completed": "done",
    "merged": "merged",
    "conflict": "failed",
    "cleaned": "merged",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class DeliveryTask:
    task_index: int
    title: str
    status: str = "pending"
    memory_id: str = ""
    blocked_by: list[int] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    verify_commands: list[str] = field(default_factory=list)
    package_verify_commands: list[str] = field(default_factory=list)
    cwd: str = ""
    assignee: str = ""
    branch: str = ""
    worktree_path: str = ""
    notes: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskIndex": self.task_index,
            "title": self.title,
            "status": self.status,
            "memoryId": self.memory_id,
            "blockedBy": self.blocked_by,
            "filePaths": self.file_paths,
            "forbiddenPaths": self.forbidden_paths,
            "verifyCommands": self.verify_commands,
            "packageVerifyCommands": self.package_verify_commands,
            "cwd": self.cwd,
            "assignee": self.assignee,
            "branch": self.branch,
            "worktreePath": self.worktree_path,
            "notes": self.notes,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryTask":
        return cls(
            task_index=int(data.get("taskIndex", 0)),
            title=str(data.get("title", "")),
            status=str(data.get("status", "pending")),
            memory_id=str(data.get("memoryId", "")),
            blocked_by=[int(v) for v in data.get("blockedBy", []) if isinstance(v, int)],
            file_paths=[str(v) for v in data.get("filePaths", []) if isinstance(v, str)],
            forbidden_paths=[str(v) for v in data.get("forbiddenPaths", []) if isinstance(v, str)],
            verify_commands=[str(v) for v in data.get("verifyCommands", []) if isinstance(v, str)],
            package_verify_commands=[
                str(v) for v in data.get("packageVerifyCommands", []) if isinstance(v, str)
            ],
            cwd=str(data.get("cwd", "")),
            assignee=str(data.get("assignee", "")),
            branch=str(data.get("branch", "")),
            worktree_path=str(data.get("worktreePath", "")),
            notes=[str(v) for v in data.get("notes", []) if isinstance(v, str)],
            updated_at=str(data.get("updatedAt", _now_iso())),
        )

    @classmethod
    def from_task_desc(cls, task_desc: dict[str, Any], *, fallback_index: int) -> "DeliveryTask":
        file_scope = task_desc.get("file_scope", {})
        commands = task_desc.get("commands", {})
        blocked_by = task_desc.get("blockedBy", [])
        status = "skipped" if task_desc.get("skipped", False) else ("ready" if not blocked_by else "pending")
        return cls(
            task_index=int(task_desc.get("plan_task_index", fallback_index)),
            title=str(task_desc.get("title", f"Task {fallback_index + 1}")),
            status=status,
            memory_id=str(task_desc.get("task_id", "")),
            blocked_by=[int(v) for v in blocked_by if isinstance(v, int)],
            file_paths=[str(v) for v in file_scope.get("paths", []) if isinstance(v, str)],
            forbidden_paths=[str(v) for v in file_scope.get("forbidden", []) if isinstance(v, str)],
            verify_commands=[str(v) for v in commands.get("verify", []) if isinstance(v, str)],
            package_verify_commands=[
                str(v) for v in commands.get("package_verify", []) if isinstance(v, str)
            ],
            cwd=str(task_desc.get("cwd", "")) if task_desc.get("cwd") else "",
        )


@dataclass
class DeliveryRun:
    schema_version: int = DELIVERY_RUN_SCHEMA_VERSION
    run_id: str = ""
    feature: str = ""
    plan_number: str = ""
    mode: str = "serial"
    status: str = "created"
    started_by: str = "claude"
    branch: str = ""
    plan_path: str = ""
    summary_path: str = ""
    review_path: str = ""
    recommendation: dict[str, Any] = field(default_factory=dict)
    integration: dict[str, Any] = field(default_factory=dict)
    review_readiness: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)
    tasks: list[DeliveryTask] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "runId": self.run_id,
            "feature": self.feature,
            "planNumber": self.plan_number,
            "mode": self.mode,
            "status": self.status,
            "startedBy": self.started_by,
            "branch": self.branch,
            "planPath": self.plan_path,
            "summaryPath": self.summary_path,
            "reviewPath": self.review_path,
            "recommendation": self.recommendation,
            "integration": self.integration,
            "reviewReadiness": self.review_readiness,
            "review": self.review,
            "tasks": [task.to_dict() for task in self.tasks],
            "notes": self.notes,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryRun":
        return cls(
            schema_version=int(data.get("schemaVersion", DELIVERY_RUN_SCHEMA_VERSION)),
            run_id=str(data.get("runId", "")),
            feature=str(data.get("feature", "")),
            plan_number=str(data.get("planNumber", "")),
            mode=str(data.get("mode", "serial")),
            status=str(data.get("status", "created")),
            started_by=str(data.get("startedBy", "claude")),
            branch=str(data.get("branch", "")),
            plan_path=str(data.get("planPath", "")),
            summary_path=str(data.get("summaryPath", "")),
            review_path=str(data.get("reviewPath", "")),
            recommendation=dict(data.get("recommendation", {}))
            if isinstance(data.get("recommendation"), dict)
            else {},
            integration=dict(data.get("integration", {}))
            if isinstance(data.get("integration"), dict)
            else {},
            review_readiness=dict(data.get("reviewReadiness", {}))
            if isinstance(data.get("reviewReadiness"), dict)
            else {},
            review=dict(data.get("review", {}))
            if isinstance(data.get("review"), dict)
            else {},
            tasks=[
                DeliveryTask.from_dict(task)
                for task in data.get("tasks", [])
                if isinstance(task, dict)
            ],
            notes=[str(v) for v in data.get("notes", []) if isinstance(v, str)],
            created_at=str(data.get("createdAt", _now_iso())),
            updated_at=str(data.get("updatedAt", _now_iso())),
        )


def delivery_run_dir(root: Path, feature: str) -> Path:
    return root / _RUNS_DIR / feature


def delivery_run_path(root: Path, feature: str, run_id: str) -> Path:
    return delivery_run_dir(root, feature) / f"{run_id}.json"


def save_delivery_run(run: DeliveryRun, root: Path) -> Path:
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    sync_review_state(run)
    run.updated_at = _now_iso()
    if not run.created_at:
        run.created_at = run.updated_at
    path = delivery_run_path(root, run.feature, run.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(run.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_delivery_run(root: Path, feature: str, run_id: str) -> DeliveryRun | None:
    path = delivery_run_path(root, feature, run_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Delivery run at {path} must be a JSON object")
    run = DeliveryRun.from_dict(data)
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    sync_review_state(run)
    return run


def latest_delivery_run(root: Path, feature: str) -> DeliveryRun | None:
    run_dir = delivery_run_dir(root, feature)
    if not run_dir.exists():
        return None
    candidates = sorted(
        (path for path in run_dir.glob("*.json") if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            run = DeliveryRun.from_dict(data)
            ensure_run_coordination_state(run)
            ensure_run_review_state(run)
            sync_review_state(run)
            return run
    return None


def _derive_run_status(tasks: list[DeliveryTask]) -> str:
    if not tasks:
        return "created"
    states = {task.status for task in tasks}
    if "failed" in states:
        return "failed"
    if states.issubset(_RUN_COMPLETED_TASKS):
        return "completed"
    if states.issubset(_RUN_READY_FOR_REVIEW_TASKS):
        return "ready_for_review"
    if "ready" in states or "in_progress" in states:
        return "active"
    if states == {"pending"}:
        return "blocked"
    return "active"


def refresh_task_frontier(run: DeliveryRun) -> DeliveryRun:
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    by_index = {task.task_index: task for task in run.tasks}
    for task in run.tasks:
        if task.status in {"pending", "blocked"}:
            if all(
                by_index.get(dep) is not None and by_index[dep].status in _TASK_READY_PREDECESSORS
                for dep in task.blocked_by
            ):
                task.status = "ready"
                task.updated_at = _now_iso()
    run.status = _derive_run_status(run.tasks)
    run.updated_at = _now_iso()
    sync_integration_state(run)
    return sync_review_state(run)


def create_delivery_run(
    root: Path,
    *,
    feature: str,
    plan_number: str,
    plan_path: Path,
    task_descriptions: list[dict[str, Any]],
    mode: str,
    run_id: str | None = None,
    started_by: str = "claude",
    branch: str = "",
    recommendation: dict[str, Any] | None = None,
) -> DeliveryRun:
    if mode not in {"serial", "team"}:
        raise ValueError(f"Unsupported delivery run mode: {mode!r}")
    if not run_id:
        run_id = f"{feature}-{int(time.time())}"
    tasks = [
        DeliveryTask.from_task_desc(task_desc, fallback_index=index)
        for index, task_desc in enumerate(task_descriptions)
    ]
    run = DeliveryRun(
        run_id=run_id,
        feature=feature,
        plan_number=plan_number,
        mode=mode,
        status="created",
        started_by=started_by,
        branch=branch,
        plan_path=str(plan_path),
        summary_path=str(plan_path.with_name(f"{plan_path.stem.replace('-PLAN', '')}-SUMMARY.json")),
        review_path=str(plan_path.with_name("REVIEW.json")),
        recommendation=recommendation or {},
        integration={},
        review_readiness={},
        review={},
        tasks=tasks,
    )
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    refresh_task_frontier(run)
    save_delivery_run(run, root)
    return run


def ensure_delivery_run(
    root: Path,
    *,
    feature: str,
    plan_number: str,
    plan_path: Path,
    task_descriptions: list[dict[str, Any]],
    mode: str,
    run_id: str | None = None,
    started_by: str = "claude",
    branch: str = "",
    recommendation: dict[str, Any] | None = None,
    resume_latest: bool = True,
) -> DeliveryRun:
    if run_id:
        existing = load_delivery_run(root, feature, run_id)
        if existing is not None:
            return existing
    if resume_latest:
        latest = latest_delivery_run(root, feature)
        if latest is not None and latest.plan_number == plan_number and latest.status not in TERMINAL_DELIVERY_RUN_STATUSES:
            return latest
    return create_delivery_run(
        root,
        feature=feature,
        plan_number=plan_number,
        plan_path=plan_path,
        task_descriptions=task_descriptions,
        mode=mode,
        run_id=run_id,
        started_by=started_by,
        branch=branch,
        recommendation=recommendation,
    )


def update_delivery_task_status(
    run: DeliveryRun,
    *,
    task_index: int,
    status: str,
    assignee: str | None = None,
    branch: str | None = None,
    worktree_path: str | None = None,
    note: str | None = None,
) -> DeliveryRun:
    if status not in DELIVERY_TASK_STATUSES:
        raise ValueError(f"Unsupported delivery task status: {status!r}")
    task = next((task for task in run.tasks if task.task_index == task_index), None)
    if task is None:
        raise ValueError(f"Unknown task index {task_index} for run {run.run_id}")
    task.status = status
    if assignee is not None:
        task.assignee = assignee
    if branch is not None:
        task.branch = branch
    if worktree_path is not None:
        task.worktree_path = worktree_path
    if note:
        task.notes.append(note)
    task.updated_at = _now_iso()
    return refresh_task_frontier(run)


def sync_run_with_worktree_session(run: DeliveryRun, session: Any) -> DeliveryRun:
    ensure_run_coordination_state(run)
    ensure_run_review_state(run)
    worktrees = getattr(session, "worktrees", None)
    if worktrees is None and isinstance(session, dict):
        worktrees = session.get("worktrees")
    if not isinstance(worktrees, list):
        sync_integration_state(run, session=session)
        return sync_review_state(run)

    by_index = {task.task_index: task for task in run.tasks}
    for worktree in worktrees:
        task_index = getattr(worktree, "task_index", None)
        status = getattr(worktree, "status", None)
        branch = getattr(worktree, "branch", "")
        path = getattr(worktree, "path", "")
        memory_id = getattr(worktree, "memory_id", "")
        if isinstance(worktree, dict):
            task_index = worktree.get("taskIndex", task_index)
            status = worktree.get("status", status)
            branch = worktree.get("branch", branch)
            path = worktree.get("path", path)
            memory_id = worktree.get("memoryId", memory_id)
        if not isinstance(task_index, int) or task_index not in by_index:
            continue
        task = by_index[task_index]
        task.branch = str(branch or task.branch)
        task.worktree_path = str(path or task.worktree_path)
        if memory_id:
            task.memory_id = str(memory_id)
        mapped_status = _WORKTREE_TO_TASK_STATUS.get(str(status))
        if mapped_status:
            task.status = mapped_status
        task.updated_at = _now_iso()

    run.updated_at = _now_iso()
    run.status = _derive_run_status(run.tasks)
    sync_integration_state(run, session=session)
    return sync_review_state(run)
