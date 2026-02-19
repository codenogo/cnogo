#!/usr/bin/env python3
"""Bridge between cnogo memory engine and Claude Code Agent Teams.

Translates NN-PLAN.json tasks into agent-executable descriptions with
memory issue linkage. One-way bridge: memory -> TaskList direction only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import storage as _st
from .identity import generate_child_id as _child_id

_CNOGO_DIR = ".cnogo"
_DB_NAME = "memory.db"

# Memory IDs must match: cn-<base36>[.<digits>]*  (e.g., cn-a3f8, cn-a3f8.1.2)
_MEMORY_ID_RE = re.compile(r"^cn-[a-z0-9]+(\.\d+)*$")


def plan_to_task_descriptions(
    plan_json_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Read an NN-PLAN.json and generate task descriptions for agent teammates.

    For each task in the plan:
      - If ``memoryId`` is present, use it.
      - If missing, create a memory issue under the plan's ``memoryEpicId``.

    Returns a list of dicts with keys:
      name, description, memoryId, files, verify, blockedBy
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

        # Skip already-closed tasks (duplicate prevention on resume)
        if memory_id and _is_already_closed(root, memory_id):
            results.append({
                "name": task.get("name", f"Task {i + 1}"),
                "description": "",
                "memoryId": memory_id,
                "files": task.get("files", []),
                "verify": task.get("verify", []),
                "blockedBy": task.get("blockedBy", []),
                "skipped": True,
            })
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

        description = generate_implement_prompt(
            task_name=task.get("name", f"Task {i + 1}"),
            action=task.get("action", ""),
            files=files,
            verify=verify,
            memory_id=memory_id,
        )

        results.append({
            "name": task.get("name", f"Task {i + 1}"),
            "description": description,
            "memoryId": memory_id,
            "files": files,
            "verify": verify,
            "blockedBy": blocked_by,
            "skipped": False,
        })

    return results


def generate_implement_prompt(
    *,
    task_name: str,
    action: str,
    files: list[str],
    verify: list[str],
    memory_id: str = "",
) -> str:
    """Generate a minimal agent prompt for an implementer teammate.

    Uses ID-based context: agents fetch details via memory.show() at runtime
    instead of embedding CONTEXT.md content.
    """
    lines: list[str] = []

    lines.append(f"# Implement: {task_name}")
    lines.append("")
    lines.append(action)
    lines.append("")

    if files:
        lines.append("**Files (ONLY touch these):**")
        lines.append(", ".join(f"`{f}`" for f in files))
        lines.append("")

    if verify:
        lines.append("**Verify (must ALL pass):**")
        for v in verify:
            lines.append(f"- `{v}`")
        lines.append("")

    if memory_id:
        if not _MEMORY_ID_RE.match(memory_id):
            raise ValueError(
                f"Invalid memory_id format: {memory_id!r}. "
                "Expected pattern: cn-<base36>[.<digits>]*"
            )
        lines.append(f"**Memory:** `{memory_id}`")
        lines.append(f"- Claim: `python3 scripts/workflow_memory.py claim {memory_id} --actor implementer`")
        lines.append(f"- Close: `python3 scripts/workflow_memory.py close {memory_id} --reason completed`")
        lines.append(f"- Context: `python3 scripts/workflow_memory.py show {memory_id}`")
        lines.append(f"- History: `python3 scripts/workflow_memory.py history {memory_id}`")
        lines.append("- Checkpoint: `python3 scripts/workflow_memory.py checkpoint`")
        lines.append("")

    lines.append("**On failure:** read history, summarize the last error, fix, and retry.")
    lines.append("**Retry loop:** after each failed verify, run the history command before next attempt.")
    lines.append("After 2 failures, message the team lead.")
    if memory_id:
        lines.append("**If blocked:** do NOT close memory. Message the team lead.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def detect_file_conflicts(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Check for file overlaps that may produce merge conflicts (advisory).

    Returns a list of conflict dicts with keys:
      file, tasks (list of task indices that share the file), severity

    Severity is always "advisory" — worktree isolation prevents runtime
    interference, and the resolver agent handles merge conflicts at merge time.

    Empty list = no overlaps detected.
    """
    file_owners: dict[str, list[int]] = {}
    for i, task in enumerate(tasks):
        if task.get("skipped", False):
            continue
        for f in task.get("files", []):
            file_owners.setdefault(f, []).append(i)

    conflicts = []
    for file_path, owners in file_owners.items():
        if len(owners) > 1:
            conflicts.append({"file": file_path, "tasks": owners, "severity": "advisory"})
    return conflicts


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
    # Late import to avoid circular dependency
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
