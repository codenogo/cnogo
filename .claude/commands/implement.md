# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan with per-task verification.

## Arguments

`/implement <feature> <plan-number> [--team]`

## Your Task

Execute the specified plan for `$ARGUMENTS`.

### Step 0: Branch Verification (verify-only — do NOT create)

Implementation must run on `feature/<feature-slug>`. The branch should already exist from `/discuss`.

```bash
git branch --show-current
git status --porcelain
```

Rules:
- If already on `feature/<feature-slug>`, continue.
- If `feature/<feature-slug>` exists locally but is not the current branch:
  - If working tree is dirty, stop and ask user to commit/stash first.
  - Else switch to it and pull latest: `git switch feature/<feature-slug> && git pull --ff-only`
- If `feature/<feature-slug>` does **not** exist, stop and tell the user to run `/discuss <feature-name>` first to create the branch.

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

### Step 2d: Bridge Validation

Generate TaskDescV2 list via bridge for validation and memory bootstrapping:

```python
from scripts.memory.bridge import plan_to_task_descriptions
from pathlib import Path
tasks = plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<NN>-PLAN.json'), Path('.'))
```

This validates blockedBy indices, creates memory issues if needed, and skips already-closed tasks on resume.

### Step 3: Execute Tasks (TaskDescV2)

For each task in the TaskDescV2 list from Step 2d:
1. skip if `task['skipped']` is true
1b. announce task start, review Operating Principles (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution)
2. if `task['task_id']` present, run `python3 scripts/workflow_memory.py claim <task_id> --actor implementer`
3. execute `task['action']`, editing only files in `task['file_scope']['paths']`
4. run all `task['commands']['verify']` commands
5. on success if task_id present: run `python3 scripts/workflow_memory.py report-done <task_id> --actor implementer`
6. on failure: inspect history, fix, retry (max 2 attempts before escalation)

**Important:** Workers NEVER close memory issues — only report done. The leader handles closure.
After all tasks, include each task's `completion_footer` in a combined footer: `TASK_DONE: [cn-xxx, cn-yyy]`

If task files touch memory sync/import paths, apply `.claude/skills/memory-sync-reconciliation.md`.

Retry helper commands:

```bash
python3 scripts/workflow_memory.py checkpoint --feature <feature-slug>
python3 scripts/workflow_memory.py history <task_id>
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
