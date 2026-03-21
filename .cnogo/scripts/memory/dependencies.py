"""Dependency helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage as _st
from .graph import rebuild_blocked_cache as _rebuild_blocked_cache
from .models import Dependency
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .runtime import emit as _emit

_CYCLE_MAX_ITERATIONS = 10_000


def add_dependency(
    root: Path,
    issue_id: str,
    depends_on: str,
    *,
    dep_type: str = "blocks",
    actor: str = "claude",
) -> None:
    conn = _conn(root)
    try:
        if not _st.id_exists(conn, issue_id):
            raise ValueError(f"Issue {issue_id} not found")
        if not _st.id_exists(conn, depends_on):
            raise ValueError(f"Issue {depends_on} not found")

        if would_create_cycle(conn, issue_id, depends_on):
            raise ValueError(f"Adding {issue_id} → {depends_on} would create a cycle")

        dep = Dependency(
            issue_id=issue_id,
            depends_on_id=depends_on,
            dep_type=dep_type,
            created_at=_st._now(),
        )
        _st.insert_dependency(conn, dep)
        _emit(
            conn,
            issue_id,
            "dep_added",
            actor,
            {
                "depends_on": depends_on,
                "dep_type": dep_type,
            },
        )
        _rebuild_blocked_cache(conn)
        conn.commit()
    finally:
        conn.close()
    _auto_export(root)


def remove_dependency(
    root: Path,
    issue_id: str,
    depends_on: str,
    *,
    actor: str = "claude",
) -> None:
    conn = _conn(root)
    try:
        ok = _st.remove_dependency(conn, issue_id, depends_on)
        if ok:
            _emit(conn, issue_id, "dep_removed", actor, {"depends_on": depends_on})
            _rebuild_blocked_cache(conn)
        conn.commit()
    finally:
        conn.close()
    _auto_export(root)


def blockers_for(root: Path, issue_id: str) -> list[Any]:
    conn = _conn(root)
    try:
        return _st.get_blocked_by(conn, issue_id)
    finally:
        conn.close()


def blocks_for(root: Path, issue_id: str) -> list[Any]:
    conn = _conn(root)
    try:
        return _st.get_blocks(conn, issue_id)
    finally:
        conn.close()


def would_create_cycle(conn_handle, issue_id: str, depends_on_id: str) -> bool:
    visited: set[str] = set()
    stack = [depends_on_id]
    iterations = 0
    while stack:
        iterations += 1
        if iterations > _CYCLE_MAX_ITERATIONS:
            raise ValueError(f"Cycle detection exceeded {_CYCLE_MAX_ITERATIONS} iterations")
        current = stack.pop()
        if current == issue_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        rows = conn_handle.execute(
            "SELECT depends_on_id FROM dependencies WHERE issue_id = ?",
            (current,),
        ).fetchall()
        for row in rows:
            stack.append(row["depends_on_id"])
    return False
