# Shape: Autonomous Execution Loop

**Initiative**: autonomous-execution-loop
**Status**: Active

---

## Problem

The dispatcher leases features and auto-plans, but stops at "begin_task". Nobody picks up the work. After implementation, auto-review and auto-ship fire but git ops (commit/push/PR) are still manual. Completed lanes aren't released, occupying WIP slots. Shape-to-queue requires manual `work-sync`. The system prepares everything but doesn't execute.

## Architecture

Three-layer agent hierarchy. Always team mode — even single tasks spawn an agent.

### Layer 1: Supervisor (Claude session, long-running)
- Started via `/run-loop` or `/spawn run-loop`
- Scans SHAPE.json for ready candidates → auto-queues Work Orders
- Calls `dispatch_ready_work()` → leases features, creates worktrees, auto-plans
- Spawns one Executor agent per implementing lane (background)
- Gets notified when executors complete
- Advances transitions: auto-review, auto-ship, lane release
- Polls `loop-status` for health

### Layer 2: Executor (background Agent, one per feature lane)
- Enters feature worktree
- Reads task frontier (tasks where `blockedBy` all complete)
- Spawns one Implementer agent per runnable task (always team mode)
- Waits for all agents to return
- Calls `run-task-complete` or `run-task-fail` for each
- Merges task worktrees into feature branch (3-tier: clean → auto-resolve → resolver agent)
- Refreshes frontier → repeats until all tasks done
- Runs plan-verify
- Handles git ops when profile allows: commit, push, PR create
- Exits — supervisor detects completion

### Layer 3: Implementer (Agent, one per task)
- Existing `implementer.md` agent definition
- Works in isolated task worktree (branch per task)
- Reads task description + file scope + micro-steps
- Writes code, runs verify commands, commits to task branch
- Writes heartbeat file for liveness monitoring
- Returns result to executor

## Observability

### Execution Event Log (`.cnogo/execution-log.jsonl`)
Append-only JSONL. Every layer writes events:
- Supervisor: `loop_tick`, `feature_dispatched`, `executor_spawned`, `lane_released`
- Executor: `executor_started`, `agents_spawned`, `task_completed`, `task_failed`, `merge_completed`, `merge_conflict`, `plan_verify_passed`, `executor_finished`
- Implementer: `implementer_started`, `implementer_heartbeat`, `verify_passed`, `verify_failed`, `implementer_finished`

### CLI Commands
- `loop-status` — unified live view: WIP, lanes, tasks, agent status
- `loop-history` — recent event stream from execution-log.jsonl

### Heartbeat Files
Implementers write `.cnogo/agent-heartbeat-task-<N>.json` on each significant action. Executors poll these to detect stale agents. Threshold: configurable (default 15min).

### Patrol Integration
Existing patrol gains agent awareness: stale executor (lane heartbeat expired), stale implementer (heartbeat file expired), orphaned worktrees.

## What Gets Removed

- `/implement` command (replaced by executor)
- Serial execution path (always team)
- `recommend_team_mode()` (always team)
- `mode` field distinction on delivery runs (always "team")
- Manual `work-sync` for queueing (auto-queue from shape)
- Manual `dispatch-ready` (supervisor does it)
- Manual lane release (auto on ship complete)

## Constraints

- Python stdlib only
- Claude Code Agent tool for spawning (no subprocess management)
- Existing worktree merge strategy (3-tier) preserved
- Existing lane/dispatch/WIP infrastructure preserved
- Existing auto-review, auto-ship, patrol, feedback sync preserved
- Execution events are append-only (no mutation of execution log)

## Global Decisions

1. Always team mode — even single tasks get a spawned agent
2. Supervisor is a Claude session, not a Python process. Python owns state, Claude owns execution.
3. Two layers of agent spawning: feature-level (executor) and task-level (implementer)
4. Executor never writes code — purely orchestration. Implementers are the only code-writing agents.
5. Git ops (commit/push/PR) handled by executor when profile allows full auto-ship
6. Execution events are the observability primitive — all monitoring derives from the event log
