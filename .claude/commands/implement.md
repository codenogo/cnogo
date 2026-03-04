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

**Step 0a: Clean up merged branches**

```bash
git branch --merged main | grep -v '^\*\|main' | xargs -r git branch -d
git remote prune origin
```

Report deleted branches if any.

### Step 1: Phase Check (Warn, Do Not Block)

```bash
python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>
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
python3 .cnogo/scripts/workflow_memory.py ready --feature <feature-slug>
python3 .cnogo/scripts/workflow_memory.py phase-set <feature-slug> implement
```

### Step 2c: Team Mode Routing

If `--team` or plan `"parallelizable": true`: delegate to `/team implement`. Falls back to serial on failure.

### Step 2d: Bridge Validation

Generate TaskDescV2 list via bridge (`plan_to_task_descriptions(plan_path, root)`).
Validates blockedBy indices, creates memory issues if needed, skips already-closed tasks on resume.

### Step 3: Execute Tasks (TaskDescV2)

For each task in the TaskDescV2 list:
1. Skip if `task['skipped']`. Announce start, review Operating Principles.
2. Execute `micro_steps` in order; respect `tdd` contract (no time boxes).
3. If `task_id` present: `workflow_memory.py claim <task_id> --actor implementer`
4. Execute `task['action']`, editing only files in `task['file_scope']['paths']`.
5. Run all verify commands; run `graph-validate-scope` (advisory, don't block).
6. No success claims without fresh evidence.
7. On success: `workflow_memory.py report-done <task_id> --actor implementer`
8. On failure: checkpoint, inspect history, fix, retry (max 2). After 2 failures, stop and report.
9. On partial completion: ensure report-done entries and checkpoint saved.

Workers NEVER close memory issues — only report done. Combined footer: `TASK_DONE: [cn-xxx, cn-yyy]`
Retry helpers: `workflow_memory.py checkpoint --feature <slug>` / `history <task_id>`.

### Step 4: Run Plan Verification

Run `planVerify[]` commands from plan JSON.
If passing and memory enabled:

```bash
python3 .cnogo/scripts/workflow_memory.py phase-set <feature-slug> review
```

### Step 5: Commit

```bash
git add -A
git commit -m "<commitMessage from plan>"
```

### Step 6: Write Summary Contract + Render

Create `<NN>-SUMMARY.json` (`schemaVersion`, `feature`, `planNumber`, `outcome`, `changes[]`, `verification[]`, `commit`, `timestamp`).
Render with `workflow_render.py`. Apply `.claude/skills/workflow-contract-integrity.md` before validation.

### Step 7: Validate

```bash
python3 .cnogo/scripts/workflow_validate.py --feature <feature-slug>
```

## Output

- Completed tasks and verification outcomes
- Commit hash/message
- Ready for `/review`
