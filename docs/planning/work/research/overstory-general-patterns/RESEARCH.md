# Research: General Patterns in Overstory

**Topic:** Architectural and design patterns in the Overstory swarm orchestration system
**Date:** 2026-02-21
**Mode:** auto (repo + web)

## Context

[Overstory](https://github.com/jayminwest/overstory) (TypeScript/Bun, MIT) transforms a single Claude Code session into a multi-agent team. 8 agent roles, 2000+ tests, zero runtime dependencies. This research catalogs its general patterns — not just what cnogo can borrow, but how the system is designed end-to-end.

## Pattern Catalog

### 1. Strict Agent Hierarchy with Depth Enforcement

Agents are organized in a tree with enforced depth limits (default: 2):

| Depth | Role | Can Spawn | Write Access |
|-------|------|-----------|-------------|
| 0 | Coordinator | Leads only | None (read-only) |
| 1 | Supervisor/Lead | Workers | Specs only |
| 2 | Builder/Scout/Reviewer/Merger | Nothing | Scoped files only |

Attempting to violate the hierarchy (e.g., coordinator spawning a builder directly) throws a `HierarchyError`. This prevents runaway spawning and enforces separation of concerns.

### 2. Two-Layer Agent Definition (Base + Overlay)

Each agent receives instructions from two sources:

- **Base definition** (`agents/*.md`): Reusable workflow, constraints, named failure modes, communication protocol
- **Per-task overlay** (generated `CLAUDE.md` from template): Task ID, file scope, branch, parent identity

The overlay template (`templates/CLAUDE.md.tmpl`) injects `{{PROJECT_NAME}}`, `{{AGENT_DEFINITIONS}}`, and `{{CANONICAL_BRANCH}}`. This separates the "how to be a builder" knowledge from "what to build now."

### 3. Exclusive File Ownership (Non-Overlapping Scopes)

Every spawned agent receives an explicit `FILE_SCOPE` — the list of files it may modify. Two agents never share write access to the same file. Enforced at three levels:

1. **Spawn-time validation** via `overstory status` before dispatching
2. **PreToolUse hooks** that block writes outside scope
3. **Named failure mode** (`OVERLAPPING_FILE_SCOPE`) in agent definitions

This is the primary merge conflict prevention strategy, not the merge resolution system.

### 4. Named Failure Modes as Documentation

Each agent definition includes a table of anti-patterns with names and definitions:

- `PATH_BOUNDARY_VIOLATION` — writing outside worktree
- `PREMATURE_MERGE` — merging before `merge_ready` signal
- `HIERARCHY_BYPASS` — spawning wrong agent types
- `SILENT_ESCALATION_DROP` — ignoring escalation mail
- etc.

Naming failures makes them referenceable in monitoring, escalation, and post-mortems. This is a pattern cnogo adopted in `team.md` (e.g., "Do NOT use TaskOutput — foreground agents report via TaskList/SendMessage").

### 5. SQLite Mail Protocol (Typed, Persistent, Queryable)

Inter-agent communication uses a custom SQLite mail system (`.overstory/mail.db`, WAL mode):

- **8 message types**: `status`, `question`, `result`, `error`, `worker_done`, `merge_ready`, `merged`, `merge_failed`, `escalation`, `dispatch`, `assign`
- **Typed payloads**: Each message type has a structured payload (e.g., `WorkerDonePayload` includes exit code and modified files)
- **Broadcast addressing**: `@all`, `@builders` for group messages
- **Thread IDs** for conversation grouping
- **Persistence**: Messages survive agent restarts and are queryable for debugging

This replaces ephemeral tool-based messaging with an auditable communication layer.

### 6. Tiered Merge Conflict Resolution

Four escalation tiers, always starting from Tier 1:

1. **Clean merge** — `git merge`, no intervention
2. **Auto-resolve** — parse conflict markers, keep incoming for non-overlapping changes
3. **AI-resolve** — Claude reads both versions, synthesizes intent-preserving merge
4. **Reimagine** — start fresh, reimplement from both branches

Historical tracking (`ConflictHistory` type) records which tiers failed previously, enabling skip-ahead. Each merge is verified with tests before proceeding to the next branch in the queue.

### 7. Three-Tier Watchdog Monitoring

Progressive health monitoring with configurable thresholds:

- **Tier 0** (mechanical): Daemon checks tmux/PID liveness every 30s. Detects zombie processes.
- **Tier 1** (AI triage): Disabled by default. Would analyze stale agents with LLM assessment.
- **Tier 2** (Monitor agent): Long-running patrol agent with adaptive cadence (2min active, 5min idle). Tracks patterns like repeated stalls, silent completions, branch divergence.

Escalation protocol: warn → first nudge → second nudge → escalation → critical. Activity resets the counter.

### 8. Zero Runtime Dependencies

The entire system runs on Bun built-ins only:

- `bun:sqlite` for databases
- `Bun.spawn` for subprocess execution
- `Bun.file` for file I/O
- Custom minimal YAML parser instead of importing one

External CLIs (`git`, `tmux`, `bd`, `mulch`) are invoked as subprocesses, never as library dependencies. This mirrors cnogo's stdlib-only Python constraint.

### 9. Worktree-Per-Agent Isolation

Each agent operates in its own git worktree (`.overstory/worktrees/`), on its own branch (`overstory/<agent-name>/<bead-id>`). No agent touches the main working tree. Worktrees are created at spawn time and cleaned up after merge.

This is the mechanical foundation that enables parallelism — multiple agents can write to "the same repo" simultaneously without filesystem conflicts.

### 10. Propulsion Principle (Execute Immediately)

Every agent definition mandates immediate execution:

> "Read your assignment. Execute immediately. Do not ask for confirmation, do not propose a plan and wait for approval."

This prevents agents from entering conversational loops asking "should I proceed?" which waste tokens and time. Quality gates are the checkpoint, not human approval.

### 11. Typed Error Hierarchy

All errors extend `OverstoryError` with:

- Machine-readable `code` field (e.g., `HIERARCHY_VIOLATION`, `MERGE_ERROR`)
- Domain-specific context fields (e.g., `agentName`, `conflictFiles`)
- Cause chaining via `ErrorOptions`

Nine specialized error classes cover config, agent, hierarchy, worktree, mail, merge, validation, group, and lifecycle failures.

### 12. Layered Configuration with Migration

Config loads via three-layer merge: `DEFAULT_CONFIG` → `config.yaml` → `config.local.yaml` (gitignored). Post-merge validation checks types, ranges, cross-field dependencies. A `migrateDeprecatedWatchdogKeys()` function handles backward-compatible field renames.

### 13. Bead-Based Task Identity

Tasks are tracked as "beads" (issue-like objects) with IDs that decouple task tracking from agent lifecycle. Agents receive a bead ID at spawn, close it on completion. This means task state survives agent crashes — the bead remains open and can be reassigned.

### 14. Session Checkpoint and Handoff

Long-lived agents (coordinator, monitor) persist state via checkpoint files:

- `SessionCheckpoint`: Progress snapshot, modified files, pending work
- `SessionHandoff`: Explicit handoff record with reason

On restart, agents reload context from checkpoints rather than starting fresh. This enables continuity across Claude Code session boundaries.

### 15. Colocated Testing with Real Dependencies

Tests live alongside source (`feature.test.ts` next to `feature.ts`). Testing philosophy: **never mock what you can use for real**:

- Real filesystems via `mkdtemp`
- Real SQLite via `:memory:` databases
- Real git repos in temp directories
- Mocks only for tmux, API calls, and network operations

Shared helpers: `createTempGitRepo()`, `cleanupTempDir()`, `commitFile()`.

## Comparison with cnogo

| Pattern | Overstory | cnogo |
|---------|-----------|-------|
| Agent hierarchy | Code-enforced depth limits | Convention-based via `team.md` |
| Agent definitions | Two-layer (base + overlay) | Two-layer (agents/ + bridge prompt) |
| File ownership | PreToolUse hook enforcement | Advisory `detect_file_conflicts()` |
| Communication | SQLite mail, typed payloads | Claude Code native SendMessage |
| Merge resolution | 4-tier automatic escalation | Single-tier + resolver agent |
| Health monitoring | 3-tier watchdog + monitor agent | Config placeholder, no implementation |
| Dependencies | Zero (Bun built-ins) | Zero (Python stdlib) |
| Worktree isolation | Per-agent worktrees | Per-session worktrees |
| Task identity | Beads (persistent) | Memory engine issues (persistent) |
| Testing | Colocated, real deps | No test suite yet |
| Error handling | Typed hierarchy | Ad-hoc exceptions |

## Key Takeaways

1. **Prevention over resolution**: Non-overlapping file scopes prevent most merge conflicts mechanically; the 4-tier merge system is a safety net, not the primary strategy
2. **Named anti-patterns are documentation**: Giving failure modes names makes them referenceable and monitorable
3. **Immediate execution reduces waste**: The propulsion principle avoids token-expensive approval loops
4. **Typed communication enables debugging**: Structured mail with typed payloads creates an auditable trail
5. **Zero-dependency constraint forces simplicity**: Both projects independently converged on this pattern

## Open Questions

1. How does the system perform at scale? (STEELMAN.md warns about 5% error compounding per agent)
2. Is the SQLite mail system a net positive vs Claude Code's native messaging at small team sizes?
3. Does the reimagine tier (Tier 4 merge) produce correct results in practice?
