# Universal Development Workflow Pack

A portable workflow system combining Boris Cherny's parallel session approach with GSD's context engineering, adapted for enterprise-grade projects.

## Features

- **27 slash commands** for the full development lifecycle (including brainstorming + research + bug routing + close)
- **Deep research artifact** support for de-risking decisions (`/research`)
- **Parallel session coordination** across multiple checkouts
- **Secret scanning** built into pre-commit hooks
- **Stack auto-detection** (Java, TypeScript, Python, Go, Rust)
- **Enterprise templates** (ADR, CODEOWNERS, PR template, release notes)
- **SBOM generation** support (CycloneDX)

## Quick Start

```bash
# Option 1: Run install script
./install.sh /path/to/your/project

# Option 2: Manual copy
cp -r .claude your-project/
cp -r docs your-project/
cp -r .github your-project/
cp CLAUDE.md your-project/
cp CHANGELOG.md your-project/

# Verify installation
cd your-project && claude
/status
```

## How to Use This Workflow (End-to-End)

This pack is designed to turn Claude into a reliable SDLC copilot by making work **artifact-driven** (docs + contracts), **small-batch** (≤3 tasks/plan), and **verifiable** (task-level checks + review gates).

### Prerequisites

- **Claude Code** installed and available as `claude`
- **Git** available as `git`
- **Python 3** available as `python3` (used for the validator + fast hooks runner; stdlib only)
- **GitHub CLI** (`gh`) optional (used by `/ship` for PR creation)

### Install Into a Project

You can install this pack into any repository (single app repo, monorepo, or polyglot).

- **Option A (recommended)**: use the installer

```bash
./install.sh /path/to/your/project
```

- **Option B (manual)**: copy the pack files

```bash
cp -r .claude /path/to/your/project/
cp -r .github /path/to/your/project/
cp -r docs /path/to/your/project/
cp CLAUDE.md CHANGELOG.md /path/to/your/project/
```

### First Run Checklist (Required)

From the target project root:

```bash
cd /path/to/your/project
claude
/init
```

#### Recommended: Enable Package-Aware Checks (Monorepos/Polyglots)

If your repo is a monorepo or polyglot, run the detector once to populate `WORKFLOW.json` with `packages[]` and suggested per-package commands:

```bash
python3 scripts/workflow_detect.py --write-workflow
```

This powers package-aware execution for:

- `python3 scripts/workflow_checks.py review`
- `python3 scripts/workflow_checks.py verify-ci <feature-slug>`

Then edit these once (they are your long-term “source of truth”):

- **`docs/planning/PROJECT.md`**: vision, constraints, architecture patterns
- **`docs/planning/STATE.md`**: what’s in progress + handoffs
- **`docs/planning/WORKFLOW.json`**: enforcement + performance knobs (monorepo packages, scoping strictness)

Finally:

```bash
/status
```

### Daily Usage: Feature Work (Tier 2–3)

Use this when work is non-trivial (new API, multi-file changes, riskier changes, schema work, etc.).

#### 1) Discuss (decisions first)

```bash
/discuss "<feature display name>"
```

Outputs:

- `docs/planning/work/features/<feature-slug>/CONTEXT.md`
- `docs/planning/work/features/<feature-slug>/CONTEXT.json`
- Updates `docs/planning/STATE.md`

#### (Optional) Deep Research (when uncertainty is high)

If the subject requires best-practice/standard knowledge (auth, security, payments, distributed systems, compliance, etc.), run:

```bash
/research "<topic>"
```

Outputs:

- `docs/planning/work/research/<slug>/RESEARCH.md`
- `docs/planning/work/research/<slug>/RESEARCH.json`

Then link it from the feature `CONTEXT.md`/`CONTEXT.json`.

#### 2) Plan (small batches, ≤3 tasks each)

```bash
/plan <feature-slug>
```

Outputs (per plan):

- `docs/planning/work/features/<feature-slug>/NN-PLAN.md`
- `docs/planning/work/features/<feature-slug>/NN-PLAN.json`

#### 3) Implement (execute one plan at a time)

```bash
/implement <feature-slug> 01
```

Outputs:

- A commit (atomic)
- `docs/planning/work/features/<feature-slug>/01-SUMMARY.md`
- `docs/planning/work/features/<feature-slug>/01-SUMMARY.json`
- Updates `docs/planning/STATE.md`

Repeat for `02`, `03`, etc.

#### 4) Verify (human UAT) + Verify CI (automation)

- **Automation / CI friendly**:

```bash
/verify-ci <feature-slug>
```

- **Human acceptance**:

