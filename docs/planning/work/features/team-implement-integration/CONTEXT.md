# Team-Implement Integration - Implementation Context

## Problem Statement

The cnogo memory engine has all the primitives for multi-agent coordination (ready queue, atomic claiming, blocked cache, dependency ordering, audit trail), but there is no bridge between these primitives and the actual team/agent system. Specifically:

1. **Teams can't run the implement loop** - `/team create` spawns agents from `.claude/agents/`, but none of them know how to execute the `/implement` cycle (load plan -> claim task -> execute -> verify -> close).
2. **Plan tasks don't map to team tasks** - Plans produce `NN-PLAN.json` with `memoryId` per task, but `/team create` creates generic tasks via `TaskCreate` that have no connection to plan structure.
3. **No dependency-driven work queue** - Agent Teams' `TaskList` supports `blocks/blockedBy` but these aren't derived from memory engine dependencies. Agents poll `TaskList` for work rather than querying `memory.ready()`.
4. **File boundaries are advisory** - The `/team` command documents file boundaries but nothing enforces them.
5. **Two coordination layers are disconnected** - Claude Code's `TaskCreate/TaskList` (session-scoped, ephemeral) and memory engine's SQLite issues (persistent, git-portable) don't talk to each other.

## Research Findings (2026)

### Industry Patterns

| System | Architecture | Key Insight |
|--------|-------------|-------------|
| **Beads** (Steve Yegge) | JSONL-first, SQLite as cache, git-native | Source of truth is file-based; agents use `bd ready --json` to resume |
| **OpenHands Refactor SDK** | Task decomposition by directory boundaries + dependency analysis | Hardest part is decomposing into individually achievable tasks |
| **Open SWE** (LangChain) | Planner -> Programmer -> Reviewer pipeline with LangGraph | Dedicated Planner agent creates plan, Programmer executes, Reviewer validates |
| **SERA** (Allen AI) | Soft-verified agents, 8B-32B, compatible with Claude Code | Train agents on your repo's patterns; SVG is 26x cheaper than RL |
| **Agyn** (arxiv) | Manager/Engineer/Reviewer/Researcher team | 72.2% SWE-bench; "future progress depends as much on organizational design as model capability" |
| **Claude-Flow** | Hierarchical/mesh swarms via MCP, SQLite-backed | 12-table SQLite store for distributed state, HNSW-indexed shared memory |
| **Claude Code Agent Teams** | TaskCreate/TaskUpdate with blocks/blockedBy, SendMessage, idle cycling | Teammates go idle between turns; leader assigns via TaskUpdate |

### 2026 Industry Consensus

**80-90% automation with human checkpoints outperforms 100% automation.** The breakthrough is not in agents themselves but in how work is decomposed and coordinated. The dominant pattern across all frameworks is a shared work queue with dependency DAG, atomic claiming, and file boundary enforcement.

**Milestone**: 16 Claude Code agents using Opus 4.6 produced a Rust-based C compiler (~100K LOC) that compiled a bootable Linux 6.9 kernel across x86, ARM, and RISC-V architectures. This demonstrates agent teams can handle large-scale implementation when properly coordinated.

### Agent Teams Technical Details (from system prompts)

- **Delegate mode** (Shift+Tab): Forces lead to coordinate-only; cannot edit files
- **Plan approval mode** (`plan_mode_required`): Teammates plan before implementing; lead approves
- **Quality gate hooks**: `TeammateIdle` (exit code 2 sends feedback), `TaskCompleted` (exit code 2 prevents completion)
- **Task claiming**: Atomic via file locking; teammates should claim in ID order
- **Idle state is normal**: Teammates go idle after every turn; sending a message wakes them
- **Background execution**: Ctrl+B backgrounds agents; hooks support `async: true`

### Key Design Insights

1. **OpenHands' insight**: The hard part is decomposition into individually achievable tasks. Our `/plan` command already does this (max 3 tasks, explicit files/verify per task). We just need to translate plan tasks into team-executable units.

2. **Open SWE's insight**: The Planner -> Programmer -> Reviewer pipeline maps directly to our `/plan` -> `/implement` -> `/review` SDLC. The gap is that our `/implement` is monolithic (one agent does everything) rather than distributable.

3. **Beads' insight**: JSONL-first with SQLite as cache is exactly our architecture. Their `bd ready --json` pattern matches our `memory.ready()`. The remaining gap is wiring `ready()` into the agent team's work loop.

