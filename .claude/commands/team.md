# Team: $ARGUMENTS
<!-- effort: high -->

Orchestrate Agent Teams for collaborative multi-agent workflows.

## Arguments

`/team <action> [args]`

| Action | Usage | Purpose |
|--------|-------|---------|
| `create` | `/team create <task-description>` | Create a team for a task |
| `implement` | `/team implement <feature> <plan>` | Execute a plan in parallel |
| `status` | `/team status` | Show progress |
| `message` | `/team message <teammate> <msg>` | Message a teammate |
| `dismiss` | `/team dismiss` | Shut down teammates |

## Your Task

### Step 0: Verify Agent Teams Enabled

Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is `"1"` in `.claude/settings.json`. If not, inform the user.

### Step 1: Parse Action

Extract action and arguments from "$ARGUMENTS". First word = action, remaining = args.

### Step 2: Execute Action

#### Action: `create`

1. Analyze the task to determine needed specializations
2. Create team via TeamCreate, create tasks via TaskCreate
3. Spawn `general-purpose` teammates with relevant `.claude/skills/` loaded via `skills` frontmatter
4. Assign file boundaries to prevent merge conflicts — no two teammates edit the same file
5. Activate delegate mode (Shift+Tab) — lead coordinates, doesn't code
6. If memory initialized, create an epic and subtasks:
   ```bash
   python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import is_initialized, create; from pathlib import Path; root=Path('.'); epic=create('<description>', issue_type='epic', labels=['team'], root=root) if is_initialized(root) else None; print(f'Epic: {epic.id}') if epic else None"
   ```

#### Action: `implement`

1. Parse `<feature>` and `<plan>` from arguments
2. Load `docs/planning/work/features/<feature>/<plan>-PLAN.json`
3. Generate task descriptions via bridge:
   ```bash
   python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory.bridge import plan_to_task_descriptions; from pathlib import Path; print(json.dumps(plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<plan>-PLAN.json'), Path('.')), indent=2))"
   ```
4. Check file conflicts via `detect_file_conflicts()`. If conflicts, warn and suggest serial `/implement` instead.
5. Create team `impl-<feature>-<plan>` via TeamCreate
6. Create TaskCreate entries (two-pass):
   - **Pass 1:** Create tasks for non-skipped items. Record `task_index_to_id` mapping (None for skipped).
   - **Pass 2:** Wire `blockedBy` dependencies via TaskUpdate `addBlockedBy`.
7. Spawn one `implementer` teammate per task via Task tool with `team_name` and `subagent_type: "general-purpose"`
8. Activate delegate mode. Monitor via TaskList until all tasks completed.
9. Run `planVerify` commands from plan JSON. Fix failures directly.
10. Create summary artifacts (`<NN>-SUMMARY.md` + `<NN>-SUMMARY.json`)
11. Commit: `git add -A && git commit -m "<commitMessage from plan>"`
13. Dismiss team, then `python3 scripts/workflow_validate.py`

#### Action: `status`

1. Read team config, show TaskList with status
2. Report: active teammates, completed/blocked tasks, recommended actions

#### Action: `message`

Parse teammate name and message, send via SendMessage, confirm delivery.

#### Action: `dismiss`

Send shutdown_request to each teammate, wait for confirmations, TeamDelete, report final status.

### Step 3: Report

```markdown
## Team Status

**Team:** [name] | **Teammates:** [count]

| Teammate | Status | Current Task |
|----------|--------|-------------|
| [name] | [active/idle/done] | [task] |

### Task List
| ID | Task | Owner | Status | Blocked By |
|----|------|-------|--------|------------|
```

## Notes

- Agent Teams is a research preview — one team per session, no resumption
- Keep teams small (3-4 teammates) — more increases coordination overhead and token cost
- For single-agent work, use `/spawn` instead

## Output

Team composition, task list, and monitoring instructions.
