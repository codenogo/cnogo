# Compaction Resilience

## Problem

When Claude Code's context window compacts during multi-agent team work:
- Claude Code Task list is wiped (ephemeral, in-context only)
- Team config files persist on disk (orphaned)
- Memory engine issues stay open forever (no sync back from Task completion)
- Leader loses track of what agents completed

Evidence: After overstory-workflow-patterns Plan 03, all 4 memory issues (cn-12vmyu0 + children) show as "open" with only "created" events despite code being fully merged.

## Root Cause

The bridge between memory engine and Claude Code Tasks is **one-way**:
- Memory creates issues -> bridge generates prompts -> Claude Code Tasks track progress
- When Tasks complete, **nothing syncs back** to close memory issues
- Compaction wipes the leader's knowledge of what to clean up

## Solution: Four-Layer Defense

### Layer 1: Prompt Enforcement (soft)
Strengthen bridge prompt template: agents MUST `claim` at start, `close` at end. Not optional.

### Layer 2: SubagentStop Hook (hard)
When any agent process stops, hook parses stdin JSON for `agent_id`/`agent_type`, matches to worktree session, and auto-closes the corresponding memory issue.

### Layer 3: PreCompact Checkpoint
Before compaction wipes context, hook dumps ephemeral state to `.cnogo/compaction-checkpoint.json`:
- Team name, task states, agent-to-memory mappings
- Timestamp and trigger type (auto/manual)

### Layer 4: Session Reconcile (recovery)
`python3 scripts/workflow_memory.py session-reconcile` reads persistent state:
1. Worktree session file -> which tasks are merged/cleaned
2. Git log -> which branches were merged
3. Memory DB -> which issues are still open
Closes any orphaned open issues whose work is confirmed complete.

## Constraints

- All hooks < 3 seconds, exit 0 on failure
- Python stdlib only
- No PostCompact hook exists (recovery is on-demand)
- SubagentStop reads stdin JSON, not env vars

## Open Questions

1. How to reliably match SubagentStop agent_id to worktree session entries?
2. Should session-reconcile auto-run on SessionStart?
3. How to handle partially-completed agent work?

## Related Code

- `scripts/memory/bridge.py` — one-way bridge (memory -> Tasks)
- `scripts/memory/worktree.py` — session lifecycle
- `scripts/workflow_hooks.py` — existing hook handlers
- `.claude/settings.json` — hook configuration