4. **Claude Code Teams' insight**: Teammates claim tasks from `TaskList`, go idle between turns, and wake on messages. The pattern is: leader creates tasks with `TaskCreate`, sets `blockedBy`, and agents poll for unblocked work. Our memory engine already has this — we just need a bridge layer.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Architecture | Implement agent: a new `.claude/agents/implementer.md` that can execute plan tasks | Keeps existing agents focused (reviewer, tester, etc.) while adding implementation capability |
| Plan Translation | `/team implement <feature> <plan>` generates team tasks from `NN-PLAN.json` with memory linkage | Reuses existing plan structure rather than inventing a new task format |
| Work Queue | Bridge layer reads `memory.ready()` and creates/unblocks corresponding `TaskList` entries | Two systems stay in sync: memory is source of truth, TaskList is agent-visible |
| Verify Loop | Each agent task includes verify commands from plan; agent runs verify and closes memory issue on pass | Plan's `verify[]` array becomes the agent's success criterion |
| File Boundaries | Enforce at plan level: each plan task already has `files[]` — translate to agent task description | No runtime enforcement needed; plan structure is the boundary |
| Sync Direction | Memory -> TaskList (one-way bridge), not bidirectional | Simpler, avoids consistency issues; memory is the persistent source of truth |
| Agent Type | `general-purpose` subagent_type (has all tools: Read, Edit, Write, Bash, Grep, Glob) | Implementer needs full tool access to edit files and run commands |
| Concurrency Model | Parallel plans only (plan 01 tasks are independent); sequential across plans (plan 02 waits for 01) | Matches existing `blocks/blockedBy` in plan dependencies |
| Failure Handling | On verify failure: agent retries once, then notifies leader; leader can reassign or escalate | Matches `/implement` Step 2 pattern: "If stuck after 2 attempts, pause and ask user" |
| Session Persistence | Memory engine persists across sessions via JSONL; TaskList is ephemeral per team session | `/resume` rebuilds TaskList from memory state if team was previously active |

## Constraints

- Python stdlib only (no external dependencies)
- Must be backward compatible: `/implement` without teams works exactly as before
- Agent Teams is experimental — design must degrade gracefully if teams are unavailable
- Max 3-4 teammates per team (token cost scales linearly)
- Plan tasks are max 3 per plan (existing constraint)
- Each agent gets its own context window — cannot share live state except through TaskList/SendMessage

## Open Questions

- Should we create a dedicated `implementer` agent or reuse `general-purpose` with implement instructions in the task description?
- Should verify failures automatically create memory events or should the agent do it explicitly?
- Should we support mixed teams (implementer + reviewer in parallel) or keep implementation and review as separate phases?

## Related Code

- `scripts/memory/__init__.py` — Public API (create, ready, claim, close)
- `scripts/memory/storage.py` — SQLite operations, atomic claiming
- `scripts/memory/graph.py` — Dependency resolution, blocked cache
- `scripts/memory/sync.py` — JSONL export/import
- `scripts/memory/context.py` — Prime/context generation
- `.claude/commands/team.md` — Team command definition
- `.claude/commands/implement.md` — Implement command definition
- `.claude/commands/plan.md` — Plan command with memory integration
- `.claude/agents/*.md` — All 10 agent definitions

## Research References

- [Beads: A Git-Friendly Issue Tracker for AI Coding Agents](https://betterstack.com/community/guides/ai/beads-issue-tracker-ai-agents/)
- [OpenHands Refactor SDK: Automating Massive Refactors with Parallel Agents](https://openhands.dev/blog/automating-massive-refactors-with-parallel-agents)
- [Open SWE: An Open-Source Asynchronous Coding Agent](https://blog.langchain.com/introducing-open-swe-an-open-source-asynchronous-coding-agent/)
- [SERA: Soft-Verified Efficient Repository Agents](https://allenai.org/blog/open-coding-agents)
- [Agyn: Multi-Agent System for Team-Based Autonomous Software Engineering](https://arxiv.org/html/2602.01465)
- [Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams)
- [Claude Code System Prompts (Piebald-AI)](https://github.com/Piebald-AI/claude-code-system-prompts)
- [Claude Code Swarm Orchestration Skill](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea)
- [From Tasks to Swarms: Agent Teams in Claude Code](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/)
- [Claude-Flow: Agent Orchestration Platform](https://github.com/ruvnet/claude-flow)
- [Claude Code's Hidden Multi-Agent System](https://paddo.dev/blog/claude-code-hidden-swarm/)
- [AI Coding Agents in 2026: Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/)

---
*Discussed: 2026-02-14*
