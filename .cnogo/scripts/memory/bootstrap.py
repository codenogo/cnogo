"""Bootstrap helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path

from . import storage as _st
from .runtime import db_path as _db_path


def init_memory(root: Path) -> None:
    path = _db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _st.connect(path)
    conn.close()


def is_initialized(root: Path) -> bool:
    return _db_path(root).exists()
