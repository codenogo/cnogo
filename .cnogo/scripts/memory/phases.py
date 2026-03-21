"""Phase helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path

from . import storage as _st
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .storage import with_retry as _with_retry


def get_feature_phase(root: Path, feature_slug: str) -> str:
    conn = _conn(root)
    try:
        return _st.get_feature_phase(conn, feature_slug)
    finally:
        conn.close()


def set_feature_phase(root: Path, feature_slug: str, phase: str) -> int:
    def _do_set() -> int:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = _st.set_feature_phase(conn, feature_slug, phase)
            conn.commit()
            return count
        finally:
            conn.close()

    count = _with_retry(_do_set)
    _auto_export(root)
    return count
