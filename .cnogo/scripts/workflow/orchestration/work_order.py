"""Feature-level Work Order rollups built on top of delivery runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import dispatcher_settings_cfg, load_workflow_config
from scripts.workflow.shared.profiles import (
    profile_auto_advance,
    profile_auto_plan,
    profile_auto_review,
    profile_auto_ship,
    profile_ship_require_pull_request,
    profile_ship_require_tracking,
)
from scripts.workflow.shared.runtime_root import runtime_path
from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .delivery_run import DeliveryRun, delivery_run_dir, latest_delivery_run, load_delivery_run
from .implement import next_delivery_run_action
from .lane import feature_lane_payload, load_feature_lane, reclaim_stale_feature_lanes
from .watch_artifacts import load_attention_queue

WORK_ORDER_SCHEMA_VERSION = 1
WORK_ORDER_STATUSES = frozenset(
    {
        "queued",
        "leased",
        "planning",
        "planned",
        "implementing",
        "reviewing",
        "shipping",
        "blocked",
        "completed",
        "cancelled",
    }
)

_WORK_ORDERS_DIR = Path(".cnogo") / "work-orders"
_PHASE_STATE_PATH = Path(".cnogo") / "feature-phases.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _feature_phase(root: Path, feature: str) -> str:
    payload = _read_json(runtime_path(root, "feature-phases.json")) or {}
    features = payload.get("features")
    if isinstance(features, dict):
        entry = features.get(feature)
        if isinstance(entry, dict):
            phase = entry.get("phase")
            if isinstance(phase, str) and phase.strip():
                return phase.strip()
    return "unknown"


def work_orders_dir(root: Path) -> Path:
    return runtime_path(root, "work-orders")


def work_order_path(root: Path, feature: str) -> Path:
    return work_orders_dir(root) / f"{feature}.json"


@dataclass
class WorkOrder:
    schema_version: int = WORK_ORDER_SCHEMA_VERSION
    work_order_id: str = ""
    feature: str = ""
    status: str = "queued"
    current_phase: str = "unknown"
    profile: dict[str, Any] = field(default_factory=dict)
    current_run_id: str = ""
    run_history: list[dict[str, Any]] = field(default_factory=list)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    queue_position: int = 0
    lane: dict[str, Any] = field(default_factory=dict)
    attention_summary: dict[str, Any] = field(default_factory=dict)
    review_summary: dict[str, Any] = field(default_factory=dict)
    ship_summary: dict[str, Any] = field(default_factory=dict)
    memory_sync: dict[str, Any] = field(default_factory=dict)
    automation_state: dict[str, Any] = field(default_factory=dict)
    next_action: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "workOrderId": self.work_order_id,
            "feature": self.feature,
            "status": self.status,
            "currentPhase": self.current_phase,
            "profile": self.profile,
            "currentRunId": self.current_run_id,
            "runHistory": self.run_history,
            "artifactPaths": self.artifact_paths,
            "queuePosition": self.queue_position,
            "lane": self.lane,
            "attentionSummary": self.attention_summary,
            "reviewSummary": self.review_summary,
            "shipSummary": self.ship_summary,
            "memorySync": self.memory_sync,
            "automationState": self.automation_state,
            "nextAction": self.next_action,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkOrder":
        return cls(
            schema_version=int(data.get("schemaVersion", WORK_ORDER_SCHEMA_VERSION)),
            work_order_id=str(data.get("workOrderId", "")),
            feature=str(data.get("feature", "")),
            status=str(data.get("status", "queued")),
            current_phase=str(data.get("currentPhase", "unknown")),
            profile=dict(data.get("profile", {})) if isinstance(data.get("profile"), dict) else {},
            current_run_id=str(data.get("currentRunId", "")),
            run_history=[dict(item) for item in data.get("runHistory", []) if isinstance(item, dict)],
            artifact_paths=dict(data.get("artifactPaths", {}))
            if isinstance(data.get("artifactPaths"), dict)
            else {},
            queue_position=int(data.get("queuePosition", 0) or 0),
            lane=dict(data.get("lane", {})) if isinstance(data.get("lane"), dict) else {},
            attention_summary=dict(data.get("attentionSummary", {}))
            if isinstance(data.get("attentionSummary"), dict)
            else {},
            review_summary=dict(data.get("reviewSummary", {}))
            if isinstance(data.get("reviewSummary"), dict)
            else {},
            ship_summary=dict(data.get("shipSummary", {}))
            if isinstance(data.get("shipSummary"), dict)
            else {},
            memory_sync=dict(data.get("memorySync", {}))
            if isinstance(data.get("memorySync"), dict)
            else {},
            automation_state=dict(data.get("automationState", {}))
            if isinstance(data.get("automationState"), dict)
            else {},
            next_action=dict(data.get("nextAction", {}))
            if isinstance(data.get("nextAction"), dict)
            else {},
            created_at=str(data.get("createdAt", _now_iso())),
            updated_at=str(data.get("updatedAt", _now_iso())),
        )


def load_work_order(root: Path, feature: str) -> WorkOrder | None:
    payload = _read_json(work_order_path(root, feature))
    if payload is None:
        return None
    return WorkOrder.from_dict(payload)


def save_work_order(order: WorkOrder, root: Path) -> Path:
    order.updated_at = _now_iso()
    if not order.created_at:
        order.created_at = order.updated_at
    path = work_order_path(root, order.feature)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(order.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _iter_feature_run_paths(root: Path, feature: str) -> list[Path]:
    run_dir = delivery_run_dir(root, feature)
    if not run_dir.is_dir():
        return []
    return sorted(run_dir.glob("*.json"))


def _load_feature_runs(root: Path, feature: str) -> list[DeliveryRun]:
    runs: list[DeliveryRun] = []
    for path in _iter_feature_run_paths(root, feature):
        run = load_delivery_run(root, feature, path.stem)
        if run is not None:
            runs.append(run)
    runs.sort(
        key=lambda run: parse_iso_timestamp(getattr(run, "updated_at", "")) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return runs


def _feature_dir(root: Path, feature: str) -> Path:
    return root / "docs" / "planning" / "work" / "features" / feature


def _feature_stub(root: Path, feature: str) -> dict[str, Any]:
    payload = _read_json(_feature_dir(root, feature) / "FEATURE.json")
    return payload if isinstance(payload, dict) else {}


def _feature_context(root: Path, feature: str) -> dict[str, Any]:
    payload = _read_json(_feature_dir(root, feature) / "CONTEXT.json")
    return payload if isinstance(payload, dict) else {}


def _parent_shape_path(root: Path, feature: str) -> Path | None:
    for contract in (_feature_context(root, feature), _feature_stub(root, feature)):
        parent_shape = contract.get("parentShape")
        if not isinstance(parent_shape, dict):
            continue
        raw_path = parent_shape.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        shape_path = Path(raw_path.strip())
        return shape_path if shape_path.is_absolute() else root / shape_path
    return None


def _shape_candidate(root: Path, feature: str) -> dict[str, Any]:
    shape_path = _parent_shape_path(root, feature)
    if shape_path is None:
        return {}
    payload = _read_json(shape_path)
    if not isinstance(payload, dict):
        return {}
    candidates = payload.get("candidateFeatures")
    if not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("slug", "")).strip() == feature:
            return candidate
    return {}


def _feature_priority(root: Path, feature: str) -> int:
    for contract in (_feature_stub(root, feature), _feature_context(root, feature), _shape_candidate(root, feature)):
        value = contract.get("priority")
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 4:
            return value
    return 2


def _sequence_index(root: Path, feature: str) -> int:
    shape_path = _parent_shape_path(root, feature)
    if shape_path is None:
        return 10_000
    payload = _read_json(shape_path)
    if not isinstance(payload, dict):
        return 10_000
    sequence = payload.get("recommendedSequence")
    if not isinstance(sequence, list):
        return 10_000
    normalized = [str(value).strip() for value in sequence if isinstance(value, str) and value.strip()]
    try:
        return normalized.index(feature)
    except ValueError:
        return 10_000


def _has_plan(feature_dir: Path) -> bool:
    return feature_dir.is_dir() and any(feature_dir.glob("[0-9][0-9]-PLAN.json"))


def _latest_feature_artifacts(root: Path, feature: str, current_run: DeliveryRun | None) -> dict[str, str]:
    feature_dir = _feature_dir(root, feature)
    artifacts = {
        "feature": str(feature_dir / "FEATURE.json"),
        "context": str(feature_dir / "CONTEXT.json"),
        "summary": "",
        "review": str(feature_dir / "REVIEW.json"),
    }
    if current_run is not None:
        if getattr(current_run, "summary_path", ""):
            artifacts["summary"] = str(current_run.summary_path)
        if getattr(current_run, "review_path", ""):
            artifacts["review"] = str(current_run.review_path)
    shape_path = _parent_shape_path(root, feature)
    if shape_path is not None:
        artifacts["shape"] = str(shape_path)
    if not artifacts["summary"] and feature_dir.is_dir():
        summaries = sorted(feature_dir.glob("*-SUMMARY.json"))
        if summaries:
            artifacts["summary"] = str(summaries[-1].relative_to(root))
    for key, raw in list(artifacts.items()):
        path = Path(raw)
        if path.is_absolute():
            try:
                artifacts[key] = str(path.relative_to(root))
            except ValueError:
                artifacts[key] = str(path)
    return artifacts


def _run_history_entry(root: Path, run: DeliveryRun) -> dict[str, Any]:
    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    ship_state = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    profile = run.profile if isinstance(getattr(run, "profile", None), dict) else {}
    return {
        "runId": run.run_id,
        "planNumber": run.plan_number,
        "mode": run.mode,
        "status": run.status,
        "updatedAt": run.updated_at,
        "reviewStatus": str(review_state.get("status", "pending")),
        "reviewVerdict": str(review_state.get("finalVerdict", "pending")),
        "shipStatus": str(ship_state.get("status", "pending")),
        "profile": str(profile.get("name", "")),
        "path": str(runtime_path(root, "runs", run.feature, f"{run.run_id}.json")),
    }


def _feature_attention_summary(root: Path, feature: str, *, attention_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = attention_items
    if items is None:
        queue = load_attention_queue(root) or {}
        raw_items = queue.get("items", [])
        items = [dict(item) for item in raw_items if isinstance(item, dict)]
    scoped = [item for item in items if str(item.get("feature", "")).strip() == feature]
    severity_counts: dict[str, int] = {}
    highest = "ok"
    for item in scoped:
        severity = str(item.get("severity", "warn")).strip() or "warn"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if severity == "fail":
            highest = "fail"
        elif severity == "warn" and highest == "ok":
            highest = "warn"
    return {
        "itemCount": len(scoped),
        "highestSeverity": highest,
        "severityCounts": severity_counts,
    }


def _review_summary(run: DeliveryRun | None) -> dict[str, Any]:
    if run is None or not isinstance(getattr(run, "review", None), dict):
        return {"status": "pending", "finalVerdict": "pending"}
    review = run.review
    return {
        "status": str(review.get("status", "pending")),
        "automatedVerdict": str(review.get("automatedVerdict", "pending")),
        "finalVerdict": str(review.get("finalVerdict", "pending")),
        "reviewers": list(review.get("reviewers", [])) if isinstance(review.get("reviewers"), list) else [],
        "artifactPath": str(review.get("artifactPath", "")),
    }


def _ship_summary(run: DeliveryRun | None) -> dict[str, Any]:
    if run is None or not isinstance(getattr(run, "ship", None), dict):
        return {"status": "pending"}
    ship = run.ship
    return {
        "status": str(ship.get("status", "pending")),
        "attempts": ship.get("attempts", 0),
        "commit": str(ship.get("commit", "")),
        "branch": str(ship.get("branch", "")),
        "prUrl": str(ship.get("prUrl", "")),
        "lastError": str(ship.get("lastError", "")),
    }


def _status_from_lane(root: Path, feature: str) -> tuple[str | None, dict[str, Any]]:
    lane = load_feature_lane(root, feature)
    if lane is None:
        return None, {}
    payload = feature_lane_payload(root, lane)
    status = str(payload.get("status", "")).strip()
    if status == "released":
        return None, payload
    if status == "completed":
        return "completed", payload
    if status in WORK_ORDER_STATUSES:
        return status, payload
    return None, payload


def _phase_from_status(status: str, fallback: str) -> str:
    mapping = {
        "queued": "plan",
        "leased": "plan",
        "planning": "plan",
        "planned": "plan",
        "implementing": "implement",
        "reviewing": "review",
        "shipping": "ship",
    }
    return mapping.get(status, fallback or "unknown")


def _derive_status(
    root: Path,
    feature: str,
    run: DeliveryRun | None,
    phase: str,
    attention_summary: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    lane_status, lane_payload = _status_from_lane(root, feature)
    highest = str(attention_summary.get("highestSeverity", "ok"))
    feature_dir = _feature_dir(root, feature)
    has_context = (feature_dir / "CONTEXT.json").exists()
    has_plan = _has_plan(feature_dir)
    if run is None:
        if lane_status:
            return lane_status, lane_payload
        if phase in {"ship"}:
            return "shipping", lane_payload
        if phase in {"review"}:
            return "reviewing", lane_payload
        if has_plan or phase in {"plan", "implement"}:
            return "planning", lane_payload
        if has_context or (feature_dir / "FEATURE.json").exists():
            return "queued", lane_payload
        return "queued", lane_payload
    ship = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    review = run.review if isinstance(getattr(run, "review", None), dict) else {}
    readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    if ship.get("status") == "completed":
        return "completed", lane_payload
    if ship.get("status") in {"failed"}:
        return "blocked", lane_payload
    if ship.get("status") in {"ready", "in_progress"} or phase == "ship":
        return "shipping", lane_payload
    if review.get("finalVerdict") == "fail":
        return "blocked", lane_payload
    if review.get("status") in {"in_progress", "completed"} or readiness.get("status") == "ready" or phase == "review":
        return "reviewing", lane_payload
    if run.status in {"failed", "cancelled", "blocked"}:
        return "blocked", lane_payload
    if integration.get("status") == "conflict":
        return "blocked", lane_payload
    if highest == "fail" and run.status not in {"completed"}:
        return "blocked", lane_payload
    if phase in {"implement"} or run.status in {"created", "active", "ready_for_review"}:
        return "implementing", lane_payload
    return "planning", lane_payload


def _automation_state(
    root: Path,
    *,
    feature: str,
    status: str,
    profile: dict[str, Any],
    lane_payload: dict[str, Any],
    current_run: DeliveryRun | None,
    next_action: dict[str, Any],
    attention_summary: dict[str, Any],
) -> dict[str, Any]:
    dispatcher = dispatcher_settings_cfg(load_workflow_config(root))
    lane_health = lane_payload.get("health", {}) if isinstance(lane_payload.get("health"), dict) else {}
    automation_hint = next_action.get("automation", {}) if isinstance(next_action, dict) else {}
    auto_review = profile_auto_review(profile)
    auto_ship = profile_auto_ship(profile)
    config = {
        "dispatcherEnabled": dispatcher["enabled"],
        "autoPlan": profile_auto_plan(profile),
        "autoAdvance": profile_auto_advance(profile),
        "autoReview": auto_review,
        "autoShip": auto_ship,
        "profilePolicy": {
            "requiresTracking": profile_ship_require_tracking(profile),
            "requiresPullRequest": profile_ship_require_pull_request(profile),
        },
    }
    if lane_health.get("stale") and not current_run:
        reason = "Feature lane lease expired before execution advanced."
        if lane_health.get("reason") == "worktree_missing":
            reason = "Feature lane worktree is missing and needs to be reclaimed or recreated."
        return {
            "state": "lane_stale",
            "owner": "patrol",
            "reason": reason,
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "queued":
        return {
            "state": "waiting_for_dispatch" if dispatcher["enabled"] else "dispatcher_disabled",
            "owner": "dispatcher",
            "reason": "Ready feature is queued for a free feature lane."
            if dispatcher["enabled"]
            else "Dispatcher is disabled in WORKFLOW.json.",
            "config": config,
            "laneHealth": lane_health,
        }
    if status in {"leased", "planning", "planned"}:
        return {
            "state": str(automation_hint.get("state", "waiting_for_planner")),
            "owner": "planner",
            "reason": str(
                automation_hint.get(
                    "reason",
                    "Planning is the next required step before execution can continue.",
                )
            ),
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "implementing":
        return {
            "state": "waiting_for_execution" if current_run is not None else "waiting_for_run_creation",
            "owner": "implementer",
            "reason": "Active delivery run can continue automatically through deterministic task state."
            if current_run is not None
            else "Feature needs a delivery run before implementation can continue.",
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "reviewing":
        default_reason = (
            "Auto-review will run on next dispatcher tick."
            if auto_review and dispatcher["enabled"]
            else "Review readiness is derived automatically, but review artifact authoring still needs `/review`."
        )
        return {
            "state": str(automation_hint.get("state", "waiting_for_review_command")),
            "owner": "dispatcher" if auto_review and dispatcher["enabled"] else "review",
            "reason": str(automation_hint.get("reason", default_reason)),
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "shipping":
        default_reason = (
            "Auto-ship will run on next dispatcher tick."
            if auto_ship and dispatcher["enabled"]
            else "Ship readiness is derived automatically, but tracked ship completion still needs `/ship`."
        )
        return {
            "state": str(automation_hint.get("state", "waiting_for_ship_command")),
            "owner": "dispatcher" if auto_ship and dispatcher["enabled"] else "ship",
            "reason": str(automation_hint.get("reason", default_reason)),
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "blocked":
        highest = str(attention_summary.get("highestSeverity", "warn")).strip() or "warn"
        return {
            "state": "blocked",
            "owner": "attention",
            "reason": f"Blocking findings are present (highest severity: {highest}).",
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "completed":
        return {
            "state": "complete",
            "owner": "system",
            "reason": "Feature work order is completed.",
            "config": config,
            "laneHealth": lane_health,
        }
    if status == "cancelled":
        return {
            "state": "cancelled",
            "owner": "system",
            "reason": "Feature work order is cancelled.",
            "config": config,
            "laneHealth": lane_health,
        }
    return {
        "state": "unknown",
        "owner": "system",
        "reason": "Automation state is unknown.",
        "config": config,
        "laneHealth": lane_health,
    }


def _default_next_action(feature: str, status: str) -> dict[str, Any]:
    if status == "queued":
        return {
            "kind": "dispatch",
            "summary": "Lease this ready feature into an execution lane.",
            "command": f"python3 .cnogo/scripts/workflow_memory.py dispatch-ready --feature {feature}",
        }
    if status in {"leased", "planning", "planned"}:
        return {
            "kind": "plan",
            "summary": "Generate or resume the deterministic plan for this feature lane.",
            "command": f"python3 .cnogo/scripts/workflow_memory.py plan-auto {feature}",
            "automation": {
                "state": "waiting_for_planner",
                "reason": "Dispatcher or patrol can run deterministic planning automatically when profile policy allows.",
            },
        }
    if status == "reviewing":
        return {
            "kind": "review",
            "summary": "Continue or complete review for the latest run.",
            "command": f"/review {feature}",
            "automation": {
                "state": "waiting_for_review_command",
                "reason": "Review state is tracked automatically, but review artifact authoring still runs through `/review`.",
            },
        }
    if status == "shipping":
        return {
            "kind": "ship",
            "summary": "Complete ship tracking for the latest accepted run.",
            "command": f"/ship {feature}",
            "automation": {
                "state": "waiting_for_ship_command",
                "reason": "Ship readiness is derived automatically, but tracked ship completion still runs through `/ship`.",
            },
        }
    if status == "blocked":
        return {
            "kind": "attention",
            "summary": "Resolve the blocking finding or retry the latest run.",
            "command": f"python3 .cnogo/scripts/workflow_memory.py work-show {feature}",
        }
    return {
        "kind": "implement",
        "summary": "Continue implementing the latest run.",
        "command": f"/implement {feature}",
    }


def build_work_order(
    root: Path,
    feature: str,
    *,
    current_run: DeliveryRun | None = None,
    runs: list[DeliveryRun] | None = None,
    attention_items: list[dict[str, Any]] | None = None,
    existing: WorkOrder | None = None,
) -> WorkOrder:
    feature = feature.strip()
    runs = runs if runs is not None else _load_feature_runs(root, feature)
    current_run = current_run or (runs[0] if runs else latest_delivery_run(root, feature))
    current_run_id = current_run.run_id if current_run is not None else ""
    phase = _feature_phase(root, feature)
    attention_summary = _feature_attention_summary(root, feature, attention_items=attention_items)
    status, lane_payload = _derive_status(root, feature, current_run, phase, attention_summary)
    profile = {}
    if current_run is not None and isinstance(getattr(current_run, "profile", None), dict):
        profile = dict(current_run.profile)
    run_history = [_run_history_entry(root, run) for run in runs]
    next_action = (
        next_delivery_run_action(current_run)
        if current_run is not None and status in {"implementing", "reviewing", "shipping", "blocked"}
        else _default_next_action(feature, status)
    )
    automation_state = _automation_state(
        root,
        feature=feature,
        status=status,
        profile=profile,
        lane_payload=lane_payload,
        current_run=current_run,
        next_action=next_action if isinstance(next_action, dict) else {},
        attention_summary=attention_summary,
    )
    created_at = existing.created_at if isinstance(existing, WorkOrder) and existing.created_at else _now_iso()
    return WorkOrder(
        work_order_id=feature,
        feature=feature,
        status=status,
        current_phase=_phase_from_status(status, phase),
        profile=profile,
        current_run_id=current_run_id,
        run_history=run_history,
        artifact_paths=_latest_feature_artifacts(root, feature, current_run),
        queue_position=existing.queue_position if isinstance(existing, WorkOrder) else 0,
        lane=lane_payload,
        attention_summary=attention_summary,
        review_summary=_review_summary(current_run),
        ship_summary=_ship_summary(current_run),
        memory_sync=dict(existing.memory_sync) if isinstance(existing, WorkOrder) else {},
        automation_state=automation_state,
        next_action=next_action if isinstance(next_action, dict) else _default_next_action(feature, status),
        created_at=created_at,
    )


def sync_work_order(
    root: Path,
    feature: str,
    *,
    current_run: DeliveryRun | None = None,
    attention_items: list[dict[str, Any]] | None = None,
) -> WorkOrder:
    reclaim_stale_feature_lanes(root, feature_filter=feature)
    existing = load_work_order(root, feature)
    order = build_work_order(
        root,
        feature,
        current_run=current_run,
        attention_items=attention_items,
        existing=existing,
    )
    memory_sync = {
        "status": "skipped",
        "reason": "memory_db_missing",
        "syncedAt": _now_iso(),
    }
    try:
        from scripts.memory.insights import sync_feature_memory
        from scripts.memory.runtime import db_path as _memory_db_path

        run_payload = current_run.to_dict() if current_run is not None else {}
        if _memory_db_path(root).exists():
            sync_result = sync_feature_memory(
                root,
                feature,
                work_order=order.to_dict(),
                run=run_payload,
                trigger="work_order_sync",
            )
            memory_sync = {"status": "ok", "syncedAt": _now_iso(), **sync_result}
    except Exception as exc:
        memory_sync = {
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "syncedAt": _now_iso(),
        }
    order.memory_sync = memory_sync
    save_work_order(order, root)

    # Phase auto-advance: sync old phase system from work order status.
    # Only advance for active execution states — not queued/leased/planning/planned
    # which are pre-dispatch states where premature phase change would alter status derivation.
    if order.status in {"implementing", "reviewing", "shipping", "completed"}:
        try:
            derived_phase = _phase_from_status(order.status, "")
            if derived_phase and derived_phase != "unknown":
                from scripts.memory.phases import set_feature_phase as _set_phase
                _set_phase(root, feature, derived_phase, quiet=True)
        except Exception:
            pass  # Best-effort — phase is compatibility-only.

    return order


def list_work_orders(root: Path, *, feature_filter: str | None = None) -> list[WorkOrder]:
    root_dir = work_orders_dir(root)
    orders: list[WorkOrder] = []
    if root_dir.is_dir():
        for path in sorted(root_dir.glob("*.json")):
            if feature_filter and path.stem != feature_filter:
                continue
            payload = _read_json(path)
            if isinstance(payload, dict):
                orders.append(WorkOrder.from_dict(payload))
    orders.sort(
        key=lambda order: (
            0 if order.status == "queued" else 1,
            order.queue_position if order.status == "queued" else 10_000,
            -_updated_sort_value(order.updated_at),
            order.feature,
        )
    )
    return orders


def _discover_features(root: Path) -> set[str]:
    features: set[str] = set()
    features_root = root / "docs" / "planning" / "work" / "features"
    if features_root.is_dir():
        for path in features_root.iterdir():
            if path.is_dir():
                features.add(path.name)
    runs_root = runtime_path(root, "runs")
    if runs_root.is_dir():
        for path in runs_root.iterdir():
            if path.is_dir():
                features.add(path.name)
    work_root = work_orders_dir(root)
    if work_root.is_dir():
        for path in work_root.glob("*.json"):
            features.add(path.stem)
    lanes_root = runtime_path(root, "lanes")
    if lanes_root.is_dir():
        for path in lanes_root.glob("*.json"):
            features.add(path.stem)
    payload = _read_json(runtime_path(root, "feature-phases.json")) or {}
    entries = payload.get("features")
    if isinstance(entries, dict):
        features.update(str(key).strip() for key in entries.keys() if str(key).strip())
    return features


def _queue_sort_key(root: Path, order: WorkOrder) -> tuple[Any, ...]:
    return (
        _feature_priority(root, order.feature),
        _sequence_index(root, order.feature),
        order.feature,
    )


def _updated_sort_value(updated_at: str) -> float:
    parsed = parse_iso_timestamp(updated_at)
    if parsed is None:
        return 0.0
    try:
        return parsed.timestamp()
    except (OverflowError, OSError, ValueError):
        return 0.0


def sync_all_work_orders(root: Path, *, feature_filter: str | None = None) -> list[WorkOrder]:
    queue = load_attention_queue(root) or {}
    items = [dict(item) for item in queue.get("items", []) if isinstance(item, dict)]
    features = {feature_filter} if feature_filter else _discover_features(root)
    synced: list[WorkOrder] = []
    for feature in sorted(feature for feature in features if feature):
        scoped_items = [item for item in items if str(item.get("feature", "")).strip() == feature]
        synced.append(sync_work_order(root, feature, attention_items=scoped_items))
    queued = sorted((order for order in synced if order.status == "queued"), key=lambda order: _queue_sort_key(root, order))
    positions = {order.feature: index + 1 for index, order in enumerate(queued)}
    for order in synced:
        position = positions.get(order.feature, 0)
        if order.queue_position != position:
            order.queue_position = position
            save_work_order(order, root)
    synced.sort(
        key=lambda order: (
            0 if order.status == "queued" else 1,
            order.queue_position if order.status == "queued" else 10_000,
            -_updated_sort_value(order.updated_at),
            order.feature,
        )
    )
    return synced


def next_work_order_action(root: Path, feature: str) -> dict[str, Any]:
    order = sync_work_order(root, feature)
    return dict(order.next_action)
