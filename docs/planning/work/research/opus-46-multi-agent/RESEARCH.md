# Research: Opus 4.6 Multi-Agent Patterns & Claude Code Orchestration

**Date:** 2026-02-14
**Mode:** auto (web + local)

## Executive Summary

- **Claude Code Agent Teams** is the primary multi-agent framework: a team lead spawns teammates via `Task` tool with shared task lists and bidirectional messaging. It is experimental (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).
- **Subagents** (fire-and-forget via `Task` tool) and **Agent Teams** (persistent teammates with coordination) use the same underlying mechanism — the difference is lifecycle and communication.
- **Opus 4.6** is the model (brain); **Claude Code** is the runtime (orchestrator). There is no special "agent mode" in the model — agentic behavior emerges from the tool-use loop.
- **Claude Agent SDK** (formerly Claude Code SDK) provides programmatic access for building autonomous agents beyond interactive coding sessions. Core loop: gather context, take action, verify, iterate.
- **Best practices**: 2-5 teammates max, clear file boundaries (no two agents editing same file), delegate mode for leads, serial fallback when files overlap.
- **cnogo's architecture** already implements these patterns well: implementer/debugger agents, memory-backed claim/close lifecycle, bridge module for plan-to-task translation, file conflict detection.
- **Key limitation**: no nested subagents (agents cannot spawn agents), no nested teams, one team per session, no session resumption for teams.
- **Opus 4.6 advantages**: 1M token context (beta), 76% needle-in-haystack accuracy, highest Terminal-Bench 2.0 score, context compaction, adaptive thinking effort levels.

## Context (Project-Specific)

cnogo is a zero-dependency workflow engine that orchestrates Claude Code sessions via slash commands and Agent Teams. It already has:

- 2 agent definitions: `implementer` (sonnet, task execution) and `debugger` (inherited model, root cause analysis)
- Memory engine with SQLite storage, dependency graph, JSONL sync
- Bridge module (`scripts/memory/bridge.py`) translating plan JSON into agent task descriptions
- `/team implement` command for parallel plan execution with file conflict detection
- `/spawn` command for single-agent fire-and-forget tasks
- Recovery mechanism in `/resume` for stale claims from dead agents

**PROJECT.md constraints**: Python stdlib only, bash install.sh distribution, stack-agnostic, no runtime services.

## Options Considered

### Option A: Current Architecture (Subagents + Agent Teams + Memory Bridge)

**When to use**: When plans have independent tasks with non-overlapping files.

**Pros**:
- Already implemented and tested in cnogo
- Memory-backed claim/close prevents duplicate work
- File conflict detection warns before parallel execution
- Bridge generates minimal, focused agent prompts (ID-based context, not full injection)
- Recovery via `/resume` handles stale claims

