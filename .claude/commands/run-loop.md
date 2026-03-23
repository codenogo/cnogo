# Run Loop
<!-- effort: high -->

Autonomous run loop supervisor. Dispatches features, spawns executors, monitors, releases lanes.

## Startup

Log `loop_started` event. Show `loop-status`.

## Main Loop

### 1. Dispatch
```bash
python3 .cnogo/scripts/workflow_memory.py dispatch-ready --json
```
Report autoQueued, leased, autoPlanned, autoReviewed, autoShipStarted, autoReleased.

### 2. Spawn executors

```bash
python3 .cnogo/scripts/workflow_memory.py lane-list --json
```

For each `implementing` lane with `currentRunId` and no active executor:
- Check `run-next <feature> --run-id <run-id> --json`
- If `begin_task` or `resolve_failure`: spawn executor as background agent:
```
Agent(subagent_type="executor", prompt="FEATURE=<f> RUN_ID=<r> WORKTREE=<w>\nDrive feature <f> to review-ready.", run_in_background=true, name="executor-<f>", mode="bypassPermissions")
```

CRITICAL: Use `mode="bypassPermissions"` so the executor can access the feature lane worktree and run commands without permission prompts. Do NOT use `isolation="worktree"` — it creates Claude Code-managed worktrees that conflict with cnogo's session-based merge system.
- Log `executor_spawned`. Track name to avoid duplicates.

### 3. Process completions

When background executor completes (notified automatically):
- Log `executor_finished` or `executor_error`
- `work-sync <feature>` to refresh Work Order
- Next dispatch tick handles auto-review/auto-ship

### 4. Tick

Show `loop-status`. Log `loop_tick`. Wait, then go to step 1.

Continue until no features in active states or user interrupts.

## Exit

Log `loop_finished`. Show final status + summary.

## Rules

- Supervisor dispatches and spawns — never implements.
- One executor per lane. Track active names to prevent duplicates.
- Executor failure → log + let next tick re-assess.
- Reviewing/shipping lanes handled by dispatch auto-review/auto-ship.
- Lane/run JSON is source of truth — keep supervisor state minimal.
- Log execution events for every action.
