# Research: Opus 4.6 & Agent Workflow — What Can We Learn to Improve This Workflow

**Date:** 2026-02-10
**Mode:** auto (repo-local + web)

## Executive Summary

- **Agent Teams** (research preview in Opus 4.6) introduce a mesh-network multi-agent model with shared task lists, direct inter-agent messaging, and delegate mode — a paradigm shift from our current hub-and-spoke `/spawn` approach.
- **1M token context** (beta) dramatically reduces context-rot risk, but our <=3-task plan batching remains wise — Anthropic's own research shows context quality degrades long before hitting limits.
- **Adaptive effort controls** (low/medium/high/max) allow per-task cost/speed optimization that our workflow doesn't yet exploit — quick tasks should use low effort, complex planning should use max.
- **Context compaction** (API beta) enables longer sessions without manual `/pause`+`/resume` cycles, potentially simplifying our session handoff system.
- **Persistent subagent memory** is now a first-class feature — subagents can build knowledge across sessions, something our workflow doesn't leverage at all.
- **Custom subagents** (`.claude/agents/*.md`) replace ad-hoc `/spawn` prompts with version-controlled, team-shareable, skill-preloaded agent definitions with hooks and permission modes.
- **Anthropic's multi-agent research** found orchestrator+workers outperformed single agents by 90.2%, but also that **15x token usage** makes agent teams economically viable only for high-value tasks.
- **Long-running agent harnesses** (Anthropic engineering) recommend JSON-based progress tracking, bootstrapping rituals, single-feature-per-session focus, and git-based state recovery — patterns our workflow already partially implements.
- The biggest gap in our current workflow is the **absence of persistent, version-controlled subagent definitions** — we use ephemeral `/spawn` prompts instead of `.claude/agents/` files with memory, hooks, and skill preloading.
- Our `/sync` command for parallel sessions is conceptually aligned with Agent Teams but uses a manual coordination model; Agent Teams automate this with shared task lists and mailboxes.

## Context (Project-Specific)

This repo (`cnogo`) is a **Universal Development Workflow Pack** — a portable template that installs a 27-command SDLC workflow into any project. It currently implements:

- Artifact-driven development (markdown + JSON contracts)
- <=3-task plan batching (context freshness)
- `/spawn` for subagent orchestration (8 specializations)
- `/sync` for parallel session coordination
- Enforcement via hooks, CI validation, and secret scanning
- Skills library (15 playbooks including Karpathy principles)

**Constraints from PROJECT.md**: The project is template-based and must remain stack-agnostic, stdlib-only (no external Python deps), and installable via a single `install.sh`.

The current STATE.md shows the project is idle — this is the right time to evaluate architectural improvements.

## Options Considered

### Option A: Add Custom Subagent Definitions (`.claude/agents/`)

Replace ephemeral `/spawn` prompts with persistent, version-controlled subagent files using the new `.claude/agents/*.md` format.

- **When to use**: Immediately — this is the highest-ROI improvement.
- **Pros**:
  - Subagents become team-shareable artifacts checked into version control
  - Each agent gets focused system prompts, tool restrictions, and permission modes
  - Skills can be preloaded into agents (`skills:` field) instead of relying on prompt injection
  - Persistent memory (`memory: project`) enables agents to learn project patterns across sessions
  - Hooks (`PreToolUse`, `PostToolUse`) enforce agent-specific constraints (e.g., read-only reviewers)
  - Model routing: use `haiku` for fast exploration, `sonnet` for reviews, `inherit` (opus) for complex implementation
  - Compatible with Agent Teams when that feature stabilizes
- **Cons**:
  - Adds files to the `.claude/` directory (minor — already has commands/ and settings)
  - Requires updating `install.sh` to install agent definitions
  - Memory files need `.gitignore` consideration for `local` scope
- **Risks**:
  - Subagent API may evolve (mitigated: frontmatter format is stable per docs)
  - Over-specialization can fragment work unnecessarily

**Recommended agents to create:**

| Agent | Model | Tools | Memory | Skills |
|-------|-------|-------|--------|--------|
| `code-reviewer` | sonnet | Read, Grep, Glob, Bash | project | Security Review, Refactor Safety |
| `security-scanner` | sonnet | Read, Grep, Glob, Bash | user | Security Review, Auth/AuthZ |
| `test-writer` | inherit | Read, Edit, Write, Bash, Grep, Glob | project | Test Strategy |
| `debugger` | inherit | Read, Edit, Bash, Grep, Glob | project | Debug Investigation, RCA |
| `docs-writer` | haiku | Read, Write, Grep, Glob | none | Docs Quality |
| `perf-analyzer` | sonnet | Read, Grep, Glob, Bash | project | Performance Profiling |
| `explorer` | haiku | Read, Grep, Glob | none | (none — fast context gathering) |

### Option B: Integrate Agent Teams Support

