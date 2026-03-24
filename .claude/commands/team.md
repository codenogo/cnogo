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
   Use the returned `runId` and `recommendation` as the source of truth.
3. Create TaskCreate entries, then wire blockedBy.
4. Use `python3 .cnogo/scripts/workflow_memory.py run-next <feature> --run-id <run-id> --json` to find the current frontier.
5. Generate worker prompts with `python3 .cnogo/scripts/workflow_memory.py run-task-prompt <feature> <task-index> --run-id <run-id> [--actor <name>]`.
6. Spawn one implementer per runnable task. Leader is orchestration-only. Require `TASK_EVIDENCE` then `TASK_DONE`.
   Workers must not commit, push, create PRs, or stage repo-wide changes. The leader owns merge, commit, push, and ship.
7. Monitor TaskList and poll stalls via `workflow_memory.py stalled`; takeover and respawn as needed.
8. Keep the Delivery Run current as tasks move through `ready`, `in_progress`, `done`, `merged`, or `failed`. Use `python3 .cnogo/scripts/workflow_memory.py run-sync-session <feature> --run-id <run-id> --json` after worker progress or integration.
9. Apply worker outputs with `python3 .cnogo/scripts/workflow_memory.py session-apply --json`. Use `session-merge` only for older commit-based worker branches. Resolve conflicts before continuing.
10. For runtime smoke checks, prefer `python3 .cnogo/scripts/workflow_memory.py verify-import <module> [symbol...]`.
11. Record planVerify with `python3 .cnogo/scripts/workflow_memory.py run-plan-verify <feature> pass|fail --run-id <run-id> --use-plan-verify [--command "<cmd>"]...`.
12. If verification passed but review is still blocked on integration state, run `python3 .cnogo/scripts/workflow_memory.py run-review-ready <feature> --run-id <run-id>`.
13. Commit, summarize, set phase `review`, run `workflow_memory.py session-cleanup`, validate, and dismiss the team.

## Action: `status`

Report teammates, blockers, Work Order state, Delivery Run state, Integration state, Review readiness, and next action.
Use `python3 .cnogo/scripts/workflow_memory.py session-status --json` as the primary source when a worktree session exists.
Also inspect `python3 .cnogo/scripts/workflow_memory.py work-list --needs-attention --json` or `run-watch-patrol --feature <feature>` if stalled.

## Action: `message`

Send teammate guidance.

## Action: `dismiss`

Shutdown teammates, wait, then TeamDelete.

## Anti-Patterns

- **No TaskOutput**: foreground agents report via TaskList/SendMessage auto-delivery. TaskOutput targets background/remote sessions only.
- **No composite IDs** (`name@team_name`): Claude Code uses opaque system-generated task IDs; composites cause "No task found" errors.
- **No `isolation: "worktree"` on Agent spawns**: Claude Code's sandbox bounds file access to the main checkout. `isolation: "worktree"` creates a separate worktree that cnogo can't merge, and `bypassPermissions` doesn't extend the sandbox. Instead, implementers work in the main checkout (within sandbox); the executor copies changes to the feature worktree and commits there.
- **No manual `git worktree remove`**: `session-cleanup` runs `cleanup_session()` with `--force`, covering modified files and branch deletion.
