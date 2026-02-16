# cnogo Workflow

Workflow engine documentation. Claude reads this automatically alongside your project's CLAUDE.md.

## Operating Principles

Apply these on every non-trivial task. Inspired by [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills).

1. **Think Before Coding** — surface confusion and tradeoffs; ask when ambiguous
2. **Simplicity First** — minimum code that solves the problem; no speculative abstractions
3. **Surgical Changes** — touch only what's needed; don't refactor unrelated areas
4. **Goal-Driven Execution** — define success criteria; verify with commands/tests; loop until proven
5. **Prefer Shared Utility Packages Over Hand-Rolled Helpers** — reuse shared helpers/packages before adding new utility implementations
6. **Don't Probe Data YOLO-Style** — avoid guess-and-check reads; use explicit schemas/contracts
7. **Validate Boundaries** — validate input/output at API, DB, filesystem, and network boundaries
8. **Typed SDKs** — prefer official typed SDKs/clients over ad-hoc HTTP calls when available

## Memory Engine

Structured task tracking (initialized at install via `install.sh`, or manually via `python3 scripts/workflow_memory.py init`):

```bash
# CLI access
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

Key files:
- `scripts/memory/` — Python package (stdlib only)
- `.cnogo/memory.db` — SQLite runtime (gitignored)
- `.cnogo/issues.jsonl` — Git-tracked sync format

## Planning Docs

- Current state: memory engine (`prime()` for context summary)
- Project vision: `docs/planning/PROJECT.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`
- Research: `docs/planning/work/research/`

## Skills Library

Reusable domain expertise, lazy-loaded by commands:
- `.claude/skills/` — code review, security scanning, performance analysis, API review, test writing, debug investigation, refactor safety, release readiness

## Security

- Never commit: secrets, keys, credentials, `.env` files
- Pre-commit hooks scan for secrets and dangerous commands
- Always validate user input at system boundaries
