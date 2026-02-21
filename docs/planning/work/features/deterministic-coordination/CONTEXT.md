# Deterministic Coordination

Redesign multi-agent coordination to be deterministic, role-enforced, and safe.

## Problem

The current workflow has fundamental flaws:

- **Workers close shared issues** — task agents (and SubagentStop hook) close plans/epics that other agents depend on
- **SubagentStop hook is over-scoped** — regex-scans all `cn-*` IDs from messages and closes everything it finds
- **No ownership boundaries** — no enforcement that only the leader can mutate coordination objects
- **State model is ambiguous** — binary open/closed causes reopen loops and "already closed" conflicts
- **Team lifecycle isn't deterministic** — cleanup is best-effort, causing "Already leading team" deadlocks
- **Validation has no baseline** — "warnings are pre-existing" is asserted without a diff

## Contracts

### 01: Object Types + Ownership

- `Issue.type` mandatory enum: `EPIC | PLAN | TASK`
- `Issue.owner_actor` mandatory for TASK (single owner), leader-owned for PLAN/EPIC
- Hierarchy: EPIC > PLAN > TASK

### 02: Roles + Permissions

- `ActorRole = LEADER | WORKER | HOOK`
- **WORKER**: may only set `TASK.state = DONE_BY_WORKER` and add outputs/comments
- **HOOK**: same as WORKER but only for current worker's owned TASKs
- **LEADER**: may set VERIFIED, CLOSED, close PLANs/EPICs, run reconciliation
- Enforced in `close()` / `transition()` — not just convention

### 03: State Model

- `Issue.state` with type-specific machines:
  - **TASK**: `OPEN -> IN_PROGRESS -> DONE_BY_WORKER -> VERIFIED -> CLOSED`
  - **PLAN**: `OPEN -> READY_TO_CLOSE -> CLOSED`
  - **EPIC**: `OPEN -> READY_TO_CLOSE -> CLOSED`
- `status=CLOSED` only when `state=CLOSED`
- `close_reason` becomes structured enum + optional note

### 04: Two-Phase Completion

- **Phase A (Worker)**: `report_done(task_id, outputs)` — sets `DONE_BY_WORKER`, attaches outputs, cannot close
- **Phase B (Leader)**: `verify_and_close(task_id)` — sets `VERIFIED` then `CLOSED` (or reopens with reason)
- Workers never close shared things

### 05: Kill Auto-Close-Parent

- Remove "if all children closed then close parent" logic from `close()`
- Parent closure belongs exclusively in leader reconciliation
- No more cascade: worker closes task -> parent epic closes -> leader reopens -> wasted time

### 06: SubagentStop Hook Behavior

- Hook must **never close anything**
- May only call `report_done()` for TASKs matching: `type=TASK` AND `owner_actor == current_agent`
- Stop regex-scanning `cn-*` IDs from messages
- Require structured footer from workers: `TASK_DONE: [cn-123, cn-456]`

### 07: Team Lifecycle

- Leader wraps entire run in `try/finally` with guaranteed `TeamDelete`
- Unique team name per run: `impl-<feature>-<run_id>`
- Persist `team_id` in run ledger so compaction/restarts don't orphan teams

### 08: Leader Reconciliation

- **Only** component allowed to close PLAN/EPIC objects
- Deterministic algorithm:
  1. Load EPIC -> PLANs -> TASKs
  2. For each TASK: if `DONE_BY_WORKER` and checks pass -> `VERIFIED` -> `CLOSED`
  3. For each PLAN: if all TASKs closed -> `READY_TO_CLOSE` -> `CLOSED`
  4. EPIC: if all PLANs closed -> `READY_TO_CLOSE` -> `CLOSED`

### 09: Validation Baseline

- Persist baseline per branch/run: `.cnogo/validate-baseline.json`
- Leader reports diffs only: new warnings, resolved warnings, unchanged
- Store warnings by stable signature (rule id + file + line)

### 10: Token + Compaction Optimization

- **Run ledger** at `.cnogo/run.json` — single-file coordination state
  - Schema: `run_id`, `phase`, `team_id`, `issue_ids`, `states`, `outputs_hash`
  - Leader can restart any time by reading 1 file and reconciling
- **Minimal worker context** — workers never get full history, only:
  - Task ID
  - Acceptance criteria
  - Files
  - `"report_done, don't close"`
- Survives compaction/restart — no orphaned teams or lost state

## Related Code

| File | Role |
|------|------|
| `scripts/memory/__init__.py` | Core memory API (`close()`, `create()`, `claim()`) |
| `scripts/memory/models.py` | `Issue` data model (needs `type`, `state`, `owner_actor`) |
| `scripts/memory/bridge.py` | Plan-to-task bridge (generates worker prompts with close instructions) |
| `scripts/hook-subagent-stop.py` | SubagentStop hook (currently closes everything) |
| `scripts/workflow_memory.py` | CLI wrapper for memory engine |
| `scripts/workflow_validate.py` | Validation runner (needs baseline support) |
| `.claude/agents/implementer.md` | Worker agent definition (tells workers to close) |
| `.claude/commands/implement.md` | Serial implementation flow (no try/finally) |
| `.claude/commands/team.md` | Team coordination flow (best-effort cleanup) |
| `.claude/settings.json` | Hook registrations |

## Constraints

- Python stdlib-only (no external deps)
- SQLite + JSONL sync format
- Max 3 tasks per plan
- All state transitions enforced in Python API
- SubagentStop hook < 3 seconds
- Must migrate existing `issues.jsonl` data

## Open Questions

1. Migration strategy for existing issues lacking `type`/`state`/`owner_actor` fields
2. `close_reason` enum values beyond `completed`
