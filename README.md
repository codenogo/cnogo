# cnogo

A zero-dependency workflow engine for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) that provides structured development lifecycle management with 29 slash commands, a SQLite-backed memory engine, and Agent Teams coordination.

## Overview

cnogo installs into any git repository and gives Claude Code a repeatable, artifact-driven development workflow. Work is organized into small batches (max 3 tasks per plan) with verification at every step.

**Key capabilities:**

- **29 slash commands** covering the full SDLC: discuss, plan, implement, verify, review, ship
- **Memory engine** — SQLite-backed issue tracking with JSONL sync for git persistence
- **Agent Teams** — multi-agent coordination with structured task descriptions (TaskDesc V2) and conflict detection
- **16 skills** — lazy-loaded domain expertise (code review, security scan, performance analysis, etc.)
- **Package-aware checks** — monorepo/polyglot support with per-package lint, test, and type checking
- **Token optimization** — command telemetry, artifact budgeting, and compact context management

**Requirements:** Python 3.10+ (stdlib only), Git, Claude Code. Optional: GitHub CLI (`gh`) for PR creation.

## Install

```bash
# Into a project
./install.sh /path/to/your/project

# First run (from the target project)
cd /path/to/your/project
claude
/cnogo-init
```

### Global install (recommended for multiple repos)

```bash
# Clone once
git clone git@github.com:codenogo/workflowy.git ~/.workflowy/workflowy

# Add shell helper (~/.zshrc or ~/.bashrc)
workflowy() { ~/.workflowy/workflowy/install.sh "$1"; }

# Install/upgrade any repo
workflowy /path/to/your/project
```

## Workflow

```
Feature work (non-trivial changes):
  /discuss → /plan → /implement → /review → /ship

Quick fixes (small, low-risk):
  /quick → /review → /ship

Bug triage:
  /bug → routes to /quick, /debug, or /discuss
```

### Feature lifecycle

**1. Discuss** — capture decisions before coding.

```bash
/discuss "feature display name"
```

Creates `feature/<slug>` branch, `CONTEXT.json`/`CONTEXT.md`, and a memory epic.

**2. Plan** — break work into small batches.

```bash
/plan <feature-slug>
```

Creates `NN-PLAN.json`/`NN-PLAN.md` with max 3 tasks, explicit file scopes, and verification commands.

**3. Implement** — execute one plan at a time.

```bash
/implement <feature-slug> 01
```

Runs each task with verification, writes `NN-SUMMARY.json`/`NN-SUMMARY.md`, creates an atomic commit.

For parallel execution with Agent Teams:

```bash
/team implement <feature-slug> 01
```

**4. Review** — quality gates.

```bash
/review
```

Runs automated package-aware checks, 7-axis manual scoring, writes `REVIEW.json`/`REVIEW.md`.

**5. Ship** — push and open PR.

```bash
/ship
```

## Commands

### Core workflow

| Command | Purpose |
|---------|---------|
| `/discuss <feature>` | Capture decisions before coding |
| `/plan <feature>` | Create implementation plans (max 3 tasks each) |
| `/implement <feature> <plan>` | Execute a plan with per-task verification |
| `/review` | Automated + manual quality gates |
| `/ship` | Commit, push, create PR |
| `/quick <task>` | Fast path for small fixes |

### Research and exploration

| Command | Purpose |
|---------|---------|
| `/research <topic>` | Deep research artifact (repo + optional web) |
| `/brainstorm <idea>` | Narrow ideas via Q&A before `/discuss` |
| `/context <topic>` | Build focused context pack for a feature/topic |

### Verification and enforcement

| Command | Purpose |
|---------|---------|
| `/verify <feature>` | Human acceptance testing |
| `/verify-ci <feature>` | Non-interactive verification (CI-friendly) |
| `/validate` | Enforce workflow contracts (schemas, slugs, task limits) |

### Debugging and recovery

