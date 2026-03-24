# Implement: $ARGUMENTS
<!-- effort: high -->

Single-feature execution entry point. Dispatches the feature, creates a delivery run, spawns an executor agent, and tracks the full lifecycle.

## Parse

Extract `<feature>` from `$ARGUMENTS`. If empty, show usage and stop:
```
Usage: /implement <feature>
```

## Step 1: Dispatch the feature

```bash
python3 .cnogo/scripts/workflow_memory.py dispatch-ready --feature <feature> --json
```

Parse the JSON output. This command does everything in one call:
- Leases the feature into a lane (creates worktree)
- Auto-plans if no plan exists (creates plan contract)
- Creates a delivery run

Extract from the output:
- `leased[0].worktreePath` → `WORKTREE`
- `leased[0].laneId` → `LANE_ID`
- `autoPlanned[0].deliveryRun.runId` → `RUN_ID`
- `autoPlanned[0].planNumber` → `PLAN_NUMBER`

If the feature was already dispatched (empty `leased`, empty `autoPlanned`), fall back:

a. Check for an existing lane:
```bash
python3 .cnogo/scripts/workflow_memory.py lane-show <feature> --json
```
If a lane exists, extract `worktreePath` and `currentRunId`.

b. If NO lane exists but the feature has a delivery run (check `work-show`), ensure one:
```bash
python3 .cnogo/scripts/workflow_memory.py lane-ensure <feature> --json
```
Extract `worktreePath` from the output.

c. If the feature has no delivery run at all, auto-plan first:
```bash
python3 .cnogo/scripts/workflow_memory.py plan-auto <feature> --json
```
Then ensure a lane with `lane-ensure` as in step b.

If dispatch fails entirely (feature not found, dependencies unmet, held by circuit breaker), report the error and stop. Do NOT proceed without a valid lane and delivery run.

## Step 2: Verify the delivery run has tasks

```bash
python3 .cnogo/scripts/workflow_memory.py run-next <feature> --json
```

Parse `nextAction.kind`:
- `begin_task` → tasks are ready, proceed to step 3
- `run_plan_verify` → plan already executed, proceed to step 3 (executor will handle)
- `blocked` → report what's blocking and stop
- `complete` → feature already done, report and stop
- anything else → report the state and stop

Also note `nextAction.taskIndices` — this tells you how many tasks are in the frontier.

## Step 3: Set phase to implement

```bash
python3 .cnogo/scripts/workflow_memory.py phase-set <feature> implement
```

## Step 4: Spawn the executor agent

```bash
python3 .cnogo/scripts/workflow_memory.py run-show <feature> --json
```

Use the `runId` from run-show output (authoritative source).

Spawn the executor:
```
Agent(
  subagent_type="executor",
  prompt="FEATURE=<feature> RUN_ID=<runId> WORKTREE=<worktreePath>\nDrive feature <feature> to review-ready.",
  run_in_background=false,
  name="executor-<feature>",
  mode="bypassPermissions",
  description="Execute <feature>"
)
```

CRITICAL rules for the Agent spawn:
- `run_in_background=false` — wait for the executor to finish so we can process results
- `mode="bypassPermissions"` — executor needs file access in the worktree without prompts
- Do NOT use `isolation="worktree"` — cnogo manages its own worktrees at `.cnogo/feature-worktrees/`
- Do NOT set `model` — let the executor agent definition control this (it uses sonnet for cost efficiency)

## Step 5: Process executor results

When the executor returns, check the result for success or failure indicators.

Run post-execution status:
```bash
python3 .cnogo/scripts/workflow_memory.py run-show <feature> --json
```

Parse the run state:
- If all tasks are `done` and `planVerify` passed → success
- If any tasks `failed` → report failures with details
- If `planVerify` failed → report verification failure

Then sync the work order:
```bash
python3 .cnogo/scripts/workflow_memory.py work-sync <feature>
```

## Step 6: Report results

Show a summary table:

```
Feature: <feature>
Phase: implement → review (or current state)
Delivery Run: <runId>
Tasks: N/N complete
Plan Verify: pass/fail
```

If successful, suggest next steps:
- `/review` to review the feature
- `/implement <next-feature>` to continue the assembly line

If failed, show what went wrong and suggest remediation.

## Rules

- NEVER write application code yourself. The executor and implementers do that.
- NEVER skip dispatch. Always go through dispatch-ready first.
- NEVER proceed without a valid delivery run.
- If dispatch-ready or run-next fails, diagnose and report — do not fall back to ad-hoc coding.
- The memory engine is the source of truth for all state.
- Log execution events for traceability.
