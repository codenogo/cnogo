# Run Loop
<!-- effort: high -->

Autonomous supervisor. Dispatches ready features, spawns executor agents, monitors completions, advances the assembly line.

## Startup

Show current state:
```bash
python3 .cnogo/scripts/workflow_memory.py loop-status
```

Initialize an empty tracking dict for active executors: `active_executors = {}` (feature → agent name).

## Main Loop

Repeat steps 1–4 until no features remain in dispatchable states or the user interrupts.

### Step 1: Dispatch ready features

```bash
python3 .cnogo/scripts/workflow_memory.py dispatch-ready --json
```

Parse the JSON output carefully. This command:
- Leases ready features into lanes (creates worktrees)
- Auto-plans features that need plans (creates plan contracts + delivery runs)
- Reports what it did

From the output, extract:
- `leased` array → newly leased features with `feature`, `laneId`, `worktreePath`
- `autoPlanned` array → features that got plans with `feature`, `planNumber`, `deliveryRun.runId`
- `reclaimed` array → stale lanes that were reclaimed
- `skipped` array → features that couldn't be dispatched (and why)

Report a one-line summary: `Dispatch: leased=N auto-planned=N reclaimed=N skipped=N`

### Step 2: Spawn executors for ready lanes

```bash
python3 .cnogo/scripts/workflow_memory.py lane-list --json
```

Parse the JSON. For EACH lane where:
- `phase` is `implementing` (or was just leased/planned)
- `currentRunId` exists
- The feature is NOT in `active_executors`

Do the following:

a. Check if there's work to do:
```bash
python3 .cnogo/scripts/workflow_memory.py run-next <feature> --json
```

Parse `nextAction.kind`:
- `begin_task` or `resolve_failure` → spawn an executor (proceed to b)
- `run_plan_verify` → spawn an executor (it handles verification)
- `complete` or `start_review` or `start_ship` → skip, lane is done
- `blocked` or `wait` → skip, report why

b. Set phase to implement:
```bash
python3 .cnogo/scripts/workflow_memory.py phase-set <feature> implement
```

c. Spawn the executor as a background agent:
```
Agent(
  subagent_type="executor",
  prompt="FEATURE=<feature> RUN_ID=<currentRunId> WORKTREE=<worktreePath>\nDrive feature <feature> to review-ready.",
  run_in_background=true,
  name="executor-<feature>",
  mode="bypassPermissions",
  description="Execute <feature>"
)
```

Add to tracking: `active_executors[feature] = "executor-<feature>"`

CRITICAL rules:
- `run_in_background=true` — supervisor must not block on a single feature
- `mode="bypassPermissions"` — executors need unblocked file access
- Do NOT use `isolation="worktree"` — cnogo manages worktrees at `.cnogo/feature-worktrees/`
- Do NOT set `model` — executor.md specifies sonnet
- One executor per lane. Never spawn duplicates.

Spawn ALL ready executors in a SINGLE message with multiple Agent tool calls (parallel launch).

Report: `Spawned executors: <feature1>, <feature2>, ...`

### Step 3: Process completions

When a background executor completes (you will be notified automatically — do NOT poll or sleep):

a. Remove from `active_executors`

b. Check the delivery run state:
```bash
python3 .cnogo/scripts/workflow_memory.py run-show <feature> --json
```

c. Sync the work order:
```bash
python3 .cnogo/scripts/workflow_memory.py work-sync <feature>
```

d. Report the result:
- If all tasks done + planVerify passed → `<feature>: review-ready`
- If tasks failed → `<feature>: FAILED — <details>`
- If planVerify failed → `<feature>: verify FAILED`

e. The next dispatch tick (step 1) will auto-advance review/ship phases.

### Step 4: Tick

Show loop status:
```bash
python3 .cnogo/scripts/workflow_memory.py loop-status
```

Check if there are still features in active states (implementing, reviewing, shipping).
- If yes → go back to Step 1
- If no active features AND no active executors → exit

Between ticks, do NOT sleep. Process executor completions as they arrive. Only go back to Step 1 when an executor completes or when all executors are running and a new dispatch might find more work.

## Exit

Show final summary:
```bash
python3 .cnogo/scripts/workflow_memory.py loop-status
python3 .cnogo/scripts/workflow_memory.py work-list --json
```

Report:
```
Run Loop Complete
  Features processed: N
  Succeeded: <list>
  Failed: <list>
  Still active: <list>
```

## Rules

- The supervisor dispatches and spawns — it NEVER writes application code.
- One executor per lane. Track active names to prevent duplicates.
- Executor failure → log, let next tick re-assess (dispatch-ready handles reclamation).
- Lane/run JSON is the source of truth — keep supervisor state minimal.
- If dispatch-ready returns nothing and no executors are active, the loop is done.
- NEVER fall back to ad-hoc coding if the pipeline fails. Report the failure.
- Spawn multiple executors in parallel when multiple features are ready.
