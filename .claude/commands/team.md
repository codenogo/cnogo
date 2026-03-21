# Team: $ARGUMENTS
<!-- effort: high -->

## Arguments

`/team create <task>`  
`/team implement <feature> <plan>`  
`/team status`  
`/team message <teammate> <msg>`  
`/team dismiss`

Verify Agent Teams is enabled, then parse `$ARGUMENTS`.

## Action: `create`

1. Split request into specialized teammates.
2. Create team + tasks via TeamCreate/TaskCreate.
3. Spawn teammates via `/spawn`.
4. If memory is initialized, create an epic tagged `team`.

## Action: `implement`

1. Parse `<feature>` and `<plan>`. Verify phase.
2. Load plan JSON. Generate run_id via `bridge.generate_run_id(feature)`.
3. Generate TaskDescV2 via `bridge.plan_to_task_descriptions()`. Run `recommend_team_mode()` plus `detect_file_conflicts()`; stop if team mode was forced onto an unsafe plan.
4. Create or resume the Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-create <feature> <NN> --mode team --run-id <run-id> --json`.
   Persist it under `.cnogo/runs/<feature>/<run-id>.json`, sync the feature Work Order, create the worktree session with the same `run_id`, and set phase `implement`.
5. Create TaskCreate entries, then wire blockedBy.
6. Spawn one implementer per task via `bridge.generate_implement_prompt(taskdesc, actor_name=...)`. Leader is orchestration-only. Require `TASK_EVIDENCE` then `TASK_DONE`.
7. Monitor TaskList and poll stalls via `workflow_memory.py stalled`; takeover and respawn as needed.
8. Keep the Delivery Run current as tasks move through `ready`, `in_progress`, `done`, `merged`, or `failed`. Use `python3 .cnogo/scripts/workflow_memory.py run-sync-session <feature> --run-id <run-id> --json` after worker progress or merge changes.
9. Reconcile, merge with `workflow_memory.py session-merge`, resolve conflicts (max 2 retries), then record planVerify with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify <feature> pass|fail --run-id <run-id> [--command "<cmd>"]...`.
10. Commit, summarize, set phase `review`, then cleanup with `workflow_memory.py session-cleanup` + `workflow_validate.py` and dismiss the team.

## Action: `status`

Report teammates, blockers, Work Order state, Delivery Run state, Integration state, Review readiness, next action.
Use `python3 .cnogo/scripts/workflow_memory.py session-status --json` as the primary source when a worktree session exists.
Also inspect `python3 .cnogo/scripts/workflow_memory.py work-list --needs-attention --json` or `run-watch-patrol --feature <feature>` if stalled.

## Action: `message`

Send teammate guidance.

## Action: `dismiss`

Shutdown teammates, wait, then TeamDelete.