Add first-class support for Opus 4.6 Agent Teams into the workflow, extending `/spawn` and `/sync`.

- **When to use**: After Agent Teams exits research preview (currently experimental).
- **Pros**:
  - Shared task list with dependency tracking (DAGs) replaces manual `/sync` coordination
  - Direct teammate-to-teammate messaging (mesh) vs. current hub-and-spoke
  - Delegate mode keeps lead focused on orchestration
  - Quality gate hooks (`TeammateIdle`, `TaskCompleted`) for automated standards enforcement
  - Natural fit for cross-layer features, parallel code review, competing hypothesis debugging
- **Cons**:
  - Still experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)
  - No session resumption after `/resume` or `/rewind`
  - 3-4x token cost vs. sequential work
  - No nested teams (teammates can't spawn teams)
  - One team per session
- **Risks**:
  - API instability during research preview
  - File conflict risk when multiple agents edit overlapping files
  - Token costs may be prohibitive for routine work

**Integration approach (when ready):**
1. Update `settings.json` template to include env var toggle
2. Create `/team` command that wraps Agent Teams creation with workflow conventions
3. Update `/spawn` to detect Agent Teams mode and use teammates instead of subagents
4. Update `/sync` to leverage shared task list instead of manual state files
5. Add `TeammateIdle` and `TaskCompleted` hooks for quality gates

### Option C: Exploit Effort Controls for Cost Optimization

Add effort-level awareness to workflow commands.

- **When to use**: Immediately — zero-risk improvement.
- **Pros**:
  - `/quick` tasks use low/medium effort (faster, cheaper)
  - `/discuss` and `/plan` use high effort (thorough reasoning)
  - `/research` and complex `/debug` use max effort (deep analysis)
  - Subagent model routing (haiku for exploration, sonnet for review, opus for implementation)
  - Significant cost reduction on routine operations
- **Cons**:
  - Effort levels are set via `/model` command, not programmatically in slash commands (limitation)
  - Requires user awareness/training
- **Risks**:
  - Low effort may miss subtle issues in quick tasks (mitigated: review gate still catches)

**Recommended effort mapping:**

| Command | Effort | Rationale |
|---------|--------|-----------|
| `/quick` | medium | Fast fixes don't need deep reasoning |
| `/discuss` | high | Decision capture benefits from thorough analysis |
| `/plan` | high | Architecture decisions need careful planning |
| `/implement` | high (default) | Standard coding quality |
| `/research` | max | Deep analysis justifies maximum deliberation |
| `/debug` (complex) | max | Root cause analysis needs exhaustive reasoning |
| `/review` | high | Thorough quality gates |
| `/status`, `/pause`, `/resume` | low | Operational commands, minimal reasoning needed |
| Explore subagent | haiku | Fast, read-only codebase scanning |
| Code review subagent | sonnet | Balanced capability and speed |

### Option D: Leverage Context Compaction for Session Continuity

Reduce friction in long sessions and simplify `/pause`+`/resume`.

- **When to use**: When context compaction exits beta (currently API-only beta).
- **Pros**:
  - Automatic context summarization at configurable thresholds
  - Longer productive sessions without manual intervention
  - Reduces need for aggressive plan batching (<=3 tasks) in some cases
  - Subagents already support auto-compaction at 95% capacity
- **Cons**:
  - Currently API beta — may not be available in all Claude Code environments
  - Compaction loses some nuance from earlier context
  - Our <=3-task batching is still valuable for verification discipline
- **Risks**:
  - Over-reliance on compaction could degrade output quality
  - Loss of specific earlier context details

**Integration approach:**
1. Document compaction awareness in CLAUDE.md
2. Update `/pause` to note compaction state
3. Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` in settings for project-level tuning
4. Keep <=3-task plans as a discipline mechanism (not just a context workaround)

### Option E: Add Persistent Subagent Memory

Enable subagents to build institutional knowledge across sessions.

- **When to use**: Alongside Option A (custom subagent definitions).
- **Pros**:
  - Code reviewer learns project patterns, recurring issues, coding conventions
  - Debugger accumulates knowledge of common failure modes, hotspots
  - Security scanner tracks known vulnerability patterns in the codebase
  - Reduces "cold start" cost of subagents re-learning context each session
- **Cons**:
  - Memory files consume disk space
  - Stale memory could mislead agents after major refactors
  - Requires periodic curation (200-line MEMORY.md limit auto-enforced)
- **Risks**:
  - Memory drift over time (mitigated: agents self-curate)
  - Privacy concerns if memory includes sensitive code patterns

**Recommended memory scopes:**

| Agent | Scope | Rationale |
|-------|-------|-----------|
| `code-reviewer` | project | Learns project-specific conventions, ships with repo |
| `security-scanner` | user | Security patterns apply across projects |
| `debugger` | project | Debug knowledge is codebase-specific |
| `test-writer` | project | Test patterns are project-specific |
| `perf-analyzer` | project | Performance hotspots are codebase-specific |
| `docs-writer` | none | Docs are generated fresh from current state |

### Option F: Adopt Anthropic's Long-Running Agent Harness Patterns

Strengthen session persistence and recovery based on Anthropic's engineering research.

- **When to use**: Incrementally, starting now.
- **Pros**:
  - JSON-based feature tracking (our contracts already do this)
  - Bootstrapping rituals (standardized session start) reduce wasted tokens
  - Git-based state recovery enables rollback without losing progress
  - Single-feature-per-session focus aligns with our plan batching
- **Cons**:
  - Some patterns already implemented in our workflow
  - Full implementation adds complexity to `/resume`
- **Risks**:
  - Over-engineering session management for simple projects

**Gaps to address:**
1. Our `/resume` could add a "bootstrapping ritual" — read STATE.md, check git log, verify test suite, then continue
2. Progress tracking could use JSON alongside markdown (we have JSON contracts but not incremental progress logs)
3. `init.sh`-style scripts for environment setup on resume (our `/context` partially handles this)

## Recommendation

**Implement in three phases:**

### Phase 1: Immediate (Low Risk, High ROI)
1. **Create `.claude/agents/` definitions** (Option A) for the 7 specializations in the table above
2. **Add effort-level guidance** (Option C) to command markdown files as comments/hints
3. **Update `install.sh`** to install agent definitions alongside commands
4. **Add `.claude/agents/` to the repo** as a first-class workflow artifact

### Phase 2: Near-Term (Medium Risk, High ROI)
5. **Enable persistent memory** (Option E) for code-reviewer, debugger, and security-scanner agents
6. **Strengthen `/resume`** with bootstrapping ritual (Option F) — STATE.md + git log + test verification
7. **Document context compaction** awareness (Option D) in CLAUDE.md
8. **Update `/spawn`** to prefer `.claude/agents/` definitions over inline prompts

### Phase 3: When Agent Teams Stabilize
9. **Add Agent Teams integration** (Option B) as an opt-in mode
10. **Create `/team` command** for coordinated multi-agent workflows
11. **Migrate `/sync`** to leverage Agent Teams' shared task list
12. **Add `TeammateIdle`/`TaskCompleted` hooks** for quality gates

**Rationale**: Phase 1 delivers the most value with minimal risk — custom subagent definitions are a stable, documented feature that directly improves our `/spawn` system. Phase 2 builds on that foundation. Phase 3 waits for Agent Teams to stabilize before investing in integration.

## Open Questions

- [ ] Should agent memory files (`.claude/agent-memory/`) be gitignored or checked in? (Recommendation: `project` scope = checked in, `local` scope = gitignored)
- [ ] How should we handle agent definition versioning when the frontmatter schema evolves?
- [ ] Should `/spawn` be deprecated in favor of direct agent invocation, or kept as a convenience wrapper?
- [ ] What's the token cost impact of persistent memory on subagent startup? Need benchmarking.
- [ ] When Agent Teams exit experimental, should we default to teams for `/review` (parallel reviewers)?

## Sources

- **Anthropic — Introducing Claude Opus 4.6** — https://www.anthropic.com/news/claude-opus-4-6 — Official announcement with Agent Teams, 1M context, effort controls, compaction details
- **Claude Code Docs — Create Custom Subagents** — https://code.claude.com/docs/en/sub-agents — Comprehensive guide to `.claude/agents/` format, frontmatter fields, memory, hooks, permissions
- **Anthropic Engineering — Multi-Agent Research System** — https://www.anthropic.com/engineering/multi-agent-research-system — Architecture patterns, 8 prompting principles, 90.2% improvement data, economic analysis (15x tokens)
- **Anthropic Engineering — Effective Harnesses for Long-Running Agents** — https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents — Two-agent system, JSON progress tracking, bootstrapping rituals, failure prevention
- **Claude Code Agent Teams Guide** — https://claudefa.st/blog/guide/agents/agent-teams — Agent Teams architecture, shared task lists, mailbox system, delegate mode, when to use
- **Claude World — Claude Opus 4.6 Overview** — https://claude-world.com/articles/claude-opus-4-6/ — Benchmarks, effort tuning details, API pricing, developer impact analysis
- **Repo: docs/planning/WORKFLOW.json** — `docs/planning/WORKFLOW.json` — Current enforcement config showing research mode, packages, enforcement settings
- **Repo: docs/skills.md** — `docs/skills.md` — 15 reusable playbooks that should map to subagent skill preloading
- **Repo: .claude/commands/spawn.md** — `.claude/commands/spawn.md` — Current `/spawn` implementation using inline prompts (to be replaced by agent definitions)
- **Repo: .claude/settings.json** — `.claude/settings.json` — Current hooks, permissions, and enforcement configuration
