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
3. Generate task descriptions via bridge (once — reuse for steps 4 and 5):
   ```bash
   python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory.bridge import plan_to_task_descriptions; from pathlib import Path; descs=plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<plan>-PLAN.json'), Path('.')); print(json.dumps(descs, indent=2))"
   ```
   Save the returned list as `task_descriptions` for subsequent steps.
4. Check file conflicts via `detect_file_conflicts(task_descriptions)`. **Advisory only** — if conflicts, warn: "File overlaps detected. Merge conflicts likely — resolver agent will handle." Proceed regardless (worktree isolation prevents runtime interference).
5. **Create worktree session** — pass the `task_descriptions` from step 3 (do NOT call `plan_to_task_descriptions` again):
   ```bash
   python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory import create_session; from pathlib import Path; root=Path('.'); session=create_session(Path('docs/planning/work/features/<feature>/<plan>-PLAN.json'), root, task_descriptions); print(json.dumps({'phase': session.phase, 'worktrees': len(session.worktrees)}))"
   ```
   Where `task_descriptions` is the list from step 3.
6. Create team `impl-<feature>-<plan>` via TeamCreate
7. Create TaskCreate entries — include the worktree path in each task description so agents know their working directory. Two-pass:
   - **Pass 1:** Create tasks for non-skipped items. Record `task_index_to_id` mapping (None for skipped).
   - **Pass 2:** Wire `blockedBy` dependencies via TaskUpdate `addBlockedBy`.
8. Spawn one `implementer` teammate per task via Task tool with `team_name`, `subagent_type: "general-purpose"`, and `model: "sonnet"`. The agent's prompt must include the implementer.md instructions and: "Your working directory is `<worktree_path>`. All file paths are relative to this directory."
9. Activate delegate mode. Monitor via TaskList until all tasks completed.
10. **Merge agent branches** — sequential merge in task order:
    ```bash
    python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory import load_session, merge_session; from pathlib import Path; root=Path('.'); session=load_session(root); result=merge_session(session, root); print(json.dumps({'success': result.success, 'merged': result.merged_indices, 'conflict_index': result.conflict_index, 'conflict_files': result.conflict_files}))"
    ```
11. **If merge conflict**: Spawn resolver agent (`.claude/agents/resolver.md`) with context from `get_conflict_context()`. After resolution, retry merge from where it left off. If resolver fails after 2 attempts, `git merge --abort` and report to user.
12. Run `planVerify` commands from plan JSON. Fix failures directly.
13. Create summary artifacts (`<NN>-SUMMARY.md` + `<NN>-SUMMARY.json`)
14. Commit: `git add -A && git commit -m "<commitMessage from plan>"`
15. **Cleanup worktrees** — remove worktrees, branches, and state file:
    ```bash
    python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import load_session, cleanup_session; from pathlib import Path; root=Path('.'); session=load_session(root); cleanup_session(session, root); print('Worktrees cleaned')"
    ```
16. Dismiss team, then `python3 scripts/workflow_validate.py`

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

- Agent Teams is a research preview — keep teams small (3-4 teammates) to limit coordination overhead and token cost
- Worktree state file (`.cnogo/worktree-session.json`) enables crash recovery — use `/resume` to detect interrupted sessions
- For single-agent work, use `/spawn` instead

## Output

Team composition, task list, and monitoring instructions.
