# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan with verification.

## Arguments

`/implement <feature> <plan-number> [--team] [--serial]`

## Steps

1. **Branch**
   - Check `git branch --show-current` and `git status --porcelain`.
   - Work on `feature/<feature-slug>`. Missing branch: stop and send the user back to `/discuss`. Dirty branch: stop before switching.

2. **Load contracts**
   - Run `python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>`; expected phase: `plan` or `implement`.
   - Read `docs/planning/work/features/<feature>/<NN>-PLAN.json` and docs.
   - If memory is enabled, run `ready --feature <feature-slug>` and `phase-set <feature-slug> implement`.
   - Build TaskDescV2 via `plan_to_task_descriptions(plan_path, root)` and call `recommend_team_mode(taskdescs)`.
   - Create or resume a Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-create <feature-slug> <NN> [--mode auto|serial|team] --json`.
   - Keep the returned `runId`; the run persists at `.cnogo/runs/<feature>/<run-id>.json` and is the source of truth.
   - Team-first default: `--serial` stays serial; otherwise `--team` or `recommended=true` routes to `/team implement`.

3. **Execute each task**
   - Skip tasks marked `skipped`.
   - Follow `micro_steps` in order and honor `tdd`.
   - If `task_id` exists, run `python3 .cnogo/scripts/workflow_memory.py claim <task-id> --actor implementer`.
   - Mark the task `in_progress` with `python3 .cnogo/scripts/workflow_memory.py run-task-set <feature-slug> <task-index> in_progress --assignee implementer`.
   - Edit only files in `task["file_scope"]["paths"]`.
   - Run all task verify commands from TaskDescV2, including the auto-appended package `lint` / `typecheck` / `test` commands from `WORKFLOW.json`.
   - `graph-validate-scope` is optional.
   - On success, run `python3 .cnogo/scripts/workflow_memory.py report-done <task-id> --actor implementer`; on failure, checkpoint, inspect history, fix, and retry twice.
   - After success, mark the task `done` with `python3 .cnogo/scripts/workflow_memory.py run-task-set <feature-slug> <task-index> done`.
   - Workers never close issues. Use `TASK_DONE: [cn-xxx, ...]` when needed.
   - Use `run-refresh` after manual intervention. Use `run-show` for `integration` plus `reviewReadiness`.
   - In serial mode, checkpoint and re-read before starting the next task.

4. **Plan verification**
   - Run all `planVerify[]` commands.
   - Record the gate outcome on the Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify <feature-slug> pass --run-id <run-id> [--command "<cmd>"]...`.
   - If verification fails, record `run-plan-verify <feature-slug> fail ...` before stopping. If it passes and memory is enabled, run `phase-set <feature-slug> review`.

5. **Commit**
   - `git add -A`
   - `git commit -m "<commitMessage from plan>"`

6. **Summary + validation**
   - Generate summary artifacts with `python3 .cnogo/scripts/workflow_checks.py summarize --feature <feature-slug> --plan <NN>`.
   - `summarize` writes both `<NN>-SUMMARY.json` and `<NN>-SUMMARY.md`; optional overrides are `--outcome partial|failed` and repeated `--note "<context>"`.
   - Apply `.claude/skills/workflow-contract-integrity.md`.
   - Run `python3 .cnogo/scripts/workflow_validate.py --feature <feature-slug>`.

## Output

- task outcomes
- commit hash and message
- ready for `/review`
