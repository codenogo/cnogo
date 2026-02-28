# Plan 02: Command Integration

## Goal
Wire the bridge module into `/team` and `/implement` commands so users can run `/team implement <feature> <plan>` to spawn a parallel implementation team.

## Prerequisites
- [ ] Plan 01 complete (bridge module + implementer agent exist)

## Tasks

### Task 1: Add `implement` action to `/team` command
**Files:** `.claude/commands/team.md`
**Action:**
Add a new action `implement` to the team command:

1. In the Arguments table, add: `implement` | `/team implement <feature> <plan>` | Spawn implementer teammates to execute a plan in parallel
2. Add a new `#### Action: implement` section after the existing `create` action:
   - Step 1: Read `NN-PLAN.json` from `docs/planning/work/features/<feature>/<plan>-PLAN.json`
   - Step 2: Call bridge module to generate task descriptions:
     ```bash
     python3 -c "
     import sys, json; sys.path.insert(0, '.')
     from scripts.memory import plan_to_task_descriptions
     from pathlib import Path
     tasks = plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<NN>-PLAN.json'), Path('.'))
     print(json.dumps(tasks, indent=2))
     "
     ```
   - Step 3: Create team via TeamCreate with name `impl-<feature>-<plan>`
   - Step 4: For each task description, create a TaskCreate entry using the task's `name` as subject, `description` as the full agent prompt, and set `addBlockedBy` from the task's `blockedBy` field
   - Step 5: Spawn one `implementer` teammate per task using the Task tool with `subagent_type="general-purpose"`, `team_name`, and the task description as the prompt
   - Step 6: Activate delegate mode (leader coordinates, doesn't code)
   - Step 7: Monitor: as teammates complete tasks, check if all are done; when all tasks pass verification, proceed to plan verification
3. Add to Recommended Team Compositions: "Implementation Team" example
4. Add to Examples section

**Verify:**
```bash
grep -q 'implement' .claude/commands/team.md && grep -q 'plan_to_task_descriptions' .claude/commands/team.md && echo "team implement action OK"
```

**Done when:** `/team implement <feature> <plan>` action is fully documented with bridge module integration.

### Task 2: Add team mode to `/implement` command
**Files:** `.claude/commands/implement.md`
**Action:**
Add a team mode detection step between Step 1 and Step 2:

1. Add `### Step 1c: Team Mode (If Requested)` after the existing Step 1b:
   - If the user runs `/implement <feature> <plan> --team` or the plan has more than 1 task and Agent Teams is available:
     - Suggest: "This plan has N tasks. Run `/team implement <feature> <plan>` for parallel execution?"
     - If user confirms or used `--team`, delegate to `/team implement`
   - Otherwise, continue with the existing single-agent sequential flow

2. The detection logic:
   ```
   If $ARGUMENTS contains "--team":
     → Delegate to /team implement <feature> <plan>
   Else if plan has >1 task and CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is set:
     → Suggest team mode, continue with serial if declined
   Else:
     → Standard serial execution (unchanged)
   ```

3. Ensure the existing single-agent flow is completely unchanged when team mode is not active (backward compatibility per CONTEXT.md constraints).

**Verify:**
```bash
grep -q 'Team Mode' .claude/commands/implement.md && grep -q 'team implement' .claude/commands/implement.md && echo "implement team mode OK"
```

**Done when:** `/implement` offers team delegation for multi-task plans while preserving existing serial behavior.

### Task 3: Add team-implement display to `/status`
**Files:** `.claude/commands/status.md`
**Action:**
Extend Step 3b (Memory Status) to include team implementation state:

1. After the existing memory prime/stats output, add a section that detects active team implementation:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '.')
   from scripts.memory import is_initialized, list_issues
   from pathlib import Path
   root = Path('.')
   if is_initialized(root):
       active = list_issues(status='in_progress', label='feature', root=root)
       if active:
           print('### Team Implementation')
           for t in active:
               children = list_issues(parent=t.id, root=root)
               done = sum(1 for c in children if c.status == 'closed')
               total = len(children)
               print(f'  {t.id} {t.title}: {done}/{total} tasks complete')
   "
   ```

2. In Step 5 (Recommend Action), add: if team implementation is active, suggest `/team status` for detailed teammate progress.

**Verify:**
```bash
grep -q 'Team Implementation' .claude/commands/status.md && echo "status team display OK"
```

**Done when:** `/status` shows team implementation progress when active.

## Verification

After all tasks:
```bash
grep -q 'Action: implement' .claude/commands/team.md && grep -q 'Team Mode' .claude/commands/implement.md && grep -q 'Team Implementation' .claude/commands/status.md && python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(team-implement-integration): wire bridge into team/implement/status commands

- Add /team implement action for parallel plan execution
- Add team mode suggestion to /implement for multi-task plans
- Add team implementation progress to /status display
```

---
*Planned: 2026-02-14*
