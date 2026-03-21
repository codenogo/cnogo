"""Query helpers for the memory engine façade."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import storage as _st
from .policy import load_agent_team_settings as _load_agent_team_settings
from .policy import parse_iso_timestamp as _parse_iso_timestamp
from .runtime import conn as _conn


def ready_issues(
    root: Path,
    *,
    assignee: str | None = None,
    feature_slug: str | None = None,
    label: str | None = None,
    limit: int = 20,
) -> list[Any]:
    conn = _conn(root)
    try:
        return _st.ready_issues_query(
            conn,
            assignee=assignee,
            feature_slug=feature_slug,
            label=label,
            limit=limit,
        )
    finally:
        conn.close()


def stalled_task_list(
    root: Path,
    *,
    feature_slug: str | None = None,
    stale_minutes: int | None = None,
) -> list[dict[str, Any]]:
    configured_stale = _load_agent_team_settings(root).get("staleIndicatorMinutes", 10)
    threshold = stale_minutes if isinstance(stale_minutes, int) and stale_minutes > 0 else configured_stale

    conn = _conn(root)
    try:
        issues = _st.list_issues_query(
            conn,
            status="in_progress",
            issue_type="task",
            feature_slug=feature_slug,
            limit=1000,
        )
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    stale: list[dict[str, Any]] = []
    for issue in issues:
        if issue.state != "in_progress":
            continue
        updated = _parse_iso_timestamp(issue.updated_at)
        if updated is None:
            continue
        age_minutes = (now - updated).total_seconds() / 60.0
        if age_minutes < float(threshold):
            continue
        stale.append(
            {
                "id": issue.id,
                "title": issue.title,
                "assignee": issue.assignee,
                "feature": issue.feature_slug,
                "planNumber": issue.plan_number,
                "status": issue.status,
                "state": issue.state,
                "updatedAt": issue.updated_at,
                "minutesStale": round(age_minutes, 1),
            }
        )
    stale.sort(key=lambda item: float(item["minutesStale"]), reverse=True)
    return stale


def list_issue_records(
    root: Path,
    *,
    status: str | None = None,
    issue_type: str | None = None,
    feature_slug: str | None = None,
    parent: str | None = None,
    assignee: str | None = None,
    label: str | None = None,
    limit: int = 100,
) -> list[Any]:
    conn = _conn(root)
    try:
        return _st.list_issues_query(
            conn,
            status=status,
            issue_type=issue_type,
            feature_slug=feature_slug,
            parent=parent,
            assignee=assignee,
            label=label,
            limit=limit,
        )
    finally:
        conn.close()


def issue_stats(root: Path) -> dict[str, Any]:
    conn = _conn(root)
    try:
        return _st.get_stats(conn)
    finally:
        conn.close()
