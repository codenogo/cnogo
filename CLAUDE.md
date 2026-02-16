# CLAUDE.md

Agent instructions for cnogo. Claude reads this automatically.

## Project Overview

cnogo is a universal development workflow pack for Claude Code. It provides 28+ slash commands, a SQLite-backed memory engine for persistent task tracking, and Agent Teams support for parallel multi-agent execution. Python stdlib only — zero external dependencies. Agent Teams requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` environment variable and Claude Code >= 2.1.

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

## Architecture Rules

### Do
- Follow the command template pattern (one `.md` per slash command in `.claude/commands/`)
- Use the memory API (`scripts/memory/`) for task state — not files
- Pair every planning artifact with a JSON contract (`CONTEXT.md` + `CONTEXT.json`)
- Verify with `python3 scripts/workflow_validate.py` before committing workflow artifacts
- Use `repo_root()` or relative paths — never hardcode absolute paths

### Don't
- Don't add external Python dependencies — stdlib only
- Don't bypass workflow contracts (every CONTEXT/PLAN/SUMMARY/REVIEW needs a JSON pair)
- Don't put cnogo's own project content in template files (`docs/templates/` is for installs)
- Don't exceed 3 tasks per plan
- Don't modify `.claude/settings.json` hooks without testing the hook scripts

## Testing

No test suite yet (tracked as v2.0 future work). Current verification:

```bash
python3 scripts/workflow_validate.py                    # Validate all workflow artifacts
python3 -m py_compile scripts/workflow_validate.py      # Syntax check
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import is_initialized, prime; from pathlib import Path; r=Path('.'); print(prime(root=r) if is_initialized(r) else 'Memory not initialized')"  # Memory engine smoke test
```

## Troubleshooting

### Memory not initialized
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import init; init(root=__import__('pathlib').Path('.'))"
```

### Workflow validation fails
Check for missing JSON contracts (every `.md` artifact needs a `.json` pair) and ensure feature slugs are kebab-case.

### install.sh target already exists
Use `bash install.sh -y /path/to/project` to auto-accept merge with existing directories.

---

## Planning Docs

- Project vision: `docs/planning/PROJECT.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`

## Memory Engine

Optional structured task tracking (initialize via `/init` or `python3 scripts/workflow_memory.py init`):

```bash
python3 scripts/workflow_memory.py ready          # Show unblocked tasks
python3 scripts/workflow_memory.py prime           # Token-efficient context summary
python3 scripts/workflow_memory.py stats           # Aggregate statistics
python3 scripts/workflow_memory.py create "title"  # Create an issue
python3 scripts/workflow_memory.py show <id>       # Show issue details
```

```python
# Python API access (from commands/scripts)
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create, ready, claim, close, prime
```

## Karpathy-Inspired Operating Principles

1. **Think Before Coding**: don't assume; surface confusion/tradeoffs; ask when ambiguous.
2. **Simplicity First**: minimum code that solves the problem; no speculative abstractions.
3. **Surgical Changes**: touch only what's needed; don't refactor unrelated areas.
4. **Goal-Driven Execution**: define success criteria; verify with commands/tests; loop until proven.
5. **Prefer Shared Utility Packages Over Hand-Rolled Helpers**: reuse shared helpers/packages before adding new utility implementations.
6. **Don't Probe Data YOLO-Style**: avoid guess-and-check reads; use explicit schemas/contracts.
7. **Validate Boundaries**: validate input/output at API, DB, filesystem, and network boundaries.
8. **Typed SDKs**: prefer official typed SDKs/clients over ad-hoc HTTP calls when available.
