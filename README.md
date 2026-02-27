# cnogo — Development Workflow Engine

An artifact-driven development workflow for Claude Code. Small-batch planning, structured memory, automated verification, and multi-agent coordination — all stdlib Python, no external dependencies.

## What It Does

cnogo turns Claude into a structured SDLC copilot by enforcing:

- **Artifact-driven work** — every decision, plan, and review produces JSON contracts + markdown
- **Small-batch execution** — max 3 tasks per plan, fresh context per plan
- **TDD as a core principle** — test-first is default for code tasks; `/tdd` is deep mode
- **Automated verification** — task-level checks, review gates, CI validation
- **Persistent memory** — SQLite-backed task tracking that survives context compaction
- **Multi-agent coordination** — Agent Teams with deterministic task assignment

## Quick Start

```bash
# Install into a project
./install.sh /path/to/your/project

# Optional: write a cnogo file manifest for clear ownership boundaries
./install.sh --manifest /path/to/your/project

# First run
cd /path/to/your/project && claude
/cnogo-init

# Check status
/status
```

### Prerequisites

- **Claude Code** (`claude`)
- **Python 3** (stdlib only — no pip installs)
- **Git**
- **GitHub CLI** (`gh`) — optional, used by `/ship`

## The Workflow

### Feature Work (non-trivial changes)

```
/discuss → /plan → /implement → /verify → /review → /ship
```

| Phase | Command | What happens |
|-------|---------|-------------|
| Decisions | `/discuss "feature name"` | Creates `feature/<slug>` branch, `CONTEXT.json` + `CONTEXT.md`, memory epic |
| Research | `/research "topic"` | Deep research artifact (`RESEARCH.json` + `RESEARCH.md`) — repo + optional web sources |
| Planning | `/plan <feature-slug>` | Creates `NN-PLAN.json` + `NN-PLAN.md` (max 3 tasks per plan) |
| Execution | `/implement <feature-slug> NN` | Executes plan tasks, writes `NN-SUMMARY.json` + `NN-SUMMARY.md`, closes memory tasks |
| Verification | `/verify <feature-slug>` | Human acceptance testing (`VERIFICATION.json` + `VERIFICATION.md`) |
| CI Verify | `/verify-ci <feature-slug>` | Non-interactive verification (CI-friendly) |
| Review | `/review` | Two-stage gate: spec compliance first, then code quality + scoring rubric |
| Ship | `/ship` | Commit, push, create PR via `gh`, requires `ship-ready` staged-review freshness gate |

### Quick Fixes (small changes)

```
/quick "description" → /review → /ship
```

Creates `fix/<slug>` branch, `PLAN.json`, implements, writes `SUMMARY.json`, commits.

### Bug Triage

```
/bug "description"
```

Routes to `/quick`, `/debug`, or `/discuss` based on complexity.

### Post-Merge Cleanup

```
/close <feature-slug>
```

## Memory Engine

SQLite-backed task tracking with JSONL git-sync. Persists across context compaction.

```bash
python3 scripts/workflow_memory.py prime           # Token-efficient context summary
python3 scripts/workflow_memory.py ready           # Show unblocked tasks
python3 scripts/workflow_memory.py stats           # Aggregate statistics
python3 scripts/workflow_memory.py create "title"  # Create an issue
python3 scripts/workflow_memory.py show <id>       # Show issue details
python3 scripts/workflow_memory.py checkpoint      # Snapshot current state
python3 scripts/workflow_memory.py stalled --feature <slug> --json
python3 scripts/workflow_memory.py takeover <id> --to <actor> --reason "stalled" --actor leader
python3 scripts/workflow_memory.py release <id> --actor leader
```

`SubagentStop` hook is observer-only: it validates `TASK_EVIDENCE`/`TASK_DONE` format and never mutates memory state.

### Memory Modules (13 files)

| Module | Purpose |
|--------|---------|
| `storage.py` | SQLite CRUD — the domain truth store |
| `bridge.py` | Translates memory objects into executable agent tasks (TaskDesc V2) |
| `sync.py` | JSONL import/export for git-tracked state |
| `worktree.py` | Git worktree isolation for parallel agent work |
| `reconcile.py` | Post-compaction orphan recovery |
| `reconcile_leader.py` | Leader-side team reconciliation |
| `identity.py` | Agent identity and run ID generation |
| `models.py` | Data models and schemas |
| `graph.py` | Dependency graph for task ordering |
| `context.py` | Context loading and summarization |
| `costs.py` | Token cost tracking |
| `watchdog.py` | Stale task detection |

Runtime DB: `.cnogo/memory.db` (gitignored). Sync format: `.cnogo/issues.jsonl` (git-tracked).

## Agent Teams

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (enabled by default).

Multi-agent coordination with shared task lists, direct messaging, and worktree isolation.

### Agents (3)

| Agent | Purpose |
|-------|---------|
| `debugger` | Root cause analysis and systematic debugging |
| `implementer` | Plan task execution with memory claim/report-done lifecycle |
| `resolver` | Merge conflict resolution |

