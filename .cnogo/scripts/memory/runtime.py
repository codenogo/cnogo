"""Shared runtime helpers for the memory engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage as _st
from .models import Event

_DB_NAME = "memory.db"
_CNOGO_DIR = ".cnogo"


def db_path(root: Path) -> Path:
    return root / _CNOGO_DIR / _DB_NAME


def conn(root: Path):  # noqa: ANN202
    return _st.connect(db_path(root))


def emit(
    conn_handle,
    issue_id: str,
    event_type: str,
    actor: str,
    data: dict[str, Any] | None = None,
) -> None:
    _st.insert_event(
        conn_handle,
        Event(
            issue_id=issue_id,
            event_type=event_type,
            actor=actor,
            data=data or {},
            created_at=_st._now(),
        ),
    )


def auto_export(root: Path) -> None:
    """Best-effort JSONL export after state-changing operations."""
    try:
        from .sync import export_jsonl as _export

        _export(root)
    except Exception:
        pass
