# Git Worktree Integration for Multi-Agent Parallel Execution — Implementation Context

## Summary

Replace the current shared-directory parallel execution model with git worktree isolation. Each agent gets its own worktree and branch. Merge conflicts are resolved by a dedicated resolver agent (opus). A state file enables crash recovery at any phase.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Integration | Replace shared-dir mode entirely | Simpler mental model — one parallel execution strategy. Worktrees provide hard filesystem isolation, eliminating silent overwrites. Shared-dir mode's "ONLY touch listed files" convention is fragile. |
| Conflict resolution | Agent-assisted (opus resolver) | Resolver agent has MORE context than a human — it reads both task descriptions (intent) + conflict markers. Opus model for reasoning about three-way merges. Falls back to user on failure. |
| Escalation on failure | Abort conflicting merge + user decides | `git merge --abort` on the failing branch only. Preserve all successfully merged branches. User can: resolve manually, re-run task against new base, or skip. No wasted work. |
| Recovery model | State file + /resume | `.cnogo/worktree-session.json` checkpoints every phase transition. `/resume` detects interrupted worktree sessions and offers: retry, clean up, or continue from last checkpoint. |
| Module location | New `scripts/memory/worktree.py` | Bridge stays a pure translator (zero side effects). Worktree module owns all git operations, filesystem management, and state file. Clean separation of concerns. |
| Memory coordination | Symlink `.cnogo/` | Each worktree gets `ln -s <main>/.cnogo <worktree>/.cnogo`. All agents share one SQLite file. WAL mode handles concurrent reads. Single writer (claim/close) with retry. |
| Resolver model | opus | Conflict resolution requires understanding both sides' intent and producing correct merges. Conflicts are rare but high-stakes — worth the cost. |
| Branch naming | `agent/<feature>-<plan>-task-<N>` | e.g., `agent/ws-notif-01-task-0`. Readable, namespaced, includes enough context to identify purpose. |
| Worktree location | Sibling directories | `../<project>-wt-<feature>-<plan>-<N>/`. Keeps main repo clean. Standard convention across ecosystem (ccswarm, parallel-cc, incident.io). |
| `detect_file_conflicts()` | Advisory only (no longer a gate) | With worktrees, file overlap doesn't block parallel execution — it surfaces at merge time instead. Conflict detection warns "expect merge conflicts" but proceeds. |

## Architecture

### Phase Model (State Machine)

```
INIT → SETUP → EXECUTING → AGENTS_COMPLETE → MERGING → MERGED → VERIFIED → COMMITTED → CLEANED
```

Each transition is checkpointed in `.cnogo/worktree-session.json`.

### Worktree Lifecycle

```
Phase 1: SETUP
  ├── Record base commit + branch
  ├── Create branch per task (agent/<feature>-<plan>-task-<N>)
  ├── Create worktree per task (git worktree add)
  ├── Symlink .cnogo/ in each worktree
  └── Write state file

Phase 2: EXECUTING
  ├── Spawn implementer agent per worktree
  ├── Agents work independently (claim → implement → verify → close)
  ├── Each agent commits to its own branch
  └── Update state file as agents complete

Phase 3: MERGING
  ├── Sequential merge in task order
  ├── For each branch:
  │   ├── git merge --no-ff agent/branch-N
  │   ├── If clean → update state, continue
  │   └── If conflict:
  │       ├── Read conflicted files + both task descriptions
  │       ├── Spawn resolver agent (opus)
  │       ├── Resolver edits, removes markers, runs verify from BOTH tasks
  │       ├── If resolved → git add + git commit → continue
  │       └── If unresolvable (2 attempts) → git merge --abort, report, pause
  └── Update state file after each merge

Phase 4: POST-MERGE
  ├── Run planVerify commands
  ├── Commit (or amend merge commits into single commit)
  ├── Create summary artifacts
  ├── Remove worktrees (git worktree remove)
  ├── Delete agent branches (git branch -d)
  └── Remove state file
```

### Failure Recovery Matrix

