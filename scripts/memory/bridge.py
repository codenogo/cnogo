#!/usr/bin/env python3
"""Bridge between cnogo memory engine and Claude Code Agent Teams.

Translates NN-PLAN.json tasks into structured TaskDesc V2 objects with
memory issue linkage. One-way bridge: memory -> TaskList direction only.

V2 changes from V1:
  - TaskDesc is structured (no baked markdown 'description' field)
  - 'action' is a first-class field
  - 'file_scope' replaces flat 'files' list (adds 'forbidden')
  - 'commands' object groups CLI commands
  - generate_implement_prompt() is a pure renderer (called at spawn-time only)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from . import storage as _st
from .identity import generate_child_id as _child_id

_CNOGO_DIR = ".cnogo"
_DB_NAME = "memory.db"

TASK_DESC_SCHEMA_VERSION = 2

# Memory IDs must match: cn-<base36>[.<digits>]*  (e.g., cn-a3f8, cn-a3f8.1.2)
_MEMORY_ID_RE = re.compile(r"^cn-[a-z0-9]+(\.\d+)*$")


def plan_to_task_descriptions(
    plan_json_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Read an NN-PLAN.json and generate TaskDesc V2 objects.

    For each task in the plan:
      - If ``memoryId`` is present, use it.
      - If missing, create a memory issue under the plan's ``memoryEpicId``.

    Returns a list of TaskDesc V2 dicts with keys:
      task_id, plan_task_index, title, action, file_scope, commands,
      completion_footer, blockedBy, skipped
    """
    text = plan_json_path.read_text(encoding="utf-8")
    plan = json.loads(text)

    feature = plan.get("feature", "")
    plan_number = plan.get("planNumber", "")
    epic_id = plan.get("memoryEpicId", "")

    tasks = plan.get("tasks", [])
    task_count = len(tasks)
    results: list[dict[str, Any]] = []

    for i, task in enumerate(tasks):
        memory_id = task.get("memoryId", "")

        # Ensure memory issue exists
        if not memory_id and epic_id:
            memory_id = _ensure_memory_issue(
                root, epic_id, task, feature, plan_number
            )

        title = task.get("name", f"Task {i + 1}")

        # Skip already-closed tasks (duplicate prevention on resume)
        if memory_id and _is_already_closed(root, memory_id):
            results.append(_make_skipped_desc(i, title, memory_id, task))
            continue

        files = task.get("files", [])
        verify = task.get("verify", [])
        blocked_by = task.get("blockedBy", [])

        # Validate blockedBy indices are in range and don't self-reference
        for idx in blocked_by:
            if not isinstance(idx, int) or idx < 0 or idx >= task_count:
                raise ValueError(
                    f"Task {i} has invalid blockedBy index {idx} "
                    f"(valid range: 0-{task_count - 1})"
                )
            if idx == i:
                raise ValueError(
                    f"Task {i} has self-referencing blockedBy index {idx}"
                )

        # Build commands object — only non-derivable commands persisted.
        # claim/report_done/context are derived from task_id at render time.
        commands: dict[str, Any] = {"verify": verify}

        # Build completion footer
        completion_footer = f"TASK_DONE: [{memory_id}]" if memory_id else ""

        results.append({
            "task_id": memory_id,
            "plan_task_index": i,
            "title": title,
            "action": task.get("action", ""),
            "file_scope": {
                "paths": files,
                "forbidden": [],
            },
            "commands": commands,
            "completion_footer": completion_footer,
            "blockedBy": blocked_by,
            "skipped": False,
        })

    return results