### Team Commands

```bash
/team create <description>    # Create a team with task list
/team status                  # Check team progress
/team message <agent> <msg>   # Send guidance to a teammate
/team dismiss                 # Shut down the team
```

`bridge.py` handles plan → task translation, file conflict detection, and deterministic command derivation from task IDs.

## Commands (29)

### Core Workflow

| Command | Purpose |
|---------|---------|
| `/discuss <feature>` | Capture decisions before coding |
| `/research <topic>` | Deep research artifact |
| `/brainstorm <idea>` | Narrow ideas via Q&A before `/discuss` |
| `/plan <feature>` | Create implementation tasks (max 3 per plan) |
| `/implement <feature> <plan>` | Execute a plan with per-task verification |
| `/verify <feature>` | User acceptance testing |
| `/verify-ci <feature>` | Non-interactive CI-friendly verification |
| `/review` | Quality gates (automated checks + 14-point rubric) |
| `/ship` | Commit, push, create PR |
| `/validate` | Enforce workflow contracts |

### Fast Path

| Command | Purpose |
|---------|---------|
| `/quick <task>` | Small fixes without full ceremony |
| `/tdd <feature>` | Deep-mode test-driven development flow (TDD is still core outside this command) |

### Session Management

| Command | Purpose |
|---------|---------|
| `/status` | Current position, blockers, next steps |
| `/pause` | Create handoff for later resume |
| `/resume` | Restore from paused session |
| `/sync` | Coordinate across parallel sessions |
| `/context <feature>` | Load relevant files for a feature |

### Debugging and Recovery

| Command | Purpose |
|---------|---------|
| `/debug <issue>` | Systematic debugging with state tracking |
| `/bug <description>` | Bug triage router (quick vs debug vs discuss) |
| `/rollback` | Revert changes (last, commit-hash, or branch) |

### Release

| Command | Purpose |
|---------|---------|
| `/changelog` | Generate changelog from git history |
| `/release <version>` | Create release with notes and tag |

### Setup and Lifecycle

| Command | Purpose |
|---------|---------|
| `/cnogo-init` | Initialize workflow in a project (stack detection, templates) |
| `/close <feature>` | Post-merge cleanup (memory close + optional archive) |

### Agents and Automation

| Command | Purpose |
|---------|---------|
| `/background <task>` | Fire-and-forget long-running tasks |
| `/spawn <type> <task>` | Launch specialized subagents |
| `/team <action>` | Orchestrate Agent Teams |
| `/mcp` | Manage Model Context Protocol connections |
| `/doctor` | Diagnose workflow health issues |

## Skills (16)

Reusable domain expertise, lazy-loaded by commands from `.claude/skills/`:

| Skill | Purpose |
|-------|---------|
| `code-review` | Code quality and best-practice analysis |
| `security-scan` | Vulnerability auditing (OWASP, secrets, auth) |
| `perf-analysis` | Performance bottleneck analysis |
| `api-review` | API design review (REST, contracts) |
| `test-writing` | Test generation (unit, integration, edge cases) |
| `debug-investigation` | Root cause analysis |
| `refactor-safety` | Safe refactoring verification |
| `release-readiness` | Pre-release checklist |
| `performance-review` | 7-axis scoring rubric (final review gate) |
| `workflow-contract-integrity` | Planning artifact correctness |
| `artifact-token-budgeting` | Token budget enforcement for artifacts |
| `boundary-and-sdk-enforcement` | API boundary and SDK usage checks |
| `changed-scope-verification` | Verify changes match plan scope |
| `memory-sync-reconciliation` | Fix memory sync/import issues |
| `worktree-merge-recovery` | Recover from failed worktree merges |
| `feature-lifecycle-closure` | Post-ship cleanup checklist |

## Hooks

Configured in `.claude/settings.json`:

| Hook | Trigger | What it does |
|------|---------|-------------|
| `hook-dangerous-cmd.sh` | PreToolUse (Bash) | Blocks destructive commands (`rm -rf /`, `sudo`, `chmod 777`) |
| `hook-pre-commit-secrets.sh` | PreToolUse (Bash) | Scans staged files for secrets on `git commit` |
| `hook-sensitive-file.sh` | PreToolUse (Read) | Requires approval for `.env`, credentials, keys |
| `workflow_hooks.py pre_bash` | PreToolUse (Bash) | Token optimization telemetry — logs commands, suggests compact alternatives |
| `workflow_hooks.py post_edit` | PostToolUse (Write/Edit) | Auto-formats only files Claude edited |
| `hook-commit-confirm.sh` | PostToolUse (Bash) | Confirms commit with hash and message |
| `hook-subagent-stop.py` | SubagentStop | Parses `TASK_DONE: [...]` footer, runs memory `report-done` |
| `hook-pre-compact.py` | PreCompact | Checkpoints memory state before context compaction |

### Token Optimization Discovery

```bash
python3 scripts/workflow_checks.py discover --since-days 30
```