**Cons**:
- No nested agents (complex multi-step tasks can't sub-delegate)
- One team per session limits concurrent feature work
- Agent Teams still experimental (may change)
- No heartbeat/timeout for detecting dead agents (manual only)

**Risks**:
- Agent Teams API could change in future Claude Code versions
- Long-running tasks may hit context limits (mitigated by Opus 4.6's 1M tokens)

### Option B: Claude Agent SDK (Programmatic Multi-Agent)

**When to use**: For autonomous workflows beyond interactive coding — CI/CD pipelines, batch processing, scheduled tasks.

**Pros**:
- Programmatic control over agent lifecycle
- Can build custom orchestration patterns (fan-out, map-reduce, pipeline)
- SDK handles session management, tool execution, error recovery
- Suitable for non-interactive automation

**Cons**:
- Requires Node.js runtime (violates cnogo's "no runtime services" constraint)
- Separate from Claude Code's built-in Agent Teams
- More complex setup and deployment
- Not designed for interactive development workflows

**Risks**:
- SDK is still evolving (API changes expected)
- Overhead of maintaining a separate agent runtime

### Option C: Hybrid (Agent Teams for Interactive + SDK for Automation)

**When to use**: When both interactive development and automated pipelines are needed.

**Pros**:
- Best of both worlds
- Agent Teams for developer sessions, SDK for CI/CD
- Could share memory engine across both

**Cons**:
- Dual maintenance burden
- Two different orchestration models to understand
- Complexity

**Risks**:
- Feature divergence between Agent Teams and SDK
- Developer confusion about which to use when

### Option D: Enhanced Single-Agent with Subagent Delegation

**When to use**: When tasks are sequential or have heavy file overlap.

**Pros**:
- Simpler mental model (one agent, fire-and-forget subagents)
- No coordination overhead
- Built-in to Claude Code (not experimental)
- Subagents can be backgrounded or run in parallel

**Cons**:
- No bidirectional communication (fire-and-forget only)
- No shared task list
- Lead must poll for completion manually
- Less suitable for truly parallel independent work

**Risks**:
- Scale limitation (many subagents = many API conversations)

## Architecture Deep Dive

### Claude Code Agent Teams Architecture

```
Team Lead (you)
├── TeamCreate → creates team + shared task list
├── TaskCreate → defines work items
├── Task tool (spawn) → creates teammates
│   ├── Teammate 1 (implementer) ← SendMessage ↔ Lead
│   ├── Teammate 2 (implementer) ← SendMessage ↔ Lead
│   └── Teammate 3 (debugger)    ← SendMessage ↔ Lead
├── TaskList → monitor progress
└── SendMessage → coordinate
```

**Key mechanics**:
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`
- Teammates go idle after each turn (normal — send message to wake)
- Messages auto-delivered (no polling needed)
- Shutdown via `shutdown_request` → teammate approves/rejects

### Subagent Types (Built-in)

| Type | Model | Tools | Use Case |
|------|-------|-------|----------|
| Explore | haiku | Read-only (Glob, Grep, Read, WebFetch, WebSearch) | Fast codebase scanning |
| Plan | inherit | Read-only (same as Explore) | Architecture design |
| General-purpose | inherit | All tools (Read, Edit, Write, Bash, Grep, Glob, Task) | Full implementation |
| Bash | - | Bash only | Command execution |

### Custom Agents (`.claude/agents/*.md`)

YAML frontmatter configuration:
```yaml
name: implementer
description: Executes plan tasks with memory-backed claim/close cycle
tools: [Read, Edit, Write, Bash, Grep, Glob]
model: sonnet
maxTurns: 30
permissionMode: bypassPermissions  # or default, plan, acceptEdits
```

Features:
- Persistent memory scopes: user (`~/.claude/agent-memory/`), project (`.claude/agent-memory/`), local
- Hooks: custom PreToolUse/PostToolUse
- Skills: load specific playbooks
- Cannot spawn other subagents (no nesting)

### Opus 4.6 Model Capabilities

| Capability | Value | Impact on Multi-Agent |
|------------|-------|-----------------------|
| Context window | 1M tokens (beta) | Larger plans, more context per agent |
| Needle-in-haystack | 76% at 1M tokens | Better at finding relevant info in large contexts |
| Terminal-Bench 2.0 | Highest score | More reliable tool use and bash execution |
| Context compaction | Beta | Longer agent sessions without context loss |
| Adaptive thinking | Effort levels | Agents can adjust reasoning depth per task |

### cnogo's Bridge Pattern

```
NN-PLAN.json
    │
    ▼
plan_to_task_descriptions()
    │  ├── Reads plan JSON
    │  ├── Checks memory for closed tasks (skip)
    │  ├── Creates memory issues if needed
    │  └── Generates agent prompts
    │
    ▼
[{name, description, memoryId, files, verify, blockedBy, skipped}, ...]
    │
    ▼
/team implement
    │  ├── detect_file_conflicts() → warn if overlap
    │  ├── TeamCreate + TaskCreate (two-pass: create then wire deps)
    │  ├── Spawn implementer per task
    │  └── Monitor → planVerify → commit → dismiss
    │
    ▼
NN-SUMMARY.md + NN-SUMMARY.json
```

## Recommendation

**Continue with Option A (current architecture)** with these enhancements:

1. **Add agent heartbeat/timeout detection**: Track `claimed_at` timestamp in memory; `/status` can flag tasks claimed >N minutes ago as potentially stale.

2. **Consider model selection per task type**: Use `sonnet` for straightforward implementation (already done for implementer), `opus` for complex debugging or architecture decisions, `haiku` for read-only exploration.

3. **Add plan-level parallelism hints**: Extend `NN-PLAN.json` with a `parallelizable: true/false` field so `/implement` can auto-detect team mode more reliably.

4. **Wait on Agent SDK adoption**: The SDK is better suited for CI/CD automation. cnogo's interactive workflow doesn't need it yet. Revisit when cnogo adds `/verify-ci` pipeline features.

5. **Monitor Agent Teams stability**: The feature is experimental. Pin cnogo to known-good Claude Code versions and document the required env var in install.sh.

## Open Questions

- [ ] Will Agent Teams exit experimental status in Claude Code 2.x?
- [ ] Should cnogo support multiple concurrent teams (e.g., parallel features)?
- [ ] Is there a practical limit on teammate count before context/cost becomes prohibitive?
- [ ] Should the bridge generate different prompts for different agent types (implementer vs debugger)?

## Sources

- [Claude Code Agent Teams — Official Docs](https://code.claude.com/docs/en/agent-teams) — Complete architecture, configuration, best practices, limitations for Agent Teams
- [Claude Code Sub-agents — Official Docs](https://code.claude.com/docs/en/sub-agents) — Built-in types, custom agent creation, YAML config, persistent memory
- [Building Agents with the Claude Agent SDK — Anthropic Blog](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) — SDK architecture, multi-agent patterns (search, judge, orchestrator)
- [Claude Opus 4.6 Announcement — Anthropic](https://www.anthropic.com/news/claude-opus-4-6) — 1M context, needle-in-haystack, Terminal-Bench, agent teams native
- `.claude/agents/implementer.md` — cnogo's implementer agent definition (sonnet, claim/close cycle)
- `.claude/agents/debugger.md` — cnogo's debugger agent definition (hypothesis-driven, escalation)
- `.claude/commands/team.md` — cnogo's team orchestration command (create, implement, status, dismiss)
- `.claude/commands/implement.md` — Serial vs team auto-detection logic
- `scripts/memory/bridge.py` — Plan-to-task translation, file conflict detection, prompt generation
- `scripts/memory/__init__.py` — Memory engine public API (claim, close, ready, prime)
- `scripts/memory/storage.py` — SQLite storage with WAL, atomic operations, cycle detection
- `docs/planning/WORKFLOW.json` — Agent Teams configuration (enabled, delegateMode, defaultCompositions)
- `docs/planning/PROJECT.md` — Project constraints (stdlib only, no runtime services)

---
*Researched: 2026-02-14*
