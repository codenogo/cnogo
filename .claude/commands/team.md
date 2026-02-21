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
4. Generate run_id and team name:
```python
from scripts.memory.bridge import generate_run_id, plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts
run_id = generate_run_id(feature)
team_name = f"impl-{feature}-{run_id}"
```
5. Generate TaskDescV2 list via bridge and persist as versioned wrapper:
```python
tasks = plan_to_task_descriptions(plan_json_path, root)
wrapper = {"schema_version": 2, "feature": feature, "plan_number": plan, "generated_at": now, "tasks": tasks}
# Persist to .cnogo/task-descriptions-<feature>-<plan>.json
```
6. Run conflict check (`detect_file_conflicts(tasks)`). Advisory only; continue with warning.
7. Create worktree session from V2 task descriptions (pass `run_id=run_id`).
8. If memory enabled, set phase to `implement`.
9. Create TaskCreate entries (two-pass: create tasks, then wire blockedBy).
10. Spawn one implementer per task. At spawn-time, render prompt:
```python
prompt = generate_implement_prompt(taskdesc)  # TaskDescV2 → markdown
```
Include worktree path in prompt.

**Guaranteed lifecycle — try/finally structure:**
```
try:
  11. Monitor TaskList until all tasks complete.
  12. Run leader reconciliation:
      python3 -c "from scripts.memory.reconcile_leader import reconcile; print(reconcile('<epic_id>'))"
  13. Merge branches: `python3 scripts/workflow_memory.py session-merge --json`
      If conflict, run resolver agent (max 2 retries).
  14. Run planVerify commands.
  15. Write summary artifacts, commit, set phase `review`.
finally:
  16. Cleanup (guaranteed teardown — MUST execute even if tasks fail):
      python3 scripts/workflow_memory.py session-cleanup
      python3 scripts/workflow_validate.py --json
  17. Dismiss team via TeamDelete. If TeamDelete fails, retry once then log and continue.
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