```bash
/verify <feature-slug>
```

Outputs:

- `VERIFICATION-CI.md` + `VERIFICATION-CI.json` (CI)
- `VERIFICATION.md` + `VERIFICATION.json` (human)

#### 5) Review (quality gates)

```bash
/review
```

Outputs:

- `docs/planning/work/features/<feature-slug>/REVIEW.md` + `REVIEW.json` (if a feature is active)
  - or `docs/planning/work/review/<timestamp>-REVIEW.md` + `.json` otherwise

#### 6) Ship (PR)

```bash
/ship
```

Creates a PR via `gh` (if available) and updates `STATE.md`.

### Daily Usage: Quick Fixes (Tier 1)

Use this for small fixes (bug fix, tiny config tweak, docs update).

```bash
/quick "fix typo in README"
```

Outputs:

- `docs/planning/work/quick/NNN-<slug>/PLAN.md` + `PLAN.json`
- `docs/planning/work/quick/NNN-<slug>/SUMMARY.md` + `SUMMARY.json`
- A commit

Then:

```bash
/review
/ship
```

### Bug Workflow (Recommended Entry Point)

If you have a bug report and you’re not sure whether it’s “quick” or “deep”, start with:

```bash
/bug "describe the bug"
```

It routes you to `/quick`, `/debug`, or `/discuss` and ensures branch safety and verification guidance.

### Post-Merge Cleanup

After a feature is merged into `main`, clean up state and optionally archive feature artifacts:

```bash
/close <feature-slug>
```

### Enforcement: Validate Anytime

Run this anytime you want a fast “are we still following the workflow?” check:

```bash
/validate
```

Under the hood, it runs `python3 scripts/workflow_validate.py`.

### CI Usage (Recommended)

In CI, run the validator and (optionally) CI verification:

```bash
python3 scripts/workflow_validate.py
# Optionally: call /verify-ci in a Claude-run CI job OR mirror its checks in your pipeline
```

This repo includes a ready-to-use GitHub Actions workflow:

- `.github/workflows/workflow-validate.yml`

If you’ve populated `docs/planning/WORKFLOW.json` → `packages[].commands`, you can also run package-aware checks in CI:

```bash
python3 scripts/workflow_checks.py review
```

### Monorepo / Polyglot Setup (Recommended)

To make plan verification scoping smarter, populate `docs/planning/WORKFLOW.json` with packages:

```json
{
  "version": 1,
  "repoShape": "auto",
  "enforcement": { "monorepoVerifyScope": "warn" },
  "packages": [
    { "name": "api", "path": "packages/api", "kind": "node" },
    { "name": "web", "path": "packages/web", "kind": "node" },
    { "name": "orders", "path": "services/orders", "kind": "java" }
  ]
}
```

You can auto-populate this using:

```bash
python3 scripts/workflow_detect.py --write-workflow
```

Then in plan contracts prefer `task.cwd` or scoped verify commands (`cd <pkg> && ...`).

## The Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FEATURE WORK (Tier 2-3)                       │
│                                                                      │
│   /discuss ──► /plan ──► /implement ──► /verify ──► /review ──► /ship│
│       │          │            │            │           │          │  │
│   Decisions   Tasks≤3    Fresh ctx    Does it     Quality      PR    │
│   captured    each       per plan     work?       gates              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        QUICK FIXES (Tier 1)                          │
│                                                                      │
│   /quick ──► /review ──► /ship                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        ENFORCEMENT & CI                               │
│                                                                      │
│   /validate ──► /verify-ci ──► /research ──► /brainstorm             │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        RELEASES                                      │
│                                                                      │
│   /changelog ──► /release [major|minor|patch]                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Parallel Sessions (Boris Cherny Style)

### Local (5 terminals)

```bash
# Create separate checkouts per workstream
git clone git@github.com:you/project.git project-main
git clone git@github.com:you/project.git project-feature
git clone git@github.com:you/project.git project-bugfix
git clone git@github.com:you/project.git project-refactor
git clone git@github.com:you/project.git project-tests

# Each terminal gets its own checkout
cd project-feature && claude
```

### Remote (5-10 on claude.ai/code)

```bash
# Start remote sessions from CLI
& Implement the retry logic for failed deliveries
& Add pagination to the search endpoint

# Monitor
/tasks

# Bring back to local
claude --teleport session_xxx
```

### Coordinate Across Sessions

```bash
# See what's happening in all sessions
/sync

# Update this session's status
/sync update

# Claim a file to avoid conflicts
/sync claim src/services/notification.ts
```

## Commands Reference

### Core Workflow

