#!/usr/bin/env python3
"""Context generation for token-efficient agent consumption.

Generates minimal summaries (~500-1500 tokens) that agents can use
to understand current project state without reading full artifacts.
"""

from __future__ import annotations

from pathlib import Path

from . import storage as _st

_CNOGO_DIR = ".cnogo"
_DB_NAME = "memory.db"


def _conn(root: Path | None = None):  # noqa: ANN202
    r = root or Path(".")
    return _st.connect(r / _CNOGO_DIR / _DB_NAME)


def prime(*, limit: int = 10, root: Path | None = None) -> str:
    """Generate minimal context summary for agent injection.

    Returns ~500-1500 tokens of structured markdown with:
    - Stats overview
    - In-progress work
    - Ready-to-start tasks
    """
    conn = _conn(root)
    try:
        s = _st.get_stats(conn)
        in_progress = _st.list_issues_query(
            conn, status="in_progress", limit=limit
        )
        ready_list = _st.ready_issues_query(conn, limit=limit)

        lines: list[str] = []

        # Header with stats
        open_count = s.get("open", 0)
        active = s.get("in_progress", 0)
        ready_count = s.get("ready", 0)
        blocked = s.get("blocked", 0)
        lines.append(
            f"## Memory: {open_count} open, {active} active,"
            f" {ready_count} ready, {blocked} blocked"
        )
        lines.append("")

        # Active Epics
        epics = _st.list_issues_query(
            conn, issue_type="epic", status="in_progress", limit=limit
        )
        if not epics:
            epics = _st.list_issues_query(
                conn, issue_type="epic", status="open", limit=limit
            )
        if epics:
            lines.append("### Active Epics")
            for epic in epics:
                children = _st.list_issues_query(
                    conn, parent=epic.id, limit=200
                )
                total = len(children)
                closed = sum(1 for c in children if c.status == "closed")
                slug = epic.feature_slug or epic.id
                plan = f" plan {epic.plan_number}" if epic.plan_number else ""
                progress = f" ({closed}/{total} tasks done)" if total else ""
                lines.append(
                    f"- `{epic.id}` **{slug}**{plan}{progress}"
                )
                handoff = epic.metadata.get("handoff", "")
                if handoff:
                    snippet = handoff[:120]
                    if len(handoff) > 120:
                        snippet += "..."
                    lines.append(f"  Handoff: {snippet}")
            lines.append("")

        # In Progress
        if in_progress:
            lines.append("### In Progress")
            for issue in in_progress:
                assignee = f" (@{issue.assignee})" if issue.assignee else ""
                lines.append(
                    f"- `{issue.id}` {issue.title}{assignee}"
                )
            lines.append("")

        # Ready
        if ready_list:
            lines.append("### Ready")
            for issue in ready_list:
                prio = f"[P{issue.priority}]"
                itype = f" ({issue.issue_type})" if issue.issue_type != "task" else ""
                lines.append(
                    f"- {prio} `{issue.id}` {issue.title}{itype}"
                )
            lines.append("")

        # By Feature summary
        by_feature = s.get("by_feature", {})
        if by_feature:
            lines.append("### Features")
            for slug, count in sorted(by_feature.items()):
                lines.append(f"- `{slug}`: {count} open")
            lines.append("")

        return "\n".join(lines)
    finally:
        conn.close()


def show_graph(feature_slug: str, *, root: Path | None = None) -> str:
    """Render ASCII dependency graph for a feature.

    Returns a text representation of the issue hierarchy and dependencies.
    """
    conn = _conn(root)
    try:
        issues = _st.list_issues_query(
            conn, feature_slug=feature_slug, limit=200
        )
        if not issues:
            return f"No issues found for feature '{feature_slug}'."

        # Build ID->Issue map
        issue_map = {i.id: i for i in issues}

        # Find parent-child relationships
        children: dict[str, list[str]] = {}
        has_parent: set[str] = set()
        blocking: dict[str, list[str]] = {}

        for issue in issues:
            deps = _st.get_dependencies(conn, issue.id)
            for dep in deps:
                if dep.dep_type == "parent-child":
                    children.setdefault(dep.depends_on_id, []).append(issue.id)
                    has_parent.add(issue.id)
                elif dep.dep_type == "blocks":
                    blocking.setdefault(dep.depends_on_id, []).append(issue.id)

        # Root issues: those without a parent (within this feature)
        roots = [i.id for i in issues if i.id not in has_parent]
        roots.sort()

        lines: list[str] = [f"## {feature_slug} Dependency Graph", ""]

        def _render(issue_id: str, indent: int = 0) -> None:
            issue = issue_map.get(issue_id)
            if not issue:
                return
            prefix = "  " * indent
            status_icon = {
                "open": " ",
                "in_progress": ">",
                "closed": "x",
            }.get(issue.status, "?")
            lines.append(
                f"{prefix}[{status_icon}] {issue.id} {issue.title}"
            )
            # Show blocking relationships
            for blocked in blocking.get(issue_id, []):
                if blocked in issue_map:
                    bi = issue_map[blocked]
                    lines.append(
                        f"{prefix}    -> blocks {blocked} {bi.title}"
                    )
            # Recurse into children
            for child_id in sorted(children.get(issue_id, [])):
                _render(child_id, indent + 1)

        for root_id in roots:
            _render(root_id)

        return "\n".join(lines)
    finally:
        conn.close()
