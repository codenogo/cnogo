# Team: $ARGUMENTS
<!-- effort: high -->

Coordinate multi-agent work with explicit task boundaries and worktree sessions.

## Arguments

`/team create <task>`  
`/team implement <feature> <plan>`  
`/team status`  
`/team message <teammate> <msg>`  
`/team dismiss`

Verify Agent Teams is enabled in `.claude/settings.json` (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`), then parse the action from `$ARGUMENTS`.

## Action: `create`

1. Split request into specialized teammates (small team, clear file boundaries, no overlap).
2. Create team + tasks via TeamCreate/TaskCreate.
3. Spawn teammates with deterministic specialization->skill mapping from `/spawn`.
4. Add `.claude/skills/workflow-contract-integrity.md` for contract-heavy work and `.claude/skills/boundary-and-sdk-enforcement.md` for safety-critical work.
5. If memory is initialized, create an epic issue tagged `team`.

## Action: `implement`

1. Parse `<feature>` and `<plan>`. Verify phase (`phase-get`).
2. Load plan JSON. Generate run_id via `bridge.generate_run_id(feature)`.
3. Generate TaskDescV2 list via `bridge.plan_to_task_descriptions()`. Run `recommend_team_mode()` plus `detect_file_conflicts()`; stop if team mode was forced onto an unsafe plan.
4. Create worktree session. Set phase to `implement`.
5. Create TaskCreate entries (two-pass: create, then wire blockedBy).
6. Spawn one implementer per task via `bridge.generate_implement_prompt(taskdesc, actor_name=...)`.
   Leader is orchestration-only: do not execute task implementation or verify commands.
   Require footer protocol: `TASK_EVIDENCE: {...}` then `TASK_DONE: [cn-...]`.

**Guaranteed lifecycle — try/finally:**
```
try:
  7. Monitor TaskList. Poll stalls via `workflow_memory.py stalled`.
     For stalled tasks: takeover + spawn replacement implementer.
  8. Leader reconciliation via `reconcile_leader.reconcile(epic_id)`.
  9. Merge branches: `workflow_memory.py session-merge`. Resolver agent on conflict (max 2 retries).
  10. Run planVerify, then `/review` staged gate. Stop if `fail`.
  11. Commit the merged result, then run `python3 .cnogo/scripts/workflow_checks.py summarize --feature <feature> --plan <NN>`.
  12. Set phase `review`.
finally:
  13. Cleanup: `workflow_memory.py session-cleanup` + `workflow_validate.py`.
  14. Dismiss team via TeamDelete.
```

## Action: `status`

Report teammates, blockers, and next unblock action.

## Action: `message`

Send teammate guidance.

## Action: `dismiss`

Request teammate shutdown, wait for confirmation, then TeamDelete.

## Output

- Team state summary
- Task/blocker snapshot
- Any merge/conflict incidents and resolution status
