# Team: $ARGUMENTS
<!-- effort: high -->

Coordinate multi-agent work with explicit task boundaries and worktree sessions.

## Arguments

`/team create <task>`  
`/team implement <feature> <plan>`  
`/team status`  
`/team message <teammate> <msg>`  
`/team dismiss`

## Your Task

0. Verify Agent Teams is enabled in `.claude/settings.json` (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`).

1. Parse action from `$ARGUMENTS`.

## Action: `create`

1. Split request into specialized teammates (small team, clear file boundaries, no overlap).
2. Create team + tasks via TeamCreate/TaskCreate.
3. Spawn `general-purpose` teammates with relevant skill context.
4. If memory initialized, create an epic issue tagged `team`.

## Action: `implement`

1. Parse `<feature>` and `<plan>`.
2. If memory enabled, verify phase (`phase-get`) and confirm if not `plan`/`implement`.
3. Load `docs/planning/work/features/<feature>/<plan>-PLAN.json`.
4. Generate task descriptions once and persist to:
- `.cnogo/task-descriptions-<feature>-<plan>.json`
5. Run conflict check on persisted descriptions (`detect_file_conflicts`).
- Advisory only; continue with warning.
6. Create worktree session from persisted descriptions (do not regenerate descriptions).
7. If memory enabled, set phase to `implement`.
8. Create TaskCreate entries in two passes:
- Pass 1: create only non-skipped tasks, store `task_index_to_id` (`None` for skipped/closed).
- Pass 2: wire `blockedBy`; skip dependencies whose mapped id is `None`.
- If all dependencies are skipped/satisfied, leave task unblocked.
9. Spawn one implementer teammate per task; include exact worktree path in each prompt.
10. Monitor TaskList until complete.
11. Merge branches with session guard:
```bash
python3 scripts/workflow_memory.py session-merge --json
```
If merge conflict, run resolver agent and retry (max 2 attempts).
12. Run `planVerify` commands from plan JSON.
13. Write summary artifacts, commit, and set phase `review` (if memory enabled).
14. Cleanup:
```bash
python3 scripts/workflow_memory.py session-cleanup
python3 scripts/workflow_validate.py --json
```
15. Dismiss team.

## Action: `status`

Report active teammates, task states, blockers, and next unblock action.

## Action: `message`

Send teammate message and confirm delivery.

## Action: `dismiss`

Request teammate shutdown, wait for confirmation, then TeamDelete.

## Output

- Team state summary
- Task/blocker snapshot
- Any merge/conflict incidents and resolution status
