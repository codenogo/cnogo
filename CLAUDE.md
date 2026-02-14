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
docs/planning/STATE.md       # Current position and decisions
.cnogo/memory.db             # SQLite runtime (gitignored)
.cnogo/issues.jsonl          # Git-tracked sync format
```

## Conventions

- Feature slugs: `kebab-case` (e.g., `websocket-notifications`)
- Commits: `type(scope): description`
- Branches: `feature/description`, `fix/description`
- Python: stdlib only, no external deps
- Plans: max 3 tasks per plan, each with explicit `files` and `verify`

## Operating Principles

Apply these on every non-trivial task. Inspired by [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills).

1. **Think Before Coding** — surface confusion and tradeoffs; ask when ambiguous
2. **Simplicity First** — minimum code that solves the problem; no speculative abstractions
3. **Surgical Changes** — touch only what's needed; don't refactor unrelated areas
4. **Goal-Driven Execution** — define success criteria; verify with commands/tests; loop until proven

## Key Files

| File | Purpose |
|------|---------|
| `scripts/memory/` | Memory engine package (CRUD, deps, graph, bridge, sync) |
| `scripts/memory/bridge.py` | Translates plans to agent task descriptions |
| `.claude/settings.json` | Permissions, hooks, env vars |
| `docs/planning/WORKFLOW.json` | Workflow config (research mode, enforcement) |

## Memory Engine

Required for `/team` workflows. Initialize via `/init` or `python3 scripts/workflow_memory.py init`.

```bash
python3 scripts/workflow_memory.py show <id>     # Show issue details
python3 scripts/workflow_memory.py create "title" # Create an issue
python3 scripts/workflow_memory.py claim <id>     # Claim a task
python3 scripts/workflow_memory.py close <id>     # Close a task
```

```python
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create, ready, claim, close, prime, show
```

## Planning Docs

- Current state: `docs/planning/STATE.md`
- Project vision: `docs/planning/PROJECT.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Research: `docs/planning/work/research/`

## Security

- Never commit: secrets, keys, credentials, `.env` files
- Pre-commit hooks scan for secrets and dangerous commands
- Always validate user input at system boundaries