| Command | Purpose |
|---------|---------|
| `/bug <description>` | Bug triage router (quick vs debug vs discuss) |
| `/debug <issue>` | Systematic debugging with state tracking |
| `/rollback` | Revert changes (last, commit-hash, or branch) |

### Session management

| Command | Purpose |
|---------|---------|
| `/status` | Current position, blockers, next steps |
| `/pause` | Create handoff for later resume |
| `/resume` | Restore from paused session |
| `/sync` | Coordinate across parallel sessions |
| `/close <feature>` | Post-merge cleanup (memory close + optional archive) |

### Release

| Command | Purpose |
|---------|---------|
| `/changelog` | Generate changelog from git history |
| `/release <version>` | Create release with notes and tag |

### Agents and teams

| Command | Purpose |
|---------|---------|
| `/team <action>` | Orchestrate Agent Teams (create, status, message, dismiss) |
| `/spawn <type> <task>` | Launch specialized subagents |
| `/background <task>` | Fire-and-forget long-running tasks |

### Other

| Command | Purpose |
|---------|---------|
| `/tdd <feature>` | Test-driven development flow |
| `/mcp` | Manage MCP connections |
| `/doctor` | Diagnose workflow health |
| `/cnogo-init` | First-run setup and stack detection |

## Memory engine

SQLite-backed issue tracking with git-portable JSONL sync. Tracks features, plans, tasks, and their lifecycle across context switches and compaction.

```bash
python3 scripts/workflow_memory.py prime           # Token-efficient context summary
python3 scripts/workflow_memory.py ready           # Show unblocked tasks
python3 scripts/workflow_memory.py stats           # Aggregate statistics
python3 scripts/workflow_memory.py create "title"  # Create an issue
python3 scripts/workflow_memory.py show <id>       # Show issue details
```

Key modules in `scripts/memory/`:

| Module | Purpose |
|--------|---------|
| `storage.py` | SQLite persistence layer |
| `bridge.py` | Plan JSON → TaskDesc V2 translation for agent execution |
| `worktree.py` | Git worktree session management for parallel agents |
| `reconcile_leader.py` | Bottom-up issue closure (task → plan → epic) |
| `sync.py` | SQLite ↔ JSONL bidirectional sync |
| `identity.py` | Hierarchical ID generation (`cn-<base36>[.N]*`) |
| `models.py` | Issue/metadata dataclasses |

## Agent Teams

Multi-agent coordination using structured TaskDesc V2 contracts. The bridge translates plan JSON into task descriptions with file scopes, verification commands, and conflict detection.

3 built-in agent definitions in `.claude/agents/`:

| Agent | Specialization |
|-------|---------------|
| `implementer` | Executes plan tasks with memory-backed claim/close cycle |
| `debugger` | Investigates errors with systematic root cause analysis |
| `resolver` | Resolves git merge conflicts using task context |

Safety guarantees:
- Workers call `report-done` only — leaders handle closure
- File conflict detection before spawning parallel agents
- Bottom-up reconciliation: task → plan → epic

## Skills

16 lazy-loaded skill files in `.claude/skills/` provide domain expertise for review, security, and workflow integrity:

`code-review` · `security-scan` · `perf-analysis` · `api-review` · `test-writing` · `debug-investigation` · `refactor-safety` · `release-readiness` · `performance-review` · `artifact-token-budgeting` · `boundary-and-sdk-enforcement` · `changed-scope-verification` · `feature-lifecycle-closure` · `memory-sync-reconciliation` · `workflow-contract-integrity` · `worktree-merge-recovery`

## Project structure

