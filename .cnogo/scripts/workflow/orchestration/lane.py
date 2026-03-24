"""Feature-lane runtime state for multi-feature execution.

Single-writer assumption: only the dispatcher (or CLI via lane commands)
writes to lane files. Concurrent writes from parallel dispatchers are not
guarded with file locks and may cause state corruption.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import dispatcher_settings_cfg, load_workflow_config
from scripts.workflow.shared.runtime_root import runtime_path, runtime_root, write_runtime_root_marker
from scripts.workflow.shared.timestamps import parse_iso_timestamp


FEATURE_LANE_SCHEMA_VERSION = 2
FEATURE_LANE_STATUSES = frozenset(
    {
        "leased",
        "planning",
        "implementing",
        "reviewing",
        "shipping",
        "blocked",
        "completed",
        "released",
    }
)
_TERMINAL_FEATURE_LANE_STATUSES = frozenset({"completed", "released"})
_RECLAIMABLE_FEATURE_LANE_STATUSES = frozenset({"leased", "planning", "blocked"})
_LANES_DIR = Path(".cnogo") / "lanes"
_DEFAULT_LEASE_TIMEOUT_MINUTES = 45


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_lease_token() -> str:
    return uuid.uuid4().hex


def _lease_timeout_minutes(root: Path) -> int:
    cfg = load_workflow_config(root)
    settings = dispatcher_settings_cfg(cfg)
    value = settings.get("leaseTimeoutMinutes", _DEFAULT_LEASE_TIMEOUT_MINUTES)
    return value if isinstance(value, int) and value > 0 else _DEFAULT_LEASE_TIMEOUT_MINUTES


def _expires_at(heartbeat_at: str, root: Path) -> str:
    base = parse_iso_timestamp(heartbeat_at)
    if base is None:
        base = datetime.now(timezone.utc)
    expiry = base + timedelta(minutes=_lease_timeout_minutes(root))
    return expiry.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lane_anchor_timestamp(lane: "FeatureLane") -> str:
    for value in (lane.heartbeat_at, lane.updated_at, lane.leased_at, lane.created_at):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


@dataclass
class FeatureLane:
    lane_id: str = ""
    feature: str = ""
    work_order_id: str = ""
    branch: str = ""
    worktree_path: str = ""
    lease_owner: str = ""
    status: str = "leased"
    current_plan_number: str = ""
    current_run_id: str = ""
    session_path: str = ""
    lease_token: str = ""
    leased_at: str = ""
    heartbeat_at: str = ""
    lease_expires_at: str = ""
    released_at: str = ""
    release_reason: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": FEATURE_LANE_SCHEMA_VERSION,
            "laneId": self.lane_id,
            "feature": self.feature,
            "workOrderId": self.work_order_id,
            "branch": self.branch,
            "worktreePath": self.worktree_path,
            "leaseOwner": self.lease_owner,
            "status": self.status,
            "currentPlanNumber": self.current_plan_number,
            "currentRunId": self.current_run_id,
            "sessionPath": self.session_path,
            "leaseToken": self.lease_token,
            "leasedAt": self.leased_at,
            "heartbeatAt": self.heartbeat_at,
            "leaseExpiresAt": self.lease_expires_at,
            "releasedAt": self.released_at,
            "releaseReason": self.release_reason,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeatureLane":
        return cls(
            lane_id=str(data.get("laneId", "")),
            feature=str(data.get("feature", "")),
            work_order_id=str(data.get("workOrderId", "")),
            branch=str(data.get("branch", "")),
            worktree_path=str(data.get("worktreePath", "")),
            lease_owner=str(data.get("leaseOwner", "")),
            status=str(data.get("status", "leased")),
            current_plan_number=str(data.get("currentPlanNumber", "")),
            current_run_id=str(data.get("currentRunId", "")),
            session_path=str(data.get("sessionPath", "")),
            lease_token=str(data.get("leaseToken", "")),
            leased_at=str(data.get("leasedAt", "")),
            heartbeat_at=str(data.get("heartbeatAt", "")),
            lease_expires_at=str(data.get("leaseExpiresAt", "")),
            released_at=str(data.get("releasedAt", "")),
            release_reason=str(data.get("releaseReason", "")),
            created_at=str(data.get("createdAt", "")),
            updated_at=str(data.get("updatedAt", "")),
        )


def lanes_dir(root: Path) -> Path:
    return runtime_path(root, "lanes")


def lane_path(root: Path, feature: str) -> Path:
    return lanes_dir(root) / f"{feature}.json"


def load_feature_lane(root: Path, feature: str) -> FeatureLane | None:
    path = lane_path(root, feature)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return FeatureLane.from_dict(payload)


def save_feature_lane(lane: FeatureLane, root: Path) -> Path:
    if lane.status not in FEATURE_LANE_STATUSES:
        raise ValueError(f"Unsupported feature lane status: {lane.status!r}")
    now = _now_iso()
    lane.updated_at = now
    if not lane.created_at:
        lane.created_at = now
    if lane.status not in _TERMINAL_FEATURE_LANE_STATUSES:
        if not lane.lease_token:
            lane.lease_token = _new_lease_token()
        if not lane.leased_at:
            lane.leased_at = now
        if not lane.heartbeat_at:
            lane.heartbeat_at = now
        lane.lease_expires_at = _expires_at(lane.heartbeat_at, root)
    path = lane_path(root, lane.feature)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lane.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def list_feature_lanes(
    root: Path,
    *,
    include_terminal: bool = False,
    feature_filter: str | None = None,
) -> list[FeatureLane]:
    results: list[FeatureLane] = []
    lane_root = lanes_dir(root)
    if not lane_root.is_dir():
        return results
    for path in sorted(lane_root.glob("*.json")):
        if feature_filter and path.stem != feature_filter:
            continue
        lane = load_feature_lane(root, path.stem)
        if lane is None:
            continue
        if not include_terminal and lane.status in _TERMINAL_FEATURE_LANE_STATUSES:
            continue
        results.append(lane)
    results.sort(key=lambda lane: lane.updated_at, reverse=True)
    return results


def feature_lane_health(
    root: Path,
    lane: FeatureLane,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_dt = now or datetime.now(timezone.utc)
    timeout_minutes = _lease_timeout_minutes(root)
    active = lane.status not in _TERMINAL_FEATURE_LANE_STATUSES
    anchor_value = _lane_anchor_timestamp(lane)
    anchor = parse_iso_timestamp(anchor_value)
    expiry = parse_iso_timestamp(lane.lease_expires_at)
    minutes_since_heartbeat: float | None = None
    if anchor is not None:
        minutes_since_heartbeat = max((now_dt - anchor).total_seconds() / 60.0, 0.0)
    worktree_missing = bool(lane.worktree_path and not Path(lane.worktree_path).exists())
    expired = bool(active and expiry is not None and now_dt >= expiry)
    stale = bool(active and (worktree_missing or expired))
    reclaimable = bool(
        stale
        and not lane.current_run_id
        and lane.status in _RECLAIMABLE_FEATURE_LANE_STATUSES
    )
    reason = ""
    if worktree_missing:
        reason = "worktree_missing"
    elif expired:
        reason = "lease_expired"
    elif not active:
        reason = "terminal"
    return {
        "active": active,
        "stale": stale,
        "reclaimable": reclaimable,
        "reason": reason,
        "timeoutMinutes": timeout_minutes,
        "minutesSinceHeartbeat": round(minutes_since_heartbeat, 1)
        if minutes_since_heartbeat is not None
        else None,
        "heartbeatAt": lane.heartbeat_at,
        "leaseExpiresAt": lane.lease_expires_at,
        "worktreeMissing": worktree_missing,
        "hasCurrentRun": bool(lane.current_run_id),
    }


def feature_lane_payload(root: Path, lane: FeatureLane, *, now: datetime | None = None) -> dict[str, Any]:
    payload = lane.to_dict()
    payload["health"] = feature_lane_health(root, lane, now=now)
    return payload


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )


def _git_available(root: Path) -> bool:
    return (root / ".git").exists()


def _branch_exists(root: Path, branch: str) -> bool:
    try:
        _run_git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
        return True
    except subprocess.CalledProcessError:
        return False


def _resolve_base_branch(root: Path) -> str:
    for branch in ("main", "master"):
        if _branch_exists(root, branch):
            return branch
    try:
        result = _run_git(root, "branch", "--show-current")
    except subprocess.CalledProcessError:
        return "main"
    current = result.stdout.strip()
    return current or "main"


def _feature_worktree_path(root: Path, feature: str) -> Path:
    # Place worktrees INSIDE the main checkout (at a gitignored path) so they
    # stay within Claude Code's file sandbox boundary. Agents can access them
    # directly without isolation:"worktree" or additionalDirectories.
    return (root / ".cnogo" / "feature-worktrees" / feature).resolve()


def _ensure_feature_worktree(root: Path, feature: str) -> tuple[str, str]:
    branch = f"feature/{feature}"
    worktree_path = _feature_worktree_path(root, feature)
    if not _git_available(root):
        worktree_path.mkdir(parents=True, exist_ok=True)
        write_runtime_root_marker(worktree_path, runtime_root(root))
        return "", str(worktree_path)
    if not _branch_exists(root, branch):
        _run_git(root, "branch", branch, _resolve_base_branch(root))
    if not worktree_path.exists():
        _run_git(root, "worktree", "add", str(worktree_path), branch)
    else:
        # Verify existing worktree is on the expected branch.
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=str(worktree_path),
                capture_output=True, text=True, check=False,
            )
            actual_branch = result.stdout.strip() if result.returncode == 0 else ""
            if actual_branch and actual_branch != branch:
                subprocess.run(
                    ["git", "checkout", branch],
                    cwd=str(worktree_path),
                    capture_output=True, text=True, check=False,
                )
        except Exception:
            pass  # Best-effort verification
    write_runtime_root_marker(worktree_path, runtime_root(root))
    return branch, str(worktree_path)


def ensure_feature_lane(
    root: Path,
    *,
    feature: str,
    work_order_id: str = "",
    lease_owner: str = "dispatcher",
    status: str = "planning",
) -> FeatureLane:
    existing = load_feature_lane(root, feature)
    if existing is not None and existing.status not in _TERMINAL_FEATURE_LANE_STATUSES:
        return existing
    branch, worktree_path = _ensure_feature_worktree(root, feature)
    now = _now_iso()
    lane = FeatureLane(
        lane_id=f"{feature}-{int(time.time())}",
        feature=feature,
        work_order_id=work_order_id or feature,
        branch=branch,
        worktree_path=worktree_path,
        lease_owner=lease_owner,
        status=status,
        lease_token=_new_lease_token(),
        leased_at=now,
        heartbeat_at=now,
        lease_expires_at=_expires_at(now, root),
        created_at=now,
        updated_at=now,
    )
    save_feature_lane(lane, root)
    return lane


def heartbeat_feature_lane(
    root: Path,
    feature: str,
    *,
    status: str | None = None,
    current_plan_number: str | None = None,
    current_run_id: str | None = None,
    session_path: str | None = None,
    lease_owner: str | None = None,
) -> FeatureLane:
    lane = load_feature_lane(root, feature)
    if lane is None:
        raise ValueError(f"No feature lane found for {feature!r}")
    now = _now_iso()
    lane.heartbeat_at = now
    lane.lease_expires_at = _expires_at(now, root)
    lane.released_at = ""
    lane.release_reason = ""
    if status is not None:
        lane.status = status
    if current_plan_number is not None:
        lane.current_plan_number = current_plan_number
    if current_run_id is not None:
        lane.current_run_id = current_run_id
    if session_path is not None:
        lane.session_path = session_path
    if lease_owner is not None:
        lane.lease_owner = lease_owner
    save_feature_lane(lane, root)
    return lane


def release_feature_lane(
    root: Path,
    feature: str,
    *,
    reason: str = "released",
    lease_owner: str | None = None,
) -> FeatureLane:
    lane = load_feature_lane(root, feature)
    if lane is None:
        raise ValueError(f"No feature lane found for {feature!r}")
    lane.status = "released"
    lane.released_at = _now_iso()
    lane.release_reason = reason.strip() or "released"
    lane.lease_expires_at = ""
    lane.lease_owner = lease_owner if lease_owner is not None else lane.lease_owner
    save_feature_lane(lane, root)
    return lane


def reclaim_stale_feature_lanes(
    root: Path,
    *,
    feature_filter: str | None = None,
    lease_owner: str = "patrol",
) -> list[dict[str, Any]]:
    reclaimed: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for lane in list_feature_lanes(root, include_terminal=False):
        if feature_filter and lane.feature != feature_filter:
            continue
        health = feature_lane_health(root, lane, now=now)
        if not health.get("reclaimable"):
            continue
        released = release_feature_lane(
            root,
            lane.feature,
            reason=str(health.get("reason", "lease_expired")).strip() or "lease_expired",
            lease_owner=lease_owner,
        )
        payload = feature_lane_payload(root, released, now=now)
        payload["reclaimed"] = True
        reclaimed.append(payload)
    return reclaimed


def update_feature_lane(
    root: Path,
    feature: str,
    *,
    status: str | None = None,
    current_plan_number: str | None = None,
    current_run_id: str | None = None,
    session_path: str | None = None,
    lease_owner: str | None = None,
) -> FeatureLane:
    return heartbeat_feature_lane(
        root,
        feature,
        status=status,
        current_plan_number=current_plan_number,
        current_run_id=current_run_id,
        session_path=session_path,
        lease_owner=lease_owner,
    )
