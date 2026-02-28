# CLAUDE.md

Compact project instructions for cnogo.

Full workflow policy lives in `.claude/CLAUDE.md`. Keep this file short to reduce baseline context load.

## Quick Start

```bash
python3 .cnogo/scripts/workflow_memory.py prime
python3 .cnogo/scripts/workflow_memory.py checkpoint
python3 .cnogo/scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_checks.py discover --since-days 30
```

## Must-Hold Rules

- Python code is stdlib-only.
- Planning artifacts require JSON contracts (`CONTEXT/PLAN/SUMMARY/REVIEW`).
- Plans are small-batch (max 3 tasks per plan).
- Run `python3 .cnogo/scripts/workflow_validate.py` before shipping workflow changes.
- Use memory engine APIs (`.cnogo/scripts/memory/`) instead of ad-hoc state files.

## Structure

- `.cnogo/scripts/memory/` memory engine (SQLite + JSONL sync)
- `.cnogo/scripts/workflow_checks.py` package-aware review/verify + token telemetry/discover
- `.cnogo/scripts/workflow_validate.py` workflow contract + freshness + budget validation
- `.cnogo/scripts/workflow_hooks.py` post-edit formatting and pre-bash optimization telemetry
- `.claude/commands/` slash command artifacts
- `.claude/skills/` reusable review/verification skills
- `docs/planning/WORKFLOW.json` runtime policy knobs

## Operating Principles

Use this priority order:
1. Think Before Coding
2. Simplicity First
3. Surgical Changes
4. Goal-Driven Execution
5. Prefer shared utilities over hand-rolled helpers
6. Don’t probe data YOLO-style
7. Validate boundaries
8. Typed SDKs
