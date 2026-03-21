# Project: cnogo — Universal Development Workflow Pack

> A zero-dependency workflow engine for Claude Code that provides 28+ slash commands, SQLite-backed memory, durable Work Orders, and Agent Teams support.

## Vision

cnogo gives any software project a structured development workflow out of the box. One `bash install.sh` command installs slash commands, planning docs, memory engine, and hooks into a target project. The goal is to make Claude Code sessions reproducible, auditable, and parallelizable across any tech stack.

## Constraints

| Constraint | Reason |
|------------|--------|
| Python stdlib only | Zero external dependencies — must work on any machine with Python 3.10+ |
| Bash install.sh distribution | No package manager dependency — `install.sh` is the single distribution mechanism |
| Stack-agnostic | Must work with Java, TypeScript, Python, Go, Rust, or any other stack |
| No external service requirement | No external daemons or servers. Inline execution is the default; an optional local scheduler supervisor is allowed |
| Agent Teams requires Claude Code >= 2.1 with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | Experimental feature — pin to known-good version |

## Architecture

```
install.sh
    │
    ├── .claude/commands/       28 slash command definitions (Markdown)
    ├── .claude/agents/         Team agents plus shape scouts
    ├── .claude/skills/         Lazy-loaded domain expertise playbooks
    ├── .claude/settings.json   Hooks + permissions
    │
    ├── .cnogo/scripts/          Workflow Python scripts (stdlib only)
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
| Commands | Markdown | 30 slash commands in .claude/commands/ |
| Installer | Bash | install.sh — single entry point |
| Hooks | Bash + Python | PreToolUse, PostToolUse, PreCommit, PostCommit |

## Patterns

### Code Organisation
- Scripts in `.cnogo/scripts/` — flat structure, `workflow_` prefix for top-level scripts
- Memory engine in `.cnogo/scripts/memory/` — Python package with `__init__.py` public API
- Commands in `.claude/commands/` — one Markdown file per command
- Initiative shaping in `docs/planning/work/ideas/<slug>/` — persistent SHAPE workspace (legacy BRAINSTORM supported)
- Feature work in `docs/planning/work/features/<slug>/` — FEATURE stub, CONTEXT, PLANs, SUMMARYs, REVIEWs

### Workflow Contracts
- Every planning artifact has a paired JSON contract (e.g., `CONTEXT.md` + `CONTEXT.json`)
- Contracts have `schemaVersion`, `feature` (slug), `timestamp` at minimum
- For `schemaVersion >= 2` plans, tasks require `microSteps[]` + `tdd` contract (no minute-based time boxes)
- For `schemaVersion >= 3` plans, tasks also require `contextLinks[]` plus at least one explicit error-path scenario when TDD is required
- `/implement` is the canonical execution entrypoint; it may auto-route into `/team implement` when the dependency frontier exposes safe parallel work
- Delivery Runs are the durable plan-execution object; Work Orders are the feature-level rollup over plans, runs, review, ship, and attention state
- `profile` is the canonical delivery-policy contract; legacy `formula` remains a compatibility alias during migration
- The scheduler is built in and local: opportunistic ticks are default, and an optional local supervisor can run the same jobs on cadence
- Feature summaries should be generated from recorded execution evidence via `workflow_checks.py summarize`, not handwritten from scratch
- Review contracts use staged review structure (spec-compliance then code-quality) before ship
- Validated by `python3 .cnogo/scripts/workflow_validate.py`

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
| Pin Agent Teams to Claude Code >= 2.1 | Feature is experimental; version pinning prevents breakage | 2026-02 |

---
*Last updated: 2026-03-21*
