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
3. Spawn teammates with deterministic specialization->skill mapping from `/spawn`.
4. For architecture/contract-heavy tasks, include `.claude/skills/workflow-contract-integrity.md` in lead or reviewer prompts.
5. For safety-critical tasks, include `.claude/skills/boundary-and-sdk-enforcement.md`.
6. If memory initialized, create an epic issue tagged `team`.

## Action: `implement`

1. Parse `<feature>` and `<plan>`.
2. If memory enabled, verify phase (`phase-get`) and confirm if not `plan`/`implement`.
3. Load `docs/planning/work/features/<feature>/<plan>-PLAN.json`.
4. Generate unique team name: `impl-<feature>-<run_id>` where run_id = `generate_run_id(feature)`.
5. Create run ledger immediately after TeamCreate:
```python
from scripts.memory.ledger import create_ledger, generate_run_id, update_ledger
```
6. Generate task descriptions once and persist to `.cnogo/task-descriptions-<feature>-<plan>.json`.
7. Run conflict check (`detect_file_conflicts`). Advisory only; continue with warning.
8. Create worktree session from persisted descriptions.
9. If memory enabled, set phase to `implement`. Update ledger phase to `running`.
10. Create TaskCreate entries (two-pass: create tasks, then wire blockedBy).
11. Spawn one implementer teammate per task; include worktree path in prompt.

**Guaranteed lifecycle — try/finally structure:**
```
try:
  12. Monitor TaskList until all tasks complete.
  13. Update ledger phase to `reconciling`.
  14. Run leader reconciliation:
      python3 -c "from scripts.memory.reconcile_leader import reconcile; print(reconcile('<epic_id>'))"
  15. Merge branches: `python3 scripts/workflow_memory.py session-merge --json`
      If conflict, run resolver agent (max 2 retries).
  16. Run planVerify commands.
  17. Write summary artifacts, commit, set phase `review`.
  18. Update ledger phase to `done`.
finally:
  19. Cleanup (guaranteed teardown — MUST execute even if tasks fail):
      python3 scripts/workflow_memory.py session-cleanup
      python3 scripts/workflow_validate.py --json
  20. Update ledger phase to `failed` if not already `done`.
  21. Dismiss team via TeamDelete. If TeamDelete fails, retry once then log and continue.
```

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
