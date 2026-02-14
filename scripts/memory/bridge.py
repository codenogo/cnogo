#!/usr/bin/env python3
"""Bridge between cnogo memory engine and Claude Code Agent Teams.

Translates NN-PLAN.json tasks into agent-executable descriptions with
memory issue linkage. One-way bridge: memory -> TaskList direction only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import storage as _st
from .identity import generate_child_id as _child_id

_CNOGO_DIR = ".cnogo"
_DB_NAME = "memory.db"


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

    # Load feature context snippet (first 30 lines of CONTEXT.md)
    context_snippet = _load_context_snippet(plan_json_path.parent, feature)

    tasks = plan.get("tasks", [])
    results: list[dict[str, Any]] = []

    for i, task in enumerate(tasks):
        memory_id = task.get("memoryId", "")

        # Ensure memory issue exists
        if not memory_id and epic_id:
            memory_id = _ensure_memory_issue(
                root, epic_id, task, feature, plan_number
            )

        files = task.get("files", [])
        verify = task.get("verify", [])
        blocked_by = task.get("blockedBy", [])

        description = generate_implement_prompt(
            task_name=task.get("name", f"Task {i + 1}"),
            action=task.get("action", ""),
            files=files,
            verify=verify,
            memory_id=memory_id,
            context_snippet=context_snippet,
            feature=feature,
            plan_number=plan_number,
        )

        results.append({
            "name": task.get("name", f"Task {i + 1}"),
            "description": description,
            "memoryId": memory_id,
            "files": files,
            "verify": verify,
            "blockedBy": blocked_by,
        })

    return results


def generate_implement_prompt(
    *,
    task_name: str,
    action: str,
    files: list[str],
    verify: list[str],
    memory_id: str = "",
    context_snippet: str = "",
    feature: str = "",
    plan_number: str = "",
) -> str:
    """Generate the full agent prompt for an implementer teammate.

    Includes: context, action, file list, verify commands, memory
    claim/close instructions, and failure protocol.
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Implement: {task_name}")
    lines.append("")

    # Feature context
    if context_snippet:
        lines.append("## Feature Context")
        lines.append(context_snippet)
        lines.append("")

    # Action
    lines.append("## Action")
    lines.append(action)
    lines.append("")

    # File boundaries
    if files:
        lines.append("## Files (ONLY touch these)")
        for f in files:
            lines.append(f"- `{f}`")
        lines.append("")

    # Verification
    if verify:
        lines.append("## Verify (must ALL pass)")
        for v in verify:
            lines.append(f"```bash\n{v}\n```")
        lines.append("")

    # Memory instructions
    if memory_id:
        lines.append("## Memory Integration")
        lines.append("")
        lines.append("Before starting, claim this task:")
        lines.append("```bash")
        lines.append(f'python3 -c "')
        lines.append("import sys; sys.path.insert(0, '.')")
        lines.append("from scripts.memory import claim")
        lines.append("from pathlib import Path")
        lines.append(
            f"claim('{memory_id}', actor='implementer', root=Path('.'))"
        )
        lines.append('"')
        lines.append("```")
        lines.append("")
        lines.append("After ALL verify commands pass, close the task:")
        lines.append("```bash")
        lines.append(f'python3 -c "')
        lines.append("import sys; sys.path.insert(0, '.')")
        lines.append("from scripts.memory import close")
        lines.append("from pathlib import Path")
        lines.append(
            f"close('{memory_id}', reason='completed', root=Path('.'))"
        )
        lines.append('"')
        lines.append("```")
        lines.append("")

    # Failure protocol
    lines.append("## Failure Protocol")
    lines.append("1. If a verify command fails, diagnose and fix the issue")
    lines.append("2. Re-run the verify command")
    lines.append(
        "3. If still failing after 2 attempts, notify the team leader"
    )
    if memory_id:
        lines.append(
            "4. Update memory with failure details:"
        )
        lines.append("```bash")
        lines.append(f'python3 -c "')
        lines.append("import sys; sys.path.insert(0, '.')")
        lines.append("from scripts.memory import update")
        lines.append("from pathlib import Path")
        lines.append(
            f"update('{memory_id}', "
            "comment='Failed: <describe the issue>', root=Path('.'))"
        )
        lines.append('"')
        lines.append("```")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_context_snippet(feature_dir: Path, feature: str) -> str:
    """Load first 30 lines of CONTEXT.md for agent context injection."""
    context_path = feature_dir / "CONTEXT.md"
    if not context_path.exists():
        return ""
    try:
        text = context_path.read_text(encoding="utf-8")
        lines = text.splitlines()[:30]
        return "\n".join(lines)
    except OSError:
        return ""


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
