# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan with per-task verification.

## Arguments

`/implement <feature> <plan-number> [--team]`

## Your Task

Execute the specified plan for `$ARGUMENTS`.

### Step 0: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get <feature-slug>
```

Expected: `plan` or `implement`.

### Step 1: Load Plan Contracts

Read:
- `docs/planning/work/features/<feature>/<NN>-PLAN.json` (source of truth)
- `docs/planning/work/features/<feature>/<NN>-PLAN.md` (human context)

If missing, stop and list available plans.

### Step 1b: Memory Prep (Optional)

If memory is enabled:

```bash
python3 scripts/workflow_memory.py ready --feature <feature-slug>
python3 scripts/workflow_memory.py phase-set <feature-slug> implement
```

### Step 1c: Team Mode Routing

- If `--team` passed: delegate to `/team implement <feature> <plan>`.
- Else if plan has `"parallelizable": true` and Agent Teams available: delegate to `/team implement`.
- Else execute serially.

### Step 2: Execute Tasks

For each task in plan JSON:
1. announce task start
2. claim task memory ID if present
3. edit only listed files
4. run all task `verify[]` commands
5. on success: close memory ID if present
6. on failure: inspect history, fix, retry (max 2 attempts before escalation)

Retry helper commands:

```bash
python3 scripts/workflow_memory.py checkpoint --feature <feature-slug>
python3 scripts/workflow_memory.py history <memory-id>
```

### Step 3: Run Plan Verification

Run `planVerify[]` commands from plan JSON.
If passing and memory enabled:

```bash
python3 scripts/workflow_memory.py phase-set <feature-slug> review
```

### Step 4: Commit

```bash
git add -A
git commit -m "<commitMessage from plan>"
```

### Step 5: Write Summary Contract + Render

Create:
- `docs/planning/work/features/<feature>/<NN>-SUMMARY.json`

Minimum fields:
- `schemaVersion`, `feature`, `planNumber`, `outcome`, `changes[]`, `verification[]`, `commit`, `timestamp`

Then render markdown summary:

```bash
python3 scripts/workflow_render.py docs/planning/work/features/<feature>/<NN>-SUMMARY.json
```

### Step 6: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Completed tasks and verification outcomes
- Commit hash/message
- Ready for `/review`
