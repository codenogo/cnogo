# Project: cnogo — Universal Development Workflow Pack

> A zero-dependency workflow engine for Claude Code that provides 28+ slash commands, SQLite-backed memory, and Agent Teams support.

## Vision

cnogo gives any software project a structured development workflow out of the box. One `bash install.sh` command installs slash commands, planning docs, memory engine, and hooks into a target project. The goal is to make Claude Code sessions reproducible, auditable, and parallelizable across any tech stack.

## Constraints

| Constraint | Reason |
|------------|--------|
| Python stdlib only | Zero external dependencies — must work on any machine with Python 3.10+ |
| Bash install.sh distribution | No package manager dependency — `install.sh` is the single distribution mechanism |
| Stack-agnostic | Must work with Java, TypeScript, Python, Go, Rust, or any other stack |
| No runtime services | No daemons, servers, or background processes — everything runs inline |

## Architecture

```
install.sh
    │
    ├── .claude/commands/       28 slash command definitions (Markdown)
    ├── .claude/agents/         Team agent definitions (implementer, debugger)
    ├── .claude/skills/         Lazy-loaded domain expertise playbooks
    ├── .claude/settings.json   Hooks + permissions
    │
    ├── scripts/                Workflow Python scripts (stdlib only)
    │   └── memory/             SQLite memory engine package
    │
    ├── docs/planning/          Planning docs (PROJECT, ROADMAP, WORKFLOW.json)
    │   └── work/               Feature work, research, debug, reviews
    │
    └── docs/templates/         Install templates (*-TEMPLATE files)
```

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Scripts | Python 3.10+ (stdlib only) | workflow_validate.py, workflow_checks.py, workflow_detect.py, etc. |
| Memory | SQLite via Python sqlite3 | .cnogo/memory.db (runtime), .cnogo/issues.jsonl (git-tracked sync) |
| Commands | Markdown | 28 slash commands in .claude/commands/ |
| Installer | Bash | install.sh — single entry point |
| Hooks | Bash + Python | PreToolUse, PostToolUse, PreCommit, PostCommit |

## Patterns

### Code Organisation
- Scripts in `scripts/` — flat structure, `workflow_` prefix for top-level scripts
- Memory engine in `scripts/memory/` — Python package with `__init__.py` public API
- Commands in `.claude/commands/` — one Markdown file per command
- Feature work in `docs/planning/work/features/<slug>/` — CONTEXT, PLANs, SUMMARYs, REVIEWs

### Workflow Contracts
- Every planning artifact has a paired JSON contract (e.g., `CONTEXT.md` + `CONTEXT.json`)
- Contracts have `schemaVersion`, `feature` (slug), `timestamp` at minimum
- Validated by `python3 scripts/workflow_validate.py`

### Naming
- Feature slugs: `kebab-case` (e.g., `template-self-separation`)
- Plans: `NN-PLAN.md` + `NN-PLAN.json` (max 3 tasks per plan)
- Templates: `*-TEMPLATE.md` / `*-TEMPLATE.json` in `docs/templates/`

### Error Handling
- Scripts use stdlib exceptions — no custom exception hierarchy
- `workflow_validate.py` prints `PASS` or `FAIL` with details, exits 0 or 1
- Memory engine uses `ValueError` for invalid input, `RuntimeError` for state errors

## Non-Goals

Things explicitly out of scope:
- Not a package manager — does not manage project dependencies
- Not a CI system — provides `/verify-ci` artifacts but does not run CI pipelines
- Not a testing framework — delegates to project's own test suite
- Not a code generator — commands guide Claude, they don't generate application code

## Key Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| Python stdlib only | Ensures install works on any machine without pip install | 2026-01 |
| SQLite for memory | Built into Python stdlib, single-file DB, no server needed | 2026-02 |
| Markdown commands | Claude Code natively loads .claude/commands/*.md as slash commands | 2026-01 |
| install.sh distribution | Simplest possible install — no npm/pip/brew dependency | 2026-01 |
| Templates in docs/templates/ | Separates install templates from cnogo's own project docs | 2026-02 |

---
*Last updated: 2026-02-14*