def generate_implement_prompt(taskdesc: dict[str, Any]) -> str:
    """Render a TaskDesc V2 dict into a markdown agent prompt.

    Pure renderer — called at spawn-time only by team flow.
    Serial flow uses V2 structured fields directly and never calls this.
    """
    title = taskdesc.get("title", "Unknown task")
    action = taskdesc.get("action", "")
    file_scope = taskdesc.get("file_scope", {})
    paths = file_scope.get("paths", [])
    forbidden = file_scope.get("forbidden", [])
    commands = taskdesc.get("commands", {})
    verify = commands.get("verify", [])
    task_id = taskdesc.get("task_id", "")
    completion_footer = taskdesc.get("completion_footer", "")

    lines: list[str] = []

    lines.append(f"# Implement: {title}")
    lines.append("")
    lines.append(action)
    lines.append("")

    if paths:
        lines.append("**Files (ONLY touch these):**")
        lines.append(", ".join(f"`{f}`" for f in paths))
        lines.append("")

    if forbidden:
        lines.append("**Forbidden (NEVER touch these):**")
        lines.append(", ".join(f"`{f}`" for f in forbidden))
        lines.append("")

    if verify:
        lines.append("**Verify (must ALL pass):**")
        for v in verify:
            lines.append(f"- `{v}`")
        lines.append("")

    if task_id:
        if not _MEMORY_ID_RE.match(task_id):
            raise ValueError(
                f"Invalid task_id format: {task_id!r}. "
                "Expected pattern: cn-<base36>[.<digits>]*"
            )
        lines.append(f"**Memory:** `{task_id}`")
        # Derive claim/report_done/context from task_id (not persisted)
        lines.append(
            f"- Claim: `python3 scripts/workflow_memory.py claim {task_id} --actor implementer`"
        )
        lines.append(
            f"- Report done: `python3 scripts/workflow_memory.py report-done {task_id} --actor implementer`"
        )
        lines.append(
            f"- Context: `python3 scripts/workflow_memory.py show {task_id}`"
        )
        lines.append(f"- History: `python3 scripts/workflow_memory.py history {task_id}`")
        lines.append("- Checkpoint: `python3 scripts/workflow_memory.py checkpoint`")
        lines.append("")

    lines.append("**On failure:** read history, summarize the last error, fix, and retry.")
    lines.append("**Retry loop:** after each failed verify, run the history command before next attempt.")
    lines.append("After 2 failures, message the team lead.")
    if task_id:
        lines.append("**If blocked:** do NOT report done. Message the team lead.")
        lines.append("**NEVER close issues. Only report done. The leader handles closure.**")
        lines.append("")
        lines.append(
            f"**On completion:** Add this footer as the LAST line of your final message:\n"
            f"`{completion_footer}`"
        )
    lines.append("")

    return "\n".join(lines)


def detect_file_conflicts(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check for file overlaps that may produce merge conflicts (advisory).

    Reads file_scope.paths from TaskDesc V2 dicts. Also warns if any task's
    paths appear in another task's file_scope.forbidden list.

    Returns a list of conflict dicts with keys:
      file, tasks, severity ("advisory" or "forbidden_overlap")

    Empty list = no overlaps detected.
    """
    file_owners: dict[str, list[int]] = {}
    forbidden_map: dict[str, list[int]] = {}

    for i, task in enumerate(tasks):
        if task.get("skipped", False):
            continue
        file_scope = task.get("file_scope", {})
        for f in file_scope.get("paths", []):
            file_owners.setdefault(f, []).append(i)
        for f in file_scope.get("forbidden", []):
            forbidden_map.setdefault(f, []).append(i)

    conflicts = []

    # Path overlaps (same file touched by multiple tasks)
    for file_path, owners in file_owners.items():
        if len(owners) > 1:
            conflicts.append({
                "file": file_path,
                "tasks": owners,
                "severity": "advisory",
            })

    # Forbidden overlaps (a task touches a file another task forbids)
    for file_path, forbidders in forbidden_map.items():
        if file_path in file_owners:
            touchers = file_owners[file_path]
            # Only flag if different tasks are involved
            overlap = [t for t in touchers if t not in forbidders]
            if overlap:
                conflicts.append({
                    "file": file_path,
                    "tasks": overlap,
                    "forbidden_by": forbidders,
                    "severity": "forbidden_overlap",
                })

    return conflicts


def generate_run_id(feature: str) -> str:
    """Generate a unique run ID for a team execution session."""
    return f"{feature}-{int(time.time())}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_skipped_desc(
    index: int,
    title: str,
    memory_id: str,
    task: dict[str, Any],
) -> dict[str, Any]:
    """Build a skipped TaskDesc V2 dict."""
    return {
        "task_id": memory_id,
        "plan_task_index": index,
        "title": title,
        "action": "",
        "file_scope": {
            "paths": task.get("files", []),
            "forbidden": [],
        },
        "commands": {"verify": task.get("verify", [])},
        "completion_footer": "",
        "blockedBy": task.get("blockedBy", []),
        "skipped": True,
    }


def _is_already_closed(root: Path, memory_id: str) -> bool:
    """Check if a memory issue is already closed (for duplicate prevention)."""
    from . import is_initialized, show

    if not is_initialized(root):
        return False
    issue = show(memory_id, root=root)
    return issue is not None and issue.status == "closed"


def _ensure_memory_issue(
    root: Path,
    epic_id: str,
    task: dict[str, Any],
    feature: str,
    plan_number: str,
) -> str:
    """Create a memory issue for a plan task if it doesn't already exist.

    Returns the memory issue ID.
    """
    from . import create, is_initialized

    if not is_initialized(root):
        return ""

    issue = create(
        task.get("name", "Unnamed task"),
        parent=epic_id,
        feature_slug=feature,
        plan_number=plan_number,
        metadata={
            "files": task.get("files", []),
            "verify": task.get("verify", []),
        },
        root=root,
    )
    return issue.id
