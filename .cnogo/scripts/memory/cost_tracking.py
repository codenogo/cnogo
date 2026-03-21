"""Cost event recording and aggregation helpers for the memory engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import runtime as _runtime


def record_cost_event(
    root: Path,
    issue_id: str,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_tokens: int = 0,
    model: str = "",
    cost_usd: float = 0.0,
    actor: str = "claude",
) -> None:
    """Record a cost_report event for an issue."""
    conn = _runtime.conn(root)
    try:
        _runtime.emit(
            conn,
            issue_id,
            "cost_report",
            actor,
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_tokens": cache_tokens,
                "model": model,
                "cost_usd": cost_usd,
            },
        )
        conn.commit()
    finally:
        conn.close()


def get_cost_summary(root: Path, feature_slug: str) -> dict[str, Any]:
    """Aggregate cost_report events for all issues in a feature."""
    conn = _runtime.conn(root)
    try:
        rows = conn.execute(
            """SELECT e.data FROM events e
               JOIN issues i ON i.id = e.issue_id
               WHERE e.event_type = 'cost_report'
               AND i.feature_slug = ?""",
            (feature_slug,),
        ).fetchall()
    finally:
        conn.close()

    total_tokens = 0
    total_cost_usd = 0.0
    for row in rows:
        try:
            data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
        except (json.JSONDecodeError, TypeError):
            data = {}
        total_tokens += data.get("input_tokens", 0) + data.get("output_tokens", 0)
        total_cost_usd += data.get("cost_usd", 0.0)

    return {
        "feature_slug": feature_slug,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost_usd,
        "event_count": len(rows),
    }