| Command | Purpose |
|---------|---------|
| `/discuss <feature>` | Capture decisions before coding |
| `/research <topic>` | Deep research artifact (repo + MCP + optional web) |
| `/brainstorm <idea>` | Narrow ideas via Q&A + options before `/discuss` |
| `/plan <feature>` | Create implementation tasks (≤3 per plan) |
| `/implement <feature> <plan>` | Execute a plan with verification |
| `/verify <feature>` | User acceptance testing |
| `/verify-ci <feature>` | Non-interactive verification (CI-friendly) |
| `/review` | Quality gates (lint, test, security, SAST) |
| `/ship` | Commit, push, create PR |
| `/validate` | Enforce workflow rules (contracts, slugs, task limits) |

### Fast Path

| Command | Purpose |
|---------|---------|
| `/quick <task>` | Small fixes without full ceremony |
| `/tdd <feature>` | Test-driven development flow |

### Session Management

| Command | Purpose |
|---------|---------|
| `/status` | Current position, blockers, next steps |
| `/pause` | Create handoff for later resume |
| `/resume` | Restore from paused session |
| `/sync` | Coordinate across parallel sessions |
| `/context <feature>` | Load relevant files for a feature |

### Debugging & Recovery

| Command | Purpose |
|---------|---------|
| `/debug <issue>` | Systematic debugging with state tracking |
| `/bug <description>` | Bug triage router (quick vs debug vs discuss) |
| `/rollback` | Revert changes (last, commit-hash, or branch) |

### Release

| Command | Purpose |
|---------|---------|
| `/changelog` | Generate changelog from git history |
| `/release <version>` | Create release with notes, tag, SBOM |

### Setup

| Command | Purpose |
|---------|---------|
| `/init` | Auto-populate templates based on stack detection |
| `/close <feature>` | Post-merge cleanup (STATE.md + optional archive) |

### MCP Integrations

| Command | Purpose |
|---------|---------|
| `/mcp` | Manage Model Context Protocol connections (GitHub, Jira, Sentry, etc.) |

### Agents

| Command | Purpose |
|---------|---------|
| `/background <task>` | Fire-and-forget long-running tasks |
| `/spawn <type> <task>` | Launch specialized subagents (security, tests, docs, perf) |

## File Structure

```
your-project/
├── .claude/
│   ├── settings.json           # Permissions + hooks
│   └── commands/               # 27 slash commands
│
├── .github/
│   ├── CODEOWNERS              # Code ownership
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/planning/
│   ├── PROJECT.md              # Vision, constraints, patterns
│   ├── STATE.md                # Current position, decisions
│   ├── ROADMAP.md              # Phases and progress
│   ├── WORKFLOW.json           # Optional enforcement config (validator/monorepo)
│   ├── adr/                    # Architecture Decision Records
│   │   └── ADR-TEMPLATE.md
│   └── work/
│       ├── quick/              # Tier 1: hotfixes
│       ├── features/           # Tier 2-3: full cycle
│       │   └── CONTEXT-TEMPLATE.md
│       ├── debug/              # Debug sessions
│       ├── background/         # Background tasks
│       ├── review/             # Persisted review reports
│       ├── research/           # Research artifacts
│       └── ideas/              # Brainstorm artifacts
│
├── docs/templates/             # Stack-specific CLAUDE.md templates
│   ├── CLAUDE-java.md
│   ├── CLAUDE-typescript.md
│   ├── CLAUDE-python.md
│   ├── CLAUDE-go.md
│   └── CLAUDE-rust.md
│
├── CLAUDE.md                   # Agent instructions
├── docs/skills.md              # Reusable “skills” playbooks for consistent SDLC execution
└── CHANGELOG.md                # Release history
```

## Hooks

### PreToolUse (Security Validation)

Validates commands **before** execution:
- **Bash commands:** Blocks dangerous patterns (`rm -rf /`, `sudo rm`, `chmod 777`, disk operations)
- **Read operations:** Requires approval for sensitive files (`.env`, credentials, private keys)

### PostToolUse (Auto-format on edit)

By default, formatting runs **after edits** but is optimized for latency:

- Uses `python3 scripts/workflow_hooks.py post_edit` to format **only the files Claude edited** when possible
- Configurable via `docs/planning/WORKFLOW.json` (`performance.postEditFormat*`)

### PreCommit

1. **Secret scanning** — Blocks commits containing:
   - AWS access keys (`AKIA...`)
   - Anthropic API keys (`sk-ant-...`)
   - OpenAI API keys (`sk-...`)
   - GitHub tokens (`ghp_...`)
   - Slack tokens (`xox...`)
   - Azure storage keys (`AccountKey=...`)
   - GCP service account JSON
   - Private keys (`BEGIN PRIVATE KEY`)