| Interrupted during | State file says | Recovery action |
|---|---|---|
| Setup | `phase: "setup"` | Clean up partial worktrees, retry from scratch |
| Execution | `phase: "executing"` | Re-spawn failed agents into existing worktrees |
| Merge (clean) | `phase: "merging"`, `mergedSoFar: [0,1]` | Continue merging from next unmerged branch |
| Merge (conflict) | `phase: "merging"`, task status `"conflict"` | Re-attempt resolution or abort + report |
| Verification | `phase: "merged"` | Re-run planVerify |
| Commit | `phase: "verified"` | Just commit |
| Cleanup | `phase: "committed"` | Remove remaining worktrees |

### State File Schema

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "planNumber": "01",
  "baseCommit": "abc123",
  "baseBranch": "main",
  "phase": "executing",
  "worktrees": [
    {
      "taskIndex": 0,
      "name": "Task name",
      "branch": "agent/ws-notif-01-task-0",
      "path": "../cnogo-wt-ws-notif-01-0",
      "status": "created|executing|completed|merged|conflict|cleaned",
      "memoryId": "cn-xxx.1",
      "conflictFiles": []
    }
  ],
  "mergeOrder": [0, 1, 2],
  "mergedSoFar": [],
  "timestamp": "2026-02-14T00:00:00Z"
}
```

### New Files

| File | Purpose |
|------|---------|
| `scripts/memory/worktree.py` | Worktree lifecycle primitives: create, merge, cleanup, load_session |
| `.claude/agents/resolver.md` | Resolver agent definition (opus, conflict resolution specialist) |

### Modified Files

| File | Change |
|------|--------|
| `scripts/memory/__init__.py` | Export worktree functions |
| `scripts/memory/bridge.py` | `detect_file_conflicts()` returns advisory severity level; `generate_implement_prompt()` adds worktree-aware instructions |
| `.claude/commands/team.md` | `implement` action uses worktrees instead of shared-dir |
| `.claude/commands/implement.md` | Step 1c updated — worktrees replace shared-dir parallel mode |
| `.claude/commands/resume.md` | Step 3b detects interrupted worktree sessions |
| `scripts/workflow_validate.py` | Validate worktree-session.json schema |
| `docs/planning/WORKFLOW.json` | Add worktree config under `agentTeams` |

## Constraints

- Python stdlib only — `subprocess.run(["git", "worktree", ...])` for git operations
- No concurrent SQLite writers — WAL mode + retry pattern for claim/close contention
- Branch exclusivity — git prevents checking out same branch in two worktrees (use unique branches)
- Each worktree duplicates the working tree on disk (not object store) — plan for disk space
- Resolver agent uses opus model — higher cost per conflict, but conflicts should be rare

## Open Questions

- Should we limit worktree count (e.g., max 5) to prevent disk/resource exhaustion?
- Should the resolver agent have access to git log for historical context on conflicted files?
- Should worktree cleanup happen immediately after merge or defer to end of session?
- How to handle the case where git worktree is unavailable (old git version, shallow clone)?

## Related Code

- `scripts/memory/bridge.py` — current plan→task translator, detect_file_conflicts()
- `.claude/commands/team.md` — current team orchestration (Steps 4-11 change)
- `.claude/commands/implement.md` — Step 1c team mode detection
- `.claude/commands/resume.md` — Step 3b recovery (needs worktree session awareness)
- `.claude/agents/implementer.md` — agent definition (largely unchanged, runs in worktree)
- `scripts/memory/storage.py` — SQLite operations (WAL mode for concurrent access)

## Research

- `docs/planning/work/research/subagent-context-patterns/RESEARCH.md` — references Git Town worktree isolation pattern
- Ecosystem tools: ccswarm, parallel-cc, ccpm, git-worktree-runner all use worktrees for agent isolation
- Claude Code Swarm Mode (Feb 2026) uses worktrees internally
- Anthropic C compiler project (16 parallel agents) used similar isolation with Docker containers

---
*Discussed: 2026-02-14*
