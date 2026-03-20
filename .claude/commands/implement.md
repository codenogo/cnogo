# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan with verification.

## Arguments

`/implement <feature> <plan-number> [--team] [--serial]`

## Steps

1. **Branch**
   - Check `git branch --show-current` and `git status --porcelain`.
   - Work must run on `feature/<feature-slug>`.
   - If the branch exists but the tree is dirty, stop before switching.
   - If the branch is missing, stop and tell the user to run `/discuss` first.

2. **Load contracts**
   - Run `python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>`; expected phase is `plan` or `implement`.
   - Read `docs/planning/work/features/<feature>/<NN>-PLAN.json` and `NN-PLAN.md`.
   - If memory is enabled, run `python3 .cnogo/scripts/workflow_memory.py ready --feature <feature-slug>` and `phase-set <feature-slug> implement`.
   - Build TaskDescV2 objects via `plan_to_task_descriptions(plan_path, root)`.
   - Call `recommend_team_mode(taskdescs)`.
   - Team-first default: `--serial` stays serial; otherwise `--team` or `recommended=true` routes to `/team implement`.
   - Treat `parallelizable: true` as a hint only; actual routing comes from dependency frontier + file-scope safety.

3. **Execute each task**
   - Skip tasks marked `skipped`.
   - Follow `micro_steps` in order and honor the `tdd` contract.
   - If `task_id` exists, run `python3 .cnogo/scripts/workflow_memory.py claim <task-id> --actor implementer`.
   - Edit only files in `task["file_scope"]["paths"]`.
   - Run all task verify commands from TaskDescV2, including the auto-appended package `lint` / `typecheck` / `test` commands inferred from `WORKFLOW.json`.
   - Optional `python3 .cnogo/scripts/workflow_memory.py graph-validate-scope ...` is advisory.
   - On success, run `python3 .cnogo/scripts/workflow_memory.py report-done <task-id> --actor implementer`; on failure, checkpoint, inspect history, fix, and retry up to 2 times before stopping.
   - Workers never close issues. Use footer `TASK_DONE: [cn-xxx, ...]` when needed.
   - In serial mode, checkpoint and re-read before starting the next task.

4. **Plan verification**
   - Run all `planVerify[]` commands.
   - If they pass and memory is enabled, run `python3 .cnogo/scripts/workflow_memory.py phase-set <feature-slug> review`.

5. **Commit**
   - `git add -A`
   - `git commit -m "<commitMessage from plan>"`

6. **Summary + validation**
   - Generate summary artifacts with `python3 .cnogo/scripts/workflow_checks.py summarize --feature <feature-slug> --plan <NN>`.
   - Optional overrides: `--outcome partial|failed` and repeated `--note "<context>"`.
   - `summarize` writes both `<NN>-SUMMARY.json` and `<NN>-SUMMARY.md` from execution evidence.
   - Apply `.claude/skills/workflow-contract-integrity.md`.
   - Run `python3 .cnogo/scripts/workflow_validate.py --feature <feature-slug>`.

## Output

- task outcomes
- commit hash and message
- ready for `/review`