2. **Tests** — Runs test suite for your stack

### PostCommit

Confirms commit with hash and message.

## Security

### Permissions

The settings.json includes:
- **Allowed:** Standard dev tools (git, build tools, grep, etc.)
- **Denied:**
  - Destructive commands (`rm -rf /`, `sudo`)
  - Reading secrets (`.env`, `*-prod.yml`, `*.pem`, `*.key`)
  - Pipe to shell (`curl | bash`)

### Review Command

`/review` runs:
1. Linting (stack-specific)
2. Tests
3. Secret detection
4. Dependency vulnerability scanning (`npm audit`, `pip-audit`, etc.)
5. SAST via Semgrep (if installed)
6. Type checking

## Customisation

### Add Stack-Specific Hooks

Edit `.claude/settings.json`:

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "your-formatter-command || true"
      }
    ]
  }
]
```

### Add Project-Specific Commands

Create `.claude/commands/your-command.md`:

```markdown
# Your Command: $ARGUMENTS

[Instructions for Claude]
```

### Extend Templates

- `docs/planning/PROJECT.md` — Add your patterns
- `docs/planning/adr/ADR-TEMPLATE.md` — Adjust for your org
- `.github/CODEOWNERS` — Set your teams

## Principles

1. **Fresh context per plan** — Never let Claude degrade. Max 3 tasks per plan.
2. **Atomic commits** — One commit per task. Git bisect works. Reverts are clean.
3. **Discuss before plan** — Capture decisions upfront. Avoid rework.
4. **Verify before ship** — Trust but verify. Does it actually work?
5. **State survives sessions** — STATE.md is your memory across context switches.
6. **Security by default** — Secret scanning, dependency audits, SAST.

### Karpathy-Inspired Claude Coding Principles

These strengthen the workflow’s reliability and reduce common LLM pitfalls. Source: [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills).

1. **Think Before Coding**
2. **Simplicity First**
3. **Surgical Changes**
4. **Goal-Driven Execution**

## Monorepos & Polyglots

This pack supports single-repo apps, monorepos, and enterprise polyglots.

- **Default behavior**: the validator will **warn** when plan verify commands look unscoped in monorepos.
- **Configure enforcement** in `docs/planning/WORKFLOW.json`:
  - `enforcement.monorepoVerifyScope`: `"warn"` (default) or `"error"`
  - `enforcement.karpathyChecklist`: `"off" | "warn" | "error"` (enforce Karpathy checklist in review artifacts)

## Artifact Contracts (JSON)

For key workflow artifacts, write a machine-checkable `*.json` contract next to the markdown file.

- **Standard fields** (recommended across all contracts):
  - `schemaVersion` (number)
  - `feature` (feature slug)
  - `timestamp` (ISO-8601)

### Avoiding JSON/Markdown Drift

To prevent contracts and markdown from diverging:

- **Treat JSON as canonical** for enforcement and automation.
- **Treat Markdown as human-readable** narrative/summary.
- When creating artifacts, prefer: **write/update JSON first**, then write markdown to match it.

## WORKFLOW.json Schema

- **Config file**: `docs/planning/WORKFLOW.json`
- **Editor schema**: `docs/planning/WORKFLOW.schema.json` (helps catch typos in IDEs)

## Latency / Performance Tuning

This pack is designed to be safe by default, but you can reduce iteration latency:

- **Fast post-edit formatting (default)**: the Claude hook now tries to format **only the files Claude edited**.
- **Configure** via `docs/planning/WORKFLOW.json`:
  - `performance.postEditFormat`: `"auto"` or `"off"`
  - `performance.postEditFormatScope`: `"changed"` (default) or `"repo"`

If you see formatting slowing you down in very large repos, set `postEditFormat` to `"off"` and rely on `/review` + CI format checks instead.

## Enforcement Outside Claude (Optional)

To enforce workflow validation + secret scanning when committing outside Claude:

```bash
chmod +x .githooks/pre-commit scripts/install-githooks.sh
./scripts/install-githooks.sh
```

This configures `core.hooksPath=.githooks` for the repository.

## Credits

- **Boris Cherny** — Parallel session workflow, plan mode, fresh context pattern
- **GSD (TÂCHES)** — Context engineering, STATE.md, discuss → plan → execute → verify cycle
- **Keep a Changelog** — Changelog format
- **Conventional Commits** — Commit message format

## License

MIT
