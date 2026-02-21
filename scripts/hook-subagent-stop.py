#!/usr/bin/env python3
"""
SubagentStop hook — report-done for completed tasks (Contract 06).

Reads SubagentStop hook input from stdin as JSON, looks for a structured
TASK_DONE footer in the last assistant message, and calls report-done
for each listed ID. Workers NEVER close issues — only report done.

Must complete in < 3 seconds total. Always exits 0.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_TASK_DONE_RE = re.compile(r"TASK_DONE:\s*\[([^\]]+)\]")


def _report_done(memory_id: str, scripts_dir: Path) -> None:
    """Call report-done for a memory issue. Ignores errors."""
    try:
        subprocess.run(
            [
                "python3",
                str(scripts_dir / "workflow_memory.py"),
                "report-done",
                memory_id,
                "--actor",
                "subagent-stop-hook",
            ],
            timeout=3,
            capture_output=True,
        )
        print(f"[hook-subagent-stop] reported done: {memory_id}", file=sys.stderr)
    except Exception as exc:
        print(
            f"[hook-subagent-stop] could not report-done {memory_id}: {exc}",
            file=sys.stderr,
        )


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

        # Locate scripts directory relative to this script's own location
        scripts_dir = Path(__file__).parent.resolve()

        # Look for structured TASK_DONE footer
        match = _TASK_DONE_RE.search(last_msg)
        if not match:
            print("[hook-subagent-stop] no TASK_DONE footer found", file=sys.stderr)
            return 0

        # Parse comma-separated IDs
        ids_str = match.group(1)
        reported: set[str] = set()
        for raw_id in ids_str.split(","):
            memory_id = raw_id.strip()
            if memory_id and memory_id not in reported:
                _report_done(memory_id, scripts_dir)
                reported.add(memory_id)

    except Exception as exc:
        print(f"[hook-subagent-stop] unexpected error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