```
your-project/
├── .claude/
│   ├── settings.json          # Permissions + hooks
│   ├── commands/              # 29 slash commands
│   ├── agents/                # 3 agent definitions
│   └── skills/                # 16 domain expertise skills
│
├── .cnogo/
│   ├── memory.db              # SQLite runtime (gitignored)
│   └── issues.jsonl           # Git-tracked sync format
│
├── scripts/
│   ├── memory/                # Memory engine package (stdlib only)
│   ├── workflow_checks.py     # Package-aware review/verify + token telemetry
│   ├── workflow_validate.py   # Contract + freshness + budget validation
│   ├── workflow_detect.py     # Stack/package auto-detection
│   ├── workflow_render.py     # JSON contract → Markdown renderer
│   ├── workflow_hooks.py      # Post-edit formatting + pre-bash optimization
│   ├── workflow_memory.py     # Memory engine CLI
│   └── hook-*.py/.sh          # Git/Claude hooks
│
├── docs/planning/
│   ├── PROJECT.md             # Vision, constraints, architecture
│   ├── ROADMAP.md             # Phases and progress
│   ├── WORKFLOW.json          # Enforcement + performance config
│   └── work/
│       ├── features/          # Feature artifacts (CONTEXT/PLAN/SUMMARY/REVIEW)
│       ├── quick/             # Quick fix artifacts
│       ├── research/          # Research artifacts
│       └── review/            # Standalone review reports
│
├── .github/
│   ├── CODEOWNERS
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/workflow-validate.yml
│
├── tests/                     # Unit tests
├── CLAUDE.md                  # Agent instructions
└── CHANGELOG.md               # Release history
```

## Artifact contracts

All workflow artifacts use paired JSON + Markdown files. JSON is the source of truth for automation; Markdown is the human-readable summary.

Standard fields across all contracts: `schemaVersion`, `feature`, `timestamp`.

```bash
# Render markdown from JSON contract
python3 scripts/workflow_render.py docs/planning/work/features/<slug>/01-PLAN.json

# Validate all contracts
python3 scripts/workflow_validate.py
```

## Monorepo support

Auto-detect packages and configure per-package checks:

```bash
python3 scripts/workflow_detect.py --write-workflow
```

This populates `docs/planning/WORKFLOW.json` with `packages[]`, enabling scoped lint/test/typecheck in `/review` and `/verify-ci`.

## CI

```yaml
# .github/workflows/workflow-validate.yml (included)
- run: python3 scripts/workflow_validate.py
- run: python3 scripts/workflow_checks.py review  # if packages configured
```

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `hook-dangerous-cmd.sh` | PreToolUse (Bash) | Block destructive commands |
| `hook-sensitive-file.sh` | PreToolUse (Read) | Gate access to secrets/credentials |
| `hook-pre-commit-secrets.sh` | PreToolUse (Bash) | Scan staged files for secrets on commit |
| `hook-subagent-stop.py` | PostToolUse (SubAgentStop) | Parse TASK_DONE footer, call report-done |
| `hook-pre-compact.py` | PreToolUse (Compact) | Checkpoint memory before context compaction |
| `hook-commit-confirm.sh` | PostToolUse (Bash) | Confirm commit with hash and message |
| `workflow_hooks.py` | PostToolUse (Edit/Write) | Auto-format edited files |

## Customization

**Add project-specific commands:**

```bash
# Create .claude/commands/your-command.md
# Use $ARGUMENTS for user input
```

**Configure enforcement** in `docs/planning/WORKFLOW.json`:

```json
{
  "enforcement": {
    "monorepoVerifyScope": "warn",
    "operatingPrinciples": "warn"
  }
}
```

**Add custom agents** by creating `.claude/agents/your-agent.md` with YAML frontmatter.

## Principles

1. **Fresh context per plan** — max 3 tasks per plan prevents context degradation
2. **Atomic commits** — one commit per plan, git bisect works, reverts are clean
3. **Discuss before plan** — capture decisions upfront, avoid rework
4. **Verify before ship** — task-level and plan-level verification gates
5. **State survives sessions** — memory engine persists across context switches
6. **Security by default** — secret scanning, dangerous command blocking, sensitive file gating

## Credits

- [Boris Cherny](https://blog.borischerny.com/) — parallel session workflow, fresh context pattern
- [GSD](https://github.com/gsd-framework) — context engineering, discuss → plan → execute → verify cycle

## License

MIT
