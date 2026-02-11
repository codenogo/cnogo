#!/usr/bin/env python3
"""
Render markdown artifacts from JSON contracts to reduce drift.

Supported:
- features/<feature>/<NN>-PLAN.json -> <NN>-PLAN.md (regenerates tasks section)
- features/<feature>/<NN>-SUMMARY.json -> <NN>-SUMMARY.md (regenerates tables)

This is intentionally simple and deterministic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from workflow_utils import load_json


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def render_plan(plan: dict[str, Any]) -> str:
    feature = plan.get("feature", "[feature]")
    pn = plan.get("planNumber", "NN")
    goal = plan.get("goal", "")
    tasks = plan.get("tasks", []) if isinstance(plan.get("tasks"), list) else []
    plan_verify = plan.get("planVerify", [])
    commit_msg = plan.get("commitMessage", "")

    lines: list[str] = []
    lines.append(f"# Plan {pn}: {goal or '[Short Title]'}")
    lines.append("")
    lines.append("## Goal")
    lines.append(goal or "[One sentence: what this plan delivers]")
    lines.append("")
    lines.append("## Tasks")
    lines.append("")
    for i, t in enumerate(tasks, start=1):
        if not isinstance(t, dict):
            continue
        name = t.get("name", f"Task {i}")
        files = t.get("files", [])
        verify = t.get("verify", [])
        action = t.get("action", "")
        cwd = t.get("cwd")
        lines.append(f"### Task {i}: {name}")
        if cwd:
            lines.append(f"**CWD:** `{cwd}`")
        if isinstance(files, list) and files:
            lines.append("**Files:** " + ", ".join(f"`{f}`" for f in files))
        else:
            lines.append("**Files:** `[add files]`")
        lines.append("**Action:**")
        lines.append(action or "[Specific instructions]")
        lines.append("")
        lines.append("**Verify:**")
        lines.append("```bash")
        if isinstance(verify, list) and verify:
            for v in verify:
                lines.append(str(v))
        else:
            lines.append("[Command to verify this task]")
        lines.append("```")
        lines.append("")
        lines.append("**Done when:** [Observable outcome]")
        lines.append("")

    lines.append("## Verification")
    lines.append("")
    lines.append("After all tasks:")
    lines.append("```bash")
    if isinstance(plan_verify, list) and plan_verify:
        for v in plan_verify:
            lines.append(str(v))
    else:
        lines.append("[Commands to verify the plan is complete]")
    lines.append("```")
    lines.append("")
    lines.append("## Commit Message")
    lines.append("```")
    lines.append(commit_msg or f"feat({feature}): [description]")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def render_summary(summary: dict[str, Any]) -> str:
    pn = summary.get("planNumber", "NN")
    outcome = summary.get("outcome", "complete")
    changes = summary.get("changes", [])
    verification = summary.get("verification", [])
    commit = summary.get("commit", {})

    lines: list[str] = []
    lines.append(f"# Plan {pn} Summary")
    lines.append("")
    lines.append("## Outcome")
    lines.append(f"{outcome}")
    lines.append("")
    lines.append("## Changes Made")
    lines.append("")
    lines.append("| File | Change |")
    lines.append("|------|--------|")
    if isinstance(changes, list) and changes:
        for c in changes:
            if isinstance(c, dict):
                lines.append(f"| `{c.get('file','')}` | {c.get('change','')} |")
    else:
        lines.append("| `path/to/file` | [what changed] |")
    lines.append("")
    lines.append("## Verification Results")
    lines.append("")
    if isinstance(verification, list) and verification:
        for v in verification:
            lines.append(f"- {v}")
    else:
        lines.append("- [verification results]")
    lines.append("")
    lines.append("## Commit")
    if isinstance(commit, dict):
        h = commit.get("hash", "")
        m = commit.get("message", "")
        lines.append(f"`{h}` - {m}".strip())
    else:
        lines.append("`abc123f` - [commit message]")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render markdown artifacts from JSON contracts.")
    parser.add_argument("json_file", help="Path to JSON contract file.")
    args = parser.parse_args()

    jf = Path(args.json_file)
    if not jf.exists():
        raise SystemExit(f"File not found: {jf}")
    data = load_json(jf)
    if not isinstance(data, dict):
        raise SystemExit("Contract must be a JSON object.")

    if jf.name.endswith("-PLAN.json"):
        md = jf.with_name(jf.name.replace(".json", ".md"))
        write(md, render_plan(data))
        print(f"✅ Rendered {md}")
        return 0
    if jf.name.endswith("-SUMMARY.json"):
        md = jf.with_name(jf.name.replace(".json", ".md"))
        write(md, render_summary(data))
        print(f"✅ Rendered {md}")
        return 0

    raise SystemExit("Unsupported contract type. Use *-PLAN.json or *-SUMMARY.json.")


if __name__ == "__main__":
    raise SystemExit(main())

