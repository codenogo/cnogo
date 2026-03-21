# Implement: $ARGUMENTS
<!-- effort: medium -->

Execute a plan.

## Arguments

`/implement <feature> <plan-number> [--team] [--serial]`

## Steps

1. **Branch**
   - Check `git branch --show-current` and `git status --porcelain`.
   - Must be on `feature/<feature-slug>`. Otherwise stop.

2. **Load contracts**
   - Run `python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>`; expected phase `plan|implement`.
   - Read `docs/planning/work/features/<feature>/<NN>-PLAN.json`.
   - If memory is enabled, run `ready --feature <feature-slug>` and `phase-set <feature-slug> implement`.
   - Build TaskDescV2 and call `recommend_team_mode(taskdescs)`.
   - Resolve the plan profile from `NN-PLAN.json` or `WORKFLOW.json.profiles.default`.
   - Create or resume a Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-create <feature-slug> <NN> [--mode auto|serial|team] --json`.
   - Keep the returned `runId`; the run persists at `.cnogo/runs/<feature>/<run-id>.json`.
   - Optional: inspect `python3 .cnogo/scripts/workflow_memory.py work-show <feature-slug> --json`.
   - `--serial` stays serial; otherwise `--team` or `recommended=true` uses `/team implement`.

3. **Execute each task**
   - Use `python3 .cnogo/scripts/workflow_memory.py run-next <feature-slug> --run-id <run-id> --json`; trust returned `nextAction`.
   - In serial mode, `run-plan-verify` absorbs integration.
   - Follow `micro_steps` and honor `tdd`.
   - Preferred start path: `python3 .cnogo/scripts/workflow_memory.py run-task-begin <feature-slug> <task-index> --run-id <run-id> --actor implementer`.
   - Edit only files in `task["file_scope"]["paths"]`.
   - Run all task verify commands from TaskDescV2, including the auto-appended package `lint` / `typecheck` / `test` commands from `WORKFLOW.json`.
   - Preferred completion path: `python3 .cnogo/scripts/workflow_memory.py run-task-complete <feature-slug> <task-index> --run-id <run-id> [--command "<verify>"]...`.
   - If the task is blocked or regresses, record it with `python3 .cnogo/scripts/workflow_memory.py run-task-fail <feature-slug> <task-index> --run-id <run-id> --error "<summary>"`.
   - Use `run-refresh` after manual intervention. Use `run-show` for `integration` plus `reviewReadiness`.

4. **Plan verification**
   - Run all `planVerify[]` commands.
   - Record the gate outcome on the Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify <feature-slug> pass --run-id <run-id> --use-plan-verify [--command "<cmd>"]...`.
   - If verification fails, record `run-plan-verify <feature-slug> fail ...` before stopping.
   - If verification passes but `reviewReadiness.status` is still not `ready`, finalize it with `python3 .cnogo/scripts/workflow_memory.py run-review-ready <feature-slug> --run-id <run-id>`.

5. **Commit**
   - `git add -A`
   - `git commit -m "<commitMessage from plan>"`

6. **Summary + validation**
   - Generate summary artifacts with `python3 .cnogo/scripts/workflow_checks.py summarize --feature <feature-slug> --plan <NN>`.
   - Before handoff, run `python3 .cnogo/scripts/workflow_memory.py run-watch-patrol --feature <feature-slug>`.
   - Confirm the feature-level Work Order is current with `python3 .cnogo/scripts/workflow_memory.py work-next <feature-slug> --json`.
   - Apply `.claude/skills/workflow-contract-integrity.md`.
   - Run `python3 .cnogo/scripts/workflow_validate.py --feature <feature-slug>`.

## Output

- task outcomes
- commit hash and message
- Delivery Run + Work Order state
- ready for `/review`
