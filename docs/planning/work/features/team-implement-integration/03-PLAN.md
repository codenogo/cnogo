# Plan 03: Recovery, Documentation, and Polish

## Goal
Enable session recovery for team implementations, add documentation, and ensure all agents are aware of the new capability.

## Prerequisites
- [ ] Plan 01 complete (bridge module exists)
- [ ] Plan 02 complete (commands wired)

## Tasks

### Task 1: Add team-implement recovery to `/resume`
**Files:** `.claude/commands/resume.md`
**Action:**
Extend Step 3b (Memory Context) to detect and recover from interrupted team implementations:

1. After the existing memory import/prime block, add team recovery logic:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '.')
   from scripts.memory import is_initialized, list_issues, ready, import_jsonl
   from pathlib import Path
   root = Path('.')
   if is_initialized(root):
       import_jsonl(root)  # rebuild from JSONL
       # Find in-progress epics with children (team implementations)
       epics = list_issues(status='in_progress', issue_type='epic', root=root)
       for epic in epics:
           children = list_issues(parent=epic.id, root=root)
           in_progress = [c for c in children if c.status == 'in_progress']
           remaining = [c for c in children if c.status == 'open']
           done = [c for c in children if c.status == 'closed']
           if in_progress or remaining:
               print(f'### Interrupted: {epic.title}')
               print(f'  Completed: {len(done)}, In Progress: {len(in_progress)}, Remaining: {len(remaining)}')
               for c in in_progress:
                   print(f'  > {c.id} {c.title} (@{c.assignee}) — was in progress')
               for c in remaining[:5]:
                   print(f'  - {c.id} {c.title} — ready to resume')
               print(f'  Resume with: /team implement {epic.feature_slug} {epic.plan_number}')
   "
   ```

2. In Step 5 (Present Resume Summary), add a "Team Recovery" section that shows interrupted team work and suggests how to resume it.

3. Add guidance: "When resuming a team implementation, the memory engine preserves all task state. The new team session will see which tasks are done, which were in progress (and need re-claiming), and which are still blocked."

**Verify:**
```bash
grep -q 'Interrupted' .claude/commands/resume.md && grep -q 'team implement' .claude/commands/resume.md && echo "resume recovery OK"
```

**Done when:** `/resume` detects interrupted team implementations and suggests recovery.

### Task 2: Add "Team Implementation" skill to skills library
**Files:** `docs/skills.md`
**Action:**
Add a new skill section after "Memory Task Management":

```markdown
## Team Implementation

**When**: executing a multi-task plan with Agent Teams for parallel implementation.

**Checklist**:
- Verify plan exists: `NN-PLAN.json` with tasks, files, verify commands
- Verify memory is initialized: `is_initialized(Path('.'))`
- Generate task descriptions: `plan_to_task_descriptions(plan_path, root)`
- Create team: `TeamCreate` with name `impl-<feature>-<plan>`
- Spawn implementers: one `general-purpose` teammate per task with task description
- Activate delegate mode: Shift+Tab (leader coordinates, doesn't code)
- Monitor progress: `/team status` or TaskList
- Handle failures: retry once, then reassign or escalate
- Close epic when all tasks complete
- Sync state: `memory.sync(root)` before pausing

**File Boundary Rule**: Each task owns its `files[]` — no two teammates should edit the same file.

**Dependency Rule**: Tasks within a plan run in parallel unless `blockedBy` is set. Plans run sequentially (plan 02 waits for plan 01).

**Recovery**: If interrupted, `/resume` detects in-progress tasks from memory state.
```

**Verify:**
```bash
grep -q 'Team Implementation' docs/skills.md && grep -q 'plan_to_task_descriptions' docs/skills.md && echo "skills updated OK"
```

**Done when:** Skills library includes team implementation checklist.

### Task 3: Update implementer agent awareness across existing agents
**Files:** `.claude/agents/code-reviewer.md`, `.claude/agents/test-writer.md`
**Action:**
Add a brief note to the code-reviewer and test-writer agents that they may be spawned alongside implementer agents in a team:

In the Memory Engine Integration section of each agent, add after the existing content:

```markdown
**Team Context**: If working alongside `implementer` teammates in a team, coordinate via TaskList. Use `memory.list_issues(status='in_progress')` to see what's being implemented. Avoid reviewing/testing files that are still being actively changed by an implementer.
```

This is the minimum awareness needed — just 2 agents that are most likely to work alongside implementers (reviewer + tester). The other 8 agents don't need changes.

**Verify:**
```bash
grep -q 'Team Context' .claude/agents/code-reviewer.md && grep -q 'Team Context' .claude/agents/test-writer.md && echo "agent awareness OK"
```

**Done when:** Reviewer and test-writer agents know about implementer teammates.

## Verification

After all tasks:
```bash
grep -q 'team implement' .claude/commands/resume.md && grep -q 'Team Implementation' docs/skills.md && grep -q 'Team Context' .claude/agents/code-reviewer.md && python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(team-implement-integration): add recovery, documentation, and agent awareness

- Add team-implement recovery to /resume command
- Add Team Implementation skill to skills library
- Add team context awareness to code-reviewer and test-writer agents
```

---
*Planned: 2026-02-14*
