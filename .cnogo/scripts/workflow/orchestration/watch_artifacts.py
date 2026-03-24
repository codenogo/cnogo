"""Persistent watch-report and attention-queue helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.workflow.shared.atomic_write import atomic_write_json
from scripts.workflow.shared.runtime_root import runtime_path

_WATCH_DIR = Path(".cnogo") / "watch"
_LATEST_REPORT = "latest.json"
_ATTENTION_QUEUE = "attention.json"
_HISTORY_DIR = "history"


def watch_dir(root: Path) -> Path:
    return runtime_path(root, "watch")


def watch_report_path(root: Path) -> Path:
    return watch_dir(root) / _LATEST_REPORT


def attention_queue_path(root: Path) -> Path:
    return watch_dir(root) / _ATTENTION_QUEUE


def watch_history_dir(root: Path) -> Path:
    return watch_dir(root) / _HISTORY_DIR


def watch_snapshot_path(root: Path, checked_at: str) -> Path:
    stamp = checked_at.strip().replace(":", "-")
    if not stamp:
        stamp = "snapshot"
    return watch_history_dir(root) / f"{stamp}.json"


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


def _severity_rank(value: str) -> int:
    return {"fail": 0, "warn": 1}.get(value, 2)


def _attention_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(item.get("feature", "")).strip(),
        str(item.get("runId", "")).strip(),
        str(item.get("kind", "")).strip(),
        str(item.get("path", "")).strip(),
    )


def _summarize_attention_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}
    feature_counts: dict[str, int] = {}
    highest_severity = "ok"
    for item in items:
        severity = str(item.get("severity", "warn"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if severity == "fail":
            highest_severity = "fail"
        elif severity == "warn" and highest_severity == "ok":
            highest_severity = "warn"
        feature = str(item.get("feature", "")).strip()
        if feature:
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
    return {
        "totalItems": len(items),
        "severityCounts": severity_counts,
        "featureCounts": feature_counts,
        "highestSeverity": highest_severity,
    }


def build_attention_queue(report: dict[str, Any]) -> dict[str, Any]:
    checked_at = str(report.get("checkedAt", "")).strip()
    findings = report.get("findings", [])
    items: list[dict[str, Any]] = []
    if isinstance(findings, list):
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            items.append(dict(finding))
    items.sort(
        key=lambda item: (
            _severity_rank(str(item.get("severity", "warn"))),
            -(float(item.get("minutesStale")) if isinstance(item.get("minutesStale"), (int, float)) else -1.0),
            str(item.get("feature", "")),
            str(item.get("runId", "")),
            str(item.get("kind", "")),
        )
    )
    return {
        "checkedAt": checked_at,
        "items": items,
        "summary": _summarize_attention_items(items),
    }


def diff_attention_queues(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> dict[str, Any]:
    previous_items = previous.get("items", []) if isinstance(previous, dict) else []
    current_items = current.get("items", []) if isinstance(current, dict) else []
    previous_map = {
        _attention_key(item): dict(item)
        for item in previous_items
        if isinstance(item, dict)
    }
    current_map = {
        _attention_key(item): dict(item)
        for item in current_items
        if isinstance(item, dict)
    }
    new_items = [current_map[key] for key in current_map.keys() - previous_map.keys()]
    resolved_items = [previous_map[key] for key in previous_map.keys() - current_map.keys()]
    ongoing_items = [current_map[key] for key in current_map.keys() & previous_map.keys()]
    return {
        "newItems": sorted(new_items, key=lambda item: (_severity_rank(str(item.get("severity", "warn"))), str(item.get("kind", "")))),
        "resolvedItems": sorted(resolved_items, key=lambda item: (_severity_rank(str(item.get("severity", "warn"))), str(item.get("kind", "")))),
        "ongoingItems": sorted(ongoing_items, key=lambda item: (_severity_rank(str(item.get("severity", "warn"))), str(item.get("kind", "")))),
        "summary": {
            "new": len(new_items),
            "resolved": len(resolved_items),
            "ongoing": len(ongoing_items),
        },
    }


def persist_watch_report(root: Path, report: dict[str, Any], *, archive: bool = True) -> dict[str, Any]:
    report_copy = dict(report)
    previous_queue = load_attention_queue(root)
    queue = build_attention_queue(report_copy)
    delta = diff_attention_queues(previous_queue, queue)
    report_location = watch_report_path(root)
    attention_location = attention_queue_path(root)
    snapshot_location = watch_snapshot_path(root, str(report_copy.get("checkedAt", "")))
    report_copy["paths"] = {
        "report": str(report_location),
        "attention": str(attention_location),
    }
    if archive:
        report_copy["paths"]["snapshot"] = str(snapshot_location)
    report_copy["deltaSummary"] = delta["summary"]
    queue["sourceReportPath"] = str(report_location)
    queue["paths"] = {"attention": str(attention_location)}
    if archive:
        queue["paths"]["snapshot"] = str(snapshot_location)
    queue["deltaSummary"] = delta["summary"]
    _write_json(report_location, report_copy)
    _write_json(attention_location, queue)
    snapshot: dict[str, Any] | None = None
    if archive:
        snapshot = {
            "checkedAt": str(report_copy.get("checkedAt", "")),
            "reportSummary": dict(report_copy.get("summary", {}))
            if isinstance(report_copy.get("summary"), dict)
            else {},
            "attentionSummary": dict(queue.get("summary", {}))
            if isinstance(queue.get("summary"), dict)
            else {},
            "deltaSummary": dict(delta.get("summary", {}))
            if isinstance(delta.get("summary"), dict)
            else {},
            "paths": {
                "report": str(report_location),
                "attention": str(attention_location),
            },
        }
        _write_json(snapshot_location, snapshot)
    return {
        "report": report_copy,
        "attention": queue,
        "delta": delta,
        "snapshot": snapshot or {},
    }


def load_watch_report(root: Path) -> dict[str, Any] | None:
    return _read_json(watch_report_path(root))


def load_attention_queue(root: Path) -> dict[str, Any] | None:
    return _read_json(attention_queue_path(root))


def filter_attention_queue(
    queue: dict[str, Any],
    *,
    feature_filter: str | None = None,
    severities: set[str] | None = None,
    kinds: set[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    items = queue.get("items", [])
    if not isinstance(items, list):
        items = []
    filtered: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if feature_filter and str(item.get("feature", "")).strip() != feature_filter:
            continue
        if severities and str(item.get("severity", "")).strip() not in severities:
            continue
        if kinds and str(item.get("kind", "")).strip() not in kinds:
            continue
        filtered.append(dict(item))
    total_before_limit = len(filtered)
    if isinstance(limit, int) and limit > 0:
        filtered = filtered[:limit]
    out = dict(queue)
    out["items"] = filtered
    out["summary"] = _summarize_attention_items(filtered)
    out["summary"]["matchedItems"] = total_before_limit
    return out


def load_watch_history(root: Path, *, limit: int = 10) -> list[dict[str, Any]]:
    history_root = watch_history_dir(root)
    if not history_root.is_dir():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(history_root.glob("*.json"), reverse=True):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        snapshots.append(
            {
                "checkedAt": str(payload.get("checkedAt", "")).strip(),
                "reportSummary": dict(payload.get("reportSummary", {}))
                if isinstance(payload.get("reportSummary"), dict)
                else {},
                "attentionSummary": dict(payload.get("attentionSummary", {}))
                if isinstance(payload.get("attentionSummary"), dict)
                else {},
                "deltaSummary": dict(payload.get("deltaSummary", {}))
                if isinstance(payload.get("deltaSummary"), dict)
                else {},
                "path": str(path),
            }
        )
        if len(snapshots) >= limit:
            break
    return snapshots
