"""Persistent watch-report and attention-queue helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_WATCH_DIR = Path(".cnogo") / "watch"
_LATEST_REPORT = "latest.json"
_ATTENTION_QUEUE = "attention.json"


def watch_dir(root: Path) -> Path:
    return root / _WATCH_DIR


def watch_report_path(root: Path) -> Path:
    return watch_dir(root) / _LATEST_REPORT


def attention_queue_path(root: Path) -> Path:
    return watch_dir(root) / _ATTENTION_QUEUE


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


def _severity_rank(value: str) -> int:
    return {"fail": 0, "warn": 1}.get(value, 2)


def _summarize_attention_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts: dict[str, int] = {}
    feature_counts: dict[str, int] = {}
    for item in items:
        severity = str(item.get("severity", "warn"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        feature = str(item.get("feature", "")).strip()
        if feature:
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
    return {
        "totalItems": len(items),
        "severityCounts": severity_counts,
        "featureCounts": feature_counts,
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


def persist_watch_report(root: Path, report: dict[str, Any]) -> dict[str, Any]:
    report_copy = dict(report)
    queue = build_attention_queue(report_copy)
    report_location = watch_report_path(root)
    attention_location = attention_queue_path(root)
    report_copy["paths"] = {
        "report": str(report_location),
        "attention": str(attention_location),
    }
    queue["sourceReportPath"] = str(report_location)
    queue["paths"] = {"attention": str(attention_location)}
    _write_json(report_location, report_copy)
    _write_json(attention_location, queue)
    return {
        "report": report_copy,
        "attention": queue,
    }


def load_watch_report(root: Path) -> dict[str, Any] | None:
    return _read_json(watch_report_path(root))


def load_attention_queue(root: Path) -> dict[str, Any] | None:
    return _read_json(attention_queue_path(root))


def filter_attention_queue(
    queue: dict[str, Any],
    *,
    feature_filter: str | None = None,
) -> dict[str, Any]:
    if not feature_filter:
        return queue
    items = queue.get("items", [])
    if not isinstance(items, list):
        items = []
    filtered = [
        dict(item)
        for item in items
        if isinstance(item, dict) and str(item.get("feature", "")).strip() == feature_filter
    ]
    out = dict(queue)
    out["items"] = filtered
    out["summary"] = _summarize_attention_items(filtered)
    return out
