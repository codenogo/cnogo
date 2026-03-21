"""Feature-level Work Order rollups built on top of delivery runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.timestamps import parse_iso_timestamp

from .delivery_run import DeliveryRun, delivery_run_dir, latest_delivery_run, load_delivery_run
from .implement import next_delivery_run_action
from .watch_artifacts import load_attention_queue

WORK_ORDER_SCHEMA_VERSION = 1
WORK_ORDER_STATUSES = frozenset(
    {
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
    payload = _read_json(root / _PHASE_STATE_PATH) or {}
    features = payload.get("features")
    if isinstance(features, dict):
        entry = features.get(feature)
        if isinstance(entry, dict):
            phase = entry.get("phase")
            if isinstance(phase, str) and phase.strip():
                return phase.strip()
    return "unknown"


def work_orders_dir(root: Path) -> Path:
    return root / _WORK_ORDERS_DIR


def work_order_path(root: Path, feature: str) -> Path:
    return work_orders_dir(root) / f"{feature}.json"


@dataclass
class WorkOrder:
    schema_version: int = WORK_ORDER_SCHEMA_VERSION
    work_order_id: str = ""
    feature: str = ""
    status: str = "planned"
    current_phase: str = "unknown"
    profile: dict[str, Any] = field(default_factory=dict)
    current_run_id: str = ""
    run_history: list[dict[str, Any]] = field(default_factory=list)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    attention_summary: dict[str, Any] = field(default_factory=dict)
    review_summary: dict[str, Any] = field(default_factory=dict)
    ship_summary: dict[str, Any] = field(default_factory=dict)
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
            "attentionSummary": self.attention_summary,
            "reviewSummary": self.review_summary,
            "shipSummary": self.ship_summary,
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
            status=str(data.get("status", "planned")),
            current_phase=str(data.get("currentPhase", "unknown")),
            profile=dict(data.get("profile", {})) if isinstance(data.get("profile"), dict) else {},
            current_run_id=str(data.get("currentRunId", "")),
            run_history=[dict(item) for item in data.get("runHistory", []) if isinstance(item, dict)],
            artifact_paths=dict(data.get("artifactPaths", {}))
            if isinstance(data.get("artifactPaths"), dict)
            else {},
            attention_summary=dict(data.get("attentionSummary", {}))
            if isinstance(data.get("attentionSummary"), dict)
            else {},
            review_summary=dict(data.get("reviewSummary", {}))
            if isinstance(data.get("reviewSummary"), dict)
            else {},
            ship_summary=dict(data.get("shipSummary", {}))
            if isinstance(data.get("shipSummary"), dict)
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


def _latest_feature_artifacts(root: Path, feature: str, current_run: DeliveryRun | None) -> dict[str, str]:
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
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
        "path": str(work_order_path(root, run.feature).parent.parent / "runs" / run.feature / f"{run.run_id}.json"),
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


def _derive_status(run: DeliveryRun | None, phase: str, attention_summary: dict[str, Any]) -> str:
    highest = str(attention_summary.get("highestSeverity", "ok"))
    if run is None:
        if phase in {"ship"}:
            return "shipping"
        if phase in {"review"}:
            return "reviewing"
        return "planned"
    ship = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    review = run.review if isinstance(getattr(run, "review", None), dict) else {}
    readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    if ship.get("status") == "completed":
        return "completed"
    if ship.get("status") in {"failed"}:
        return "blocked"
    if ship.get("status") in {"ready", "in_progress"} or phase == "ship":
        return "shipping"
    if review.get("finalVerdict") == "fail":
        return "blocked"
    if review.get("status") in {"in_progress", "completed"} or readiness.get("status") == "ready" or phase == "review":
        return "reviewing"
    if run.status in {"failed", "cancelled", "blocked"}:
        return "blocked"
    if integration.get("status") == "conflict":
        return "blocked"
    if highest == "fail" and run.status not in {"completed"}:
        return "blocked"
    if phase in {"implement"} or run.status in {"created", "active", "ready_for_review"}:
        return "implementing"
    return "planned"


def _default_next_action(feature: str, status: str) -> dict[str, Any]:
    if status == "planned":
        return {
            "kind": "plan",
            "summary": "Continue planning the feature and prepare a delivery run.",
            "command": f"/plan {feature}",
        }
    if status == "reviewing":
        return {
            "kind": "review",
            "summary": "Continue or complete review for the latest run.",
            "command": f"/review {feature}",
        }
    if status == "shipping":
        return {
            "kind": "ship",
            "summary": "Complete ship tracking for the latest accepted run.",
            "command": f"/ship {feature}",
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
    status = _derive_status(current_run, phase, attention_summary)
    profile = {}
    if current_run is not None and isinstance(getattr(current_run, "profile", None), dict):
        profile = dict(current_run.profile)
    run_history = [_run_history_entry(root, run) for run in runs]
    next_action = (
        next_delivery_run_action(current_run)
        if current_run is not None and status in {"implementing", "reviewing", "shipping", "blocked"}
        else _default_next_action(feature, status)
    )
    created_at = existing.created_at if isinstance(existing, WorkOrder) and existing.created_at else _now_iso()
    return WorkOrder(
        work_order_id=feature,
        feature=feature,
        status=status,
        current_phase=phase,
        profile=profile,
        current_run_id=current_run_id,
        run_history=run_history,
        artifact_paths=_latest_feature_artifacts(root, feature, current_run),
        attention_summary=attention_summary,
        review_summary=_review_summary(current_run),
        ship_summary=_ship_summary(current_run),
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
    existing = load_work_order(root, feature)
    order = build_work_order(
        root,
        feature,
        current_run=current_run,
        attention_items=attention_items,
        existing=existing,
    )
    save_work_order(order, root)
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
        key=lambda order: parse_iso_timestamp(order.updated_at) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return orders


def _discover_features(root: Path) -> set[str]:
    features: set[str] = set()
    features_root = root / "docs" / "planning" / "work" / "features"
    if features_root.is_dir():
        for path in features_root.iterdir():
            if path.is_dir():
                features.add(path.name)
    runs_root = root / ".cnogo" / "runs"
    if runs_root.is_dir():
        for path in runs_root.iterdir():
            if path.is_dir():
                features.add(path.name)
    work_root = work_orders_dir(root)
    if work_root.is_dir():
        for path in work_root.glob("*.json"):
            features.add(path.stem)
    payload = _read_json(root / _PHASE_STATE_PATH) or {}
    entries = payload.get("features")
    if isinstance(entries, dict):
        features.update(str(key).strip() for key in entries.keys() if str(key).strip())
    return features


def sync_all_work_orders(root: Path, *, feature_filter: str | None = None) -> list[WorkOrder]:
    queue = load_attention_queue(root) or {}
    items = [dict(item) for item in queue.get("items", []) if isinstance(item, dict)]
    features = {feature_filter} if feature_filter else _discover_features(root)
    synced: list[WorkOrder] = []
    for feature in sorted(feature for feature in features if feature):
        scoped_items = [item for item in items if str(item.get("feature", "")).strip() == feature]
        synced.append(sync_work_order(root, feature, attention_items=scoped_items))
    synced.sort(
        key=lambda order: parse_iso_timestamp(order.updated_at) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return synced


def next_work_order_action(root: Path, feature: str) -> dict[str, Any]:
    order = sync_work_order(root, feature)
    return dict(order.next_action)
