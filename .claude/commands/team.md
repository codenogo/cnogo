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
2. Create or resume the Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-create <feature> <NN> --mode team --json`.
   Use the returned `runId` and `recommendation` as the supported team-execution source of truth.
3. Create TaskCreate entries, then wire blockedBy.
4. Use `python3 .cnogo/scripts/workflow_memory.py run-next <feature> --run-id <run-id> --json` to find the current frontier.
5. Generate worker prompts with `python3 .cnogo/scripts/workflow_memory.py run-task-prompt <feature> <task-index> --run-id <run-id> [--actor <name>]`.
   Do not import `bridge.*` directly in the operator flow.
6. Spawn one implementer per runnable task. Leader is orchestration-only. Require `TASK_EVIDENCE` then `TASK_DONE`.
   Workers must not commit, push, create PRs, or stage repo-wide changes. The leader owns merge, commit, push, and ship.
7. Monitor TaskList and poll stalls via `workflow_memory.py stalled`; takeover and respawn as needed.
8. Keep the Delivery Run current as tasks move through `ready`, `in_progress`, `done`, `merged`, or `failed`. Use `python3 .cnogo/scripts/workflow_memory.py run-sync-session <feature> --run-id <run-id> --json` after worker progress or merge changes.
9. Reconcile, merge with `workflow_memory.py session-merge`, resolve conflicts (max 2 retries), then record planVerify with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify <feature> pass|fail --run-id <run-id> [--command "<cmd>"]...`.
10. If verification passed but review is still blocked on integration state, run `python3 .cnogo/scripts/workflow_memory.py run-review-ready <feature> --run-id <run-id>`.
11. Commit, summarize, set phase `review` when ready, then cleanup with `workflow_memory.py session-cleanup` + `workflow_validate.py` and dismiss the team.

## Action: `status`

Report teammates, blockers, Work Order state, Delivery Run state, Integration state, Review readiness, next action.
Use `python3 .cnogo/scripts/workflow_memory.py session-status --json` as the primary source when a worktree session exists.
Also inspect `python3 .cnogo/scripts/workflow_memory.py work-list --needs-attention --json` or `run-watch-patrol --feature <feature>` if stalled.

## Action: `message`

Send teammate guidance.

## Action: `dismiss`

Shutdown teammates, wait, then TeamDelete.
