# Research: Borrowable Patterns from Overstory

**Topic:** What can cnogo borrow from the Overstory swarm orchestration system?
**Date:** 2026-02-21
**Mode:** auto (repo + web)

## Context

[Overstory](https://github.com/jayminwest/overstory) (v0.5.8, 362 stars) is a TypeScript/Bun CLI that turns a single Claude Code session into a multi-agent team using git worktrees, tmux, and SQLite messaging. It has 8 agent roles, 29 subcommands, and 1996 colocated tests.

cnogo is a Python stdlib-only workflow engine with a memory engine (SQLite + JSONL), hooks system, worktree isolation, skill library, and agent team coordination. Both projects solve similar problems with different architectures.

## Key Findings

### 1. SQLite Mail System (HIGH value, MEDIUM effort)

**What Overstory does:** A dedicated `messages` table with typed fields (from, to, subject, body, type, priority, thread_id, payload), WAL mode, and broadcast addressing (`@all`, `@builders`). Eight message types (worker_done, merge_ready, dispatch, escalation). Messages persist and can be queried/threaded.

**What cnogo has:** No inter-agent messaging. Teams rely on Claude Code's native `SendMessage` tool which is ephemeral and has no queryable history.

**Borrowable pattern:** A lightweight SQLite mail table in `.cnogo/memory.db` would give agents persistent, queryable communication history. Thread IDs enable conversation grouping. Broadcast groups (`@reviewers`) map directly to cnogo's `defaultCompositions`.

**Risk:** Over-engineering for current team sizes (2-4 agents). Claude Code's native messaging may be sufficient for coordination.

### 2. Tiered Merge Conflict Resolution (HIGH value, LOW effort)

**What Overstory does:** Four-tier escalation: clean-merge -> auto-resolve (keep incoming) -> AI-resolve (Claude `--print`) -> reimagine (rewrite from both versions). Tracks which tiers historically failed to skip them. Records outcomes for learning.

**What cnogo has:** Sequential merge with conflict detection, manual escalation to resolver agent. No automatic resolution tiers, no historical tracking.

**Borrowable pattern:** Add tiers 1-2 (clean merge + auto-resolve-keep-incoming) to `worktree.py:merge_session()` before escalating to the resolver agent. Track `resolvedTier` per merge in session state. This catches 60-80% of conflicts mechanically.

**Risk:** Auto-resolve (keep incoming) silently discards base changes. Safe only when agents work on disjoint files, which cnogo's `detect_file_conflicts()` already validates.

### 3. Watchdog / Agent Health Monitoring (HIGH value, MEDIUM effort)

**What Overstory does:** Three-tier monitoring: mechanical daemon (tmux/pid checks) -> AI-assisted triage -> Monitor agent patrol. Progressive escalation: warn -> nudge -> escalate -> terminate. Configurable thresholds (stale, zombie).

**What cnogo has:** `staleIndicatorMinutes: 10` in config but no implementation. No heartbeat, no liveness detection, no timeout enforcement. Agents can hang silently.

**Borrowable pattern:** A lightweight `watchdog.py` that: (a) polls worktree session state for stale `in_progress` tasks, (b) checks if agent output file is growing, (c) escalates after configurable thresholds. Does NOT need tmux/daemon complexity since cnogo agents are Claude Code subprocesses.

**Risk:** False positives on legitimately slow tasks. Mitigate with task-type-specific thresholds.

### 4. Transcript-Based Cost Tracking (MEDIUM value, LOW effort)

**What Overstory does:** Parses `~/.claude/projects/{slug}/{session}.jsonl` transcripts. Extracts input/output/cache tokens per turn. Calculates cost using model-specific pricing (Opus $15/$75, Sonnet $3/$15, Haiku $0.80/$4 per M tokens). Per-agent cost attribution.

**What cnogo has:** Token estimation via `len(text)//4`. Command-level savings tracking. No per-agent cost, no actual API cost, no model-aware pricing.

**Borrowable pattern:** Add a `costs.py` module that reads Claude Code session transcripts (JSONL) and computes actual cost per agent. Surface in `/team status` and post-run summaries. Enables "this feature cost $X across N agents" reporting.

**Risk:** Transcript format is Claude Code internal; may change without notice. Keep the parser defensive.

### 5. Doctor Diagnostics Module (MEDIUM value, LOW effort)

**What Overstory does:** 9 health check modules covering git, tmux, SQLite, permissions, disk space. Single `overstory doctor` command runs all checks with pass/fail/warn output.

**What cnogo has:** `workflow_validate.py` checks contracts and freshness. Invariant checks via `entropy`. Memory sync reconciliation skill. But no unified "run everything" diagnostic.

**Borrowable pattern:** A `/doctor` command that sequentially runs: (a) `workflow_validate.py`, (b) memory DB integrity check (`PRAGMA integrity_check`), (c) orphaned worktree detection, (d) stale issue scan (open >30 days), (e) hook config sanity. Single pass/fail summary.

**Risk:** Minimal. This is additive and non-breaking.

### 6. Two-Layer Agent Definitions (LOW value, already exists)

**What Overstory does:** Base `.md` files define agent workflows; per-task overlays customize scope, files, and constraints.

**What cnogo has:** Already has this pattern: base agents in `.claude/agents/` + per-task prompts generated by `memory/bridge.py:generate_implement_prompt()`. No change needed.

### 7. Capability-Based Access Control (LOW value, HIGH effort)

**What Overstory does:** PreToolUse hooks mechanically restrict file modifications for non-implementation agents (scouts, reviewers are read-only).

**What cnogo has:** Hooks scan for secrets and optimize commands but don't enforce read-only access per agent role.

**Borrowable pattern:** Could add role-based write restrictions, but Claude Code's native permission model already handles this via `subagent_type` (Explore agents can't edit). Not worth custom enforcement.

## Recommendation

**Adopt immediately (next sprint):**
1. **Tiered merge resolution** (tiers 1-2 only) in `worktree.py` -- low effort, high win rate on mechanical conflicts
2. **Doctor command** -- unify existing diagnostics into single entry point
3. **Transcript cost tracking** -- enables cost-per-feature visibility

**Adopt after validation:**
4. **Agent health monitoring** -- build lightweight watchdog for stale task detection after confirming hang frequency justifies it

**Skip:**
- SQLite mail system (Claude Code native messaging is sufficient at current scale)
- Capability-based access control (already covered by Claude Code's agent type system)
- Full 4-tier merge (tiers 3-4 add AI calls that compound cost; current resolver agent covers this)

## Open Questions

1. How often do cnogo agents actually hang in practice? (Check `.cnogo/command-usage.jsonl` for long gaps)
2. What's the current merge conflict rate? (Would tiered resolution actually save time?)
3. Are Claude Code transcript JSONL files stable enough to parse reliably?

## Overstory's Own Warnings

Their STEELMAN.md documents critical risks: error rate multiplication (5% per agent compounds), cost amplification (20-agent run: $60 vs $9 sequential), architectural drift from fragmented context, and debugging complexity across distributed logs. Their conclusion: **single-agent workflows outperform swarms for interconnected work**. Swarms only justified for truly independent tasks.

This aligns with cnogo's conservative approach: small-batch plans (max 3 tasks), advisory file conflict detection, and sequential merge ordering.