Reads `.cnogo/command-usage.jsonl` and reports missed compact-command opportunities and estimated saveable tokens.

## Automation Scripts

| Script | Purpose |
|--------|---------|
| `workflow_validate.py` | Contract validation, freshness, invariants, token budgets |
| `workflow_checks.py` | Package-aware review/verify + ship-ready gate + token telemetry + discover |
| `workflow_detect.py` | Stack auto-detection, populates `WORKFLOW.json` packages |
| `workflow_render.py` | Renders JSON contracts to markdown |
| `workflow_hooks.py` | Hook runner (pre_bash, post_edit) |
| `workflow_memory.py` | Memory engine CLI |
| `workflow_utils.py` | Shared utilities |

## Planning Artifacts

All artifacts are written as JSON (source of truth) + markdown (human-readable):

| Artifact | Location |
|----------|----------|
| Feature context | `docs/planning/work/features/<slug>/CONTEXT.json` |
| Plans | `docs/planning/work/features/<slug>/NN-PLAN.json` |
| Summaries | `docs/planning/work/features/<slug>/NN-SUMMARY.json` |
| Reviews | `docs/planning/work/features/<slug>/REVIEW.json` |
| Quick fixes | `docs/planning/work/quick/NNN-<slug>/PLAN.json` + `SUMMARY.json` |
| Research | `docs/planning/work/research/<slug>/RESEARCH.json` |

**JSON is canonical** for enforcement and automation. Markdown is the human narrative.

## Configuration

### `docs/planning/WORKFLOW.json`

Runtime policy knobs:

- **`enforcement`** — monorepo verify scope, operating principles, `tddMode`, `verificationBeforeCompletion`, `twoStageReview`, `taskOwnership`
- **`performance`** — post-edit formatting, output compaction, token telemetry, hook optimization
- **`freshness`** — stale artifact detection (context, plan, summary age limits)
- **`invariants`** — max file lines, max line length, TODO-requires-ticket, forbidden imports
- **`tokenBudgets`** — per-artifact word limits (command, context, plan, summary, review, research)
- **`packages`** — monorepo package definitions with per-package commands
- **`agentTeams`** — team settings (worktree mode, stale indicator, delegate mode, `maxTakeoversPerTask`)
- **`research`** — research mode (`auto`/`local`/`web`/`mcp`), min sources

### Monorepo / Polyglot Setup

```bash
python3 scripts/workflow_detect.py --write-workflow
```

Auto-detects packages and populates `WORKFLOW.json`. Then plan verify commands scope to the right package.

## Project Structure

```
your-project/
├── .claude/
│   ├── settings.json           # Permissions + hooks
│   ├── commands/               # 29 slash commands
│   ├── agents/                 # 3 agent definitions (debugger, implementer, resolver)
│   └── skills/                 # 16 reusable skills
├── .cnogo/
│   ├── memory.db               # SQLite runtime (gitignored)
│   └── issues.jsonl            # Git-tracked sync format
├── .github/
│   ├── CODEOWNERS
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── workflow-validate.yml
├── .githooks/
│   └── pre-commit              # Workflow validation + secret scanning
├── docs/
│   ├── planning/
│   │   ├── PROJECT.md          # Vision, constraints, patterns
│   │   ├── ROADMAP.md          # Phases and progress
│   │   ├── WORKFLOW.json       # Runtime policy knobs
│   │   ├── adr/                # Architecture Decision Records
│   │   └── work/               # Feature, quick, research, review artifacts
│   └── templates/              # Stack-specific CLAUDE.md templates
├── scripts/
│   ├── memory/                 # Memory engine (13 modules, stdlib only)
│   ├── workflow_*.py           # Automation scripts (9 files)
│   └── hook-*.sh/py            # Hook scripts (6 files)
├── tests/
│   └── test_bridge.py          # Memory bridge unit tests
├── CLAUDE.md                   # Project instructions
└── install.sh                  # Installer
```

## Install

### Local (single project)

```bash
./install.sh /path/to/your/project

# Include a manifest of installer-touched paths
./install.sh --manifest /path/to/your/project
```

### Global (reuse across repos)

```bash
# Clone once
git clone git@github.com:codenogo/workflowy.git ~/.workflowy/workflowy

# Shell helper
workflowy() { ~/.workflowy/workflowy/install.sh "$1"; }

# Install/upgrade any repo
workflowy /path/to/your/project
```

### Git Hooks (optional, for commits outside Claude)

```bash
./scripts/install-githooks.sh
```

Configures `core.hooksPath=.githooks` for workflow validation + secret scanning on commit.

## Principles

1. **Fresh context per plan** — max 3 tasks, never let context degrade
2. **Artifact-driven** — JSON contracts are the source of truth
3. **Discuss before plan** — capture decisions upfront, avoid rework
4. **Verify before completion** — no success claims without fresh evidence
5. **Memory survives sessions** — SQLite + JSONL sync across compaction
6. **Security by default** — secret scanning, dangerous command blocking, sensitive file guards

## License

MIT
