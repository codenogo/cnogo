# CLAUDE.md

Agent instructions for cnogo. Claude reads this automatically.

## Project Overview

cnogo is a universal development workflow pack for Claude Code. It provides 28+ slash commands, a SQLite-backed memory engine for persistent task tracking, and Agent Teams support for parallel multi-agent execution. Python stdlib only — zero external dependencies.

## Quick Reference

```bash
python3 scripts/workflow_validate.py            # Validate workflow artifacts
python3 scripts/workflow_memory.py stats         # Memory engine statistics
python3 scripts/workflow_memory.py prime         # Token-efficient context summary
python3 scripts/workflow_memory.py ready         # Show unblocked tasks
```

## Code Organisation

```
scripts/memory/              # Memory engine (Python, stdlib only)
.claude/agents/              # Team teammates only (implementer, debugger)
.claude/skills/              # Lazy-loaded domain expertise
.claude/commands/            # Slash command definitions
docs/planning/               # Planning docs, feature work, research
.cnogo/memory.db             # SQLite runtime (gitignored)
.cnogo/issues.jsonl          # Git-tracked sync format
```

## Conventions

- Feature slugs: `kebab-case` (e.g., `websocket-notifications`)
- Commits: `type(scope): description`
- Branches: `feature/description`, `fix/description`
- Python: stdlib only, no external deps
- Plans: max 3 tasks per plan, each with explicit `files` and `verify`

## Key Files

| File | Purpose |
|------|---------|
| `scripts/memory/` | Memory engine package (CRUD, deps, graph, bridge, sync) |
| `scripts/memory/bridge.py` | Translates plans to agent task descriptions |
| `.claude/settings.json` | Permissions, hooks, env vars |
| `docs/planning/WORKFLOW.json` | Workflow config (research mode, enforcement) |
