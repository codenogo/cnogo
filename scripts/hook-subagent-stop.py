#!/usr/bin/env python3
"""
SubagentStop hook — auto-close memory issues when a subagent stops.

Reads SubagentStop hook input from stdin as JSON, scans the last assistant
message for memory IDs (cn-[a-z0-9]+(\.[0-9]+)*), and attempts to close
each one. Falls back to checking the worktree-session.json for any
unresolved worktree whose path matches the agent's cwd.

Must complete in < 3 seconds total. Always exits 0.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_MEMORY_ID_RE = re.compile(r"cn-[a-z0-9]+(?:\.[0-9]+)*")
_DONE_STATUSES = frozenset({"merged", "cleaned"})
_SESSION_FILE = ".cnogo/worktree-session.json"


def _close_memory_id(memory_id: str, scripts_dir: Path) -> None:
    """Attempt to close a memory issue by ID. Ignores errors."""
    try:
        subprocess.run(
            [
                "python3",
                str(scripts_dir / "workflow_memory.py"),
                "close",
                memory_id,
                "--reason",
                "completed",
                "--actor",
                "subagent-stop-hook",
            ],
            timeout=3,
            capture_output=True,
        )
        print(f"[hook-subagent-stop] closed memory id: {memory_id}", file=sys.stderr)
    except Exception as exc:
        print(
            f"[hook-subagent-stop] could not close {memory_id}: {exc}", file=sys.stderr
        )


def _fallback_session_close(agent_cwd: str, scripts_dir: Path) -> None:
    """Check worktree-session.json and close memory IDs for matching paths."""
    try:
        session_path = Path(agent_cwd) / _SESSION_FILE
        if not session_path.exists():
            return
        data = json.loads(session_path.read_text(encoding="utf-8"))
        worktrees = data.get("worktrees", [])
        for wt in worktrees:
            status = wt.get("status", "")
            memory_id = wt.get("memoryId", "")
            wt_path = wt.get("path", "")
            if status in _DONE_STATUSES or not memory_id:
                continue
            # Close if agent cwd matches this worktree path
            if wt_path and Path(agent_cwd).resolve() == Path(wt_path).resolve():
                print(
                    f"[hook-subagent-stop] fallback: closing {memory_id} for worktree {wt_path}",
                    file=sys.stderr,
                )
                _close_memory_id(memory_id, scripts_dir)
    except Exception as exc:
        print(f"[hook-subagent-stop] fallback error: {exc}", file=sys.stderr)


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload: dict = {}
        try:
            payload = json.loads(raw)
        except Exception:
            print(
                "[hook-subagent-stop] could not parse stdin as JSON", file=sys.stderr
            )

        last_msg: str = payload.get("last_assistant_message", "") or ""
        agent_cwd: str = payload.get("cwd", "") or ""

        # Locate scripts directory relative to this script's own location
        scripts_dir = Path(__file__).parent.resolve()

        # Step 1: scan last assistant message for memory IDs
        found_ids = _MEMORY_ID_RE.findall(last_msg)
        closed: set[str] = set()
        for memory_id in found_ids:
            if memory_id not in closed:
                _close_memory_id(memory_id, scripts_dir)
                closed.add(memory_id)

        # Step 2: fallback via worktree-session.json
        if agent_cwd:
            _fallback_session_close(agent_cwd, scripts_dir)

    except Exception as exc:
        print(f"[hook-subagent-stop] unexpected error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
