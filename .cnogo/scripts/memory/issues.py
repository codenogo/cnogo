"""Issue-centric helpers for the memory engine façade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import storage as _st
from .identity import content_hash as _content_hash
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .runtime import emit as _emit
from .storage import with_retry as _with_retry


def show_issue(root: Path, issue_id: str) -> Any | None:
    conn = _conn(root)
    try:
        issue = _st.get_issue(conn, issue_id)
        if issue is None:
            return None
        issue.labels = _st.get_labels(conn, issue_id)
        issue.deps = _st.get_dependencies(conn, issue_id)
        issue.blocks_issues = [issue_row.id for issue_row in _st.get_blocks(conn, issue_id)]
        issue.recent_events = _st.get_events(conn, issue_id, limit=10)
        return issue
    finally:
        conn.close()


def update_issue(
    root: Path,
    issue_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    assignee: str | None = None,
    metadata: dict | None = None,
    comment: str | None = None,
    actor: str = "claude",
) -> Any:
    conn = _conn(root)
    try:
        existing = _st.get_issue(conn, issue_id)
        if existing is None:
            raise ValueError(f"Issue {issue_id} not found")

        fields: dict[str, Any] = {}
        changes: dict[str, Any] = {}

        if title is not None and title != existing.title:
            fields["title"] = title
            changes["title"] = {"old": existing.title, "new": title}
        if description is not None and description != existing.description:
            fields["description"] = description
            changes["description"] = True
        if priority is not None and priority != existing.priority:
            fields["priority"] = priority
            changes["priority"] = {"old": existing.priority, "new": priority}
        if assignee is not None and assignee != existing.assignee:
            fields["assignee"] = assignee
            changes["assignee"] = {"old": existing.assignee, "new": assignee}
        if metadata is not None:
            merged = {**existing.metadata, **metadata}
            fields["metadata"] = merged
            changes["metadata_keys"] = list(metadata.keys())

        if fields:
            new_title = fields.get("title", existing.title)
            new_desc = fields.get("description", existing.description)
            fields["content_hash"] = _content_hash(new_title, new_desc, existing.issue_type)
            _st.update_issue_fields(conn, issue_id, **fields)

        if comment:
            _emit(conn, issue_id, "commented", actor, {"comment": comment})
        if changes:
            _emit(conn, issue_id, "updated", actor, changes)

        conn.commit()
        result = _st.get_issue(conn, issue_id)
    finally:
        conn.close()
    _auto_export(root)
    return result


def claim_issue(root: Path, issue_id: str, *, actor: str) -> Any:
    def _do_claim() -> Any:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = _st.get_issue(conn, issue_id)
            if existing is None:
                raise ValueError(f"Issue {issue_id} not found")
            if existing.status == "closed":
                raise ValueError(f"Issue {issue_id} is closed")
            if existing.assignee == actor and existing.status == "in_progress":
                if existing.state == "in_progress":
                    conn.commit()
                    return existing
                raise ValueError(
                    f"Issue {issue_id} already owned by {actor!r} but state is "
                    f"{existing.state!r}; cannot re-claim"
                )

            ok = _st.claim_issue(conn, issue_id, actor)
            if not ok:
                raise ValueError(f"Issue {issue_id} already claimed by {existing.assignee!r}")

            _st.update_issue_fields(conn, issue_id, state="in_progress")
            _emit(conn, issue_id, "claimed", actor)
            conn.commit()
            return _st.get_issue(conn, issue_id)
        finally:
            conn.close()

    result = _with_retry(_do_claim)
    _auto_export(root)
    return result
