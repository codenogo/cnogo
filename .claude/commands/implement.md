# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan with per-task verification.

## Arguments

`/implement <feature> <plan-number> [--team]`

## Your Task

Execute the specified plan for `$ARGUMENTS`.

### Step 0: Branch Alignment

Implementation must run on `feature/<feature-slug>`.

```bash
git branch --show-current
git status --porcelain
```

Rules:
- If already on `feature/<feature-slug>`, continue.
- If switching branches is needed and working tree is dirty, stop and ask user to commit/stash first.
- If `feature/<feature-slug>` exists locally, switch to it.
- Else create it from default branch:

```bash
git switch main || git switch master
git pull --ff-only
git switch -c feature/<feature-slug>
```

### Step 1: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get <feature-slug>
```

Expected: `plan` or `implement`.

### Step 2: Load Plan Contracts

Read:
- `docs/planning/work/features/<feature>/<NN>-PLAN.json` (source of truth)
- `docs/planning/work/features/<feature>/<NN>-PLAN.md` (human context)

If missing, stop and list available plans.

### Step 2b: Memory Prep (Optional)

If memory is enabled:

```bash
python3 scripts/workflow_memory.py ready --feature <feature-slug>
python3 scripts/workflow_memory.py phase-set <feature-slug> implement
```

### Step 2c: Team Mode Routing

- If `--team` passed: delegate to `/team implement <feature> <plan-number>`.
- Else if plan has `"parallelizable": true` and Agent Teams available: delegate to `/team implement <feature> <plan-number>`.
- Else execute serially.

### Step 3: Execute Tasks

For each task in plan JSON:
1. announce task start
2. claim task memory ID if present
3. edit only listed files
4. run all task `verify[]` commands
5. on success: close memory ID if present
6. on failure: inspect history, fix, retry (max 2 attempts before escalation)

If task files touch memory sync/import paths (for example `scripts/memory/sync.py` or `.cnogo/issues.jsonl` flows), apply `.claude/skills/memory-sync-reconciliation.md`.

Retry helper commands:

```bash
python3 scripts/workflow_memory.py checkpoint --feature <feature-slug>
python3 scripts/workflow_memory.py history <memory-id>
```

### Step 4: Run Plan Verification

Run `planVerify[]` commands from plan JSON.
If passing and memory enabled:

```bash
python3 scripts/workflow_memory.py phase-set <feature-slug> review
```

### Step 5: Commit

```bash
git add -A
git commit -m "<commitMessage from plan>"
```

### Step 6: Write Summary Contract + Render

Create:
- `docs/planning/work/features/<feature>/<NN>-SUMMARY.json`

Minimum fields:
- `schemaVersion`, `feature`, `planNumber`, `outcome`, `changes[]`, `verification[]`, `commit`, `timestamp`

Then render markdown summary:

```bash
python3 scripts/workflow_render.py docs/planning/work/features/<feature>/<NN>-SUMMARY.json
```

Use `.claude/skills/workflow-contract-integrity.md` before final validation.

### Step 7: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Completed tasks and verification outcomes
- Commit hash/message
- Ready for `/review`
