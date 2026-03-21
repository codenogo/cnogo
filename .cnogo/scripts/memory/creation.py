"""Issue creation helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage as _st
from .graph import rebuild_blocked_cache as _rebuild_blocked_cache
from .identity import content_hash as _content_hash
from .identity import generate_child_id as _child_id
from .identity import generate_id as _gen_id
from .models import Dependency, Issue
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .runtime import emit as _emit
from .storage import with_retry as _with_retry


def create_issue(
    root: Path,
    title: str,
    *,
    issue_type: str = "task",
    parent: str | None = None,
    feature_slug: str | None = None,
    plan_number: str | None = None,
    phase: str | None = None,
    priority: int = 2,
    labels: list[str] | None = None,
    description: str | None = None,
    metadata: dict | None = None,
    owner_actor: str = "",
    actor: str = "claude",
) -> Issue:
    """Create a new issue and persist initial relationships/events."""

    def _do_create() -> Issue:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            now = _st._now()

            if parent is not None:
                if not _st.id_exists(conn, parent):
                    raise ValueError(f"Parent issue {parent} not found")
                child_num = _st.next_child_number(conn, parent)
                issue_id = _child_id(parent, child_num)
            else:
                issue_id = ""
                for nonce in range(10):
                    candidate = _gen_id(title, actor, nonce=nonce)
                    if not _st.id_exists(conn, candidate):
                        issue_id = candidate
                        break
                if not issue_id:
                    for nonce in range(10):
                        candidate = _gen_id(title, actor, id_bytes=5, nonce=nonce)
                        if not _st.id_exists(conn, candidate):
                            issue_id = candidate
                            break
                if not issue_id:
                    raise RuntimeError("Failed to generate unique ID after retries")

            chash = _content_hash(title, description or "", issue_type)
            issue = Issue(
                id=issue_id,
                title=title,
                content_hash=chash,
                description=description or "",
                status="open",
                state="open",
                issue_type=issue_type,
                priority=priority,
                assignee="",
                owner_actor=owner_actor or "",
                feature_slug=feature_slug or "",
                plan_number=plan_number or "",
                phase=_st.normalize_phase(phase or "discuss"),
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )

            _st.insert_issue(conn, issue)

            for label in labels or []:
                _st.add_label(conn, issue_id, label)
            issue.labels = labels or []

            if parent is not None:
                dep = Dependency(
                    issue_id=issue_id,
                    depends_on_id=parent,
                    dep_type="parent-child",
                    created_at=now,
                )
                _st.insert_dependency(conn, dep)

            _emit(
                conn,
                issue_id,
                "created",
                actor,
                {
                    "title": title,
                    "issue_type": issue_type,
                    "parent": parent,
                },
            )

            _rebuild_blocked_cache(conn)
            conn.commit()
            return issue
        finally:
            conn.close()

    result = _with_retry(_do_create)
    _auto_export(root)
    return result
