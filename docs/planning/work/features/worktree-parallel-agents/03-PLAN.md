# Plan 03: Command Integration

## Goal
Wire worktree primitives into team.md, implement.md, resume.md, and implementer.md — replacing shared-directory parallel execution.

## Prerequisites
- [ ] Plan 01 complete (worktree.py)
- [ ] Plan 02 complete (resolver agent, exports, validation)

## Tasks

### Task 1: Update team.md Implement Action
**Files:** `.claude/commands/team.md`
**Action:**
Rewrite the `#### Action: implement` section to use worktrees:

Replace Steps 4-11 with:

1. Parse `<feature>` and `<plan>` from arguments
2. Load `docs/planning/work/features/<feature>/<plan>-PLAN.json`
3. Generate task descriptions via bridge: `plan_to_task_descriptions()`
4. Check file conflicts via `detect_file_conflicts()`. **Advisory only** — if conflicts, warn: "File overlaps detected. Merge conflicts likely — resolver agent will handle." Proceed regardless (per CONTEXT.md: worktrees provide isolation).
5. **Create worktree session**:
   ```bash
   python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory import create_session, plan_to_task_descriptions; from pathlib import Path; root=Path('.'); descs=plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<plan>-PLAN.json'), root); session=create_session(Path('docs/planning/work/features/<feature>/<plan>-PLAN.json'), root, descs); print(json.dumps({'phase': session.phase, 'worktrees': len(session.worktrees)}))"
   ```
6. Create team `impl-<feature>-<plan>` via TeamCreate
7. Create TaskCreate entries — use worktree path in task description so agents know their working directory. Two-pass: create tasks, then wire blockedBy.
8. Spawn one `implementer` teammate per task via Task tool with `team_name`. The agent's prompt must include: "Your working directory is `<worktree_path>`. All file paths are relative to this directory."
9. Monitor via TaskList until all tasks completed.
10. **Merge agent branches**:
    ```bash
    python3 -c "import sys,json; sys.path.insert(0,'.'); from scripts.memory import load_session, merge_session; from pathlib import Path; root=Path('.'); session=load_session(root); result=merge_session(session, root); print(json.dumps({'success': result.success, 'merged': result.merged_indices, 'conflict_index': result.conflict_index, 'conflict_files': result.conflict_files}))"
    ```
11. **If merge conflict**: spawn resolver agent (`.claude/agents/resolver.md`) with context from `get_conflict_context()`. After resolution, retry merge from where it left off. If resolver fails after 2 attempts, `git merge --abort` and report to user.
12. Run `planVerify` commands from plan JSON. Fix failures directly.
13. Create summary artifacts (`<NN>-SUMMARY.md` + `<NN>-SUMMARY.json`)
14. Commit: `git add -A && git commit -m "<commitMessage from plan>"`
15. **Cleanup worktrees**:
    ```bash
    python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import load_session, cleanup_session; from pathlib import Path; root=Path('.'); session=load_session(root); cleanup_session(session, root); print('Worktrees cleaned')"
    ```
16. Dismiss team, then `python3 .cnogo/scripts/workflow_validate.py`

Also remove the `Notes` section line about "one team per session, no resumption" — worktree state file enables resumption.

**Verify:**
```bash
grep -c 'worktree' .claude/commands/team.md | xargs -I{} test {} -ge 5 && echo 'PASS' || echo 'FAIL'
```
```bash
grep 'create_session' .claude/commands/team.md && grep 'merge_session' .claude/commands/team.md && grep 'cleanup_session' .claude/commands/team.md && echo 'PASS'
```

**Done when:** team.md implement action uses full worktree lifecycle: create → execute → merge → resolve → cleanup.

### Task 2: Update implement.md + bridge.py Advisory Mode
**Files:** `.claude/commands/implement.md`, `.cnogo/scripts/memory/bridge.py`
**Action:**

**implement.md Step 1c** — Replace the detection logic to reflect worktrees-only:

```markdown
### Step 1c: Team Mode (If Requested)

**Detection logic (in priority order):**
1. If `$ARGUMENTS` contains `--team` → delegate to `/team implement <feature> <plan>` (explicit flag, always honored)
2. If plan JSON has `"parallelizable": true` AND Agent Teams available → auto-delegate with worktree isolation: "Delegating to team mode with worktree isolation (plan marked parallelizable)."
3. If plan JSON has `"parallelizable": false` → serial execution (override auto-detection)
4. If `parallelizable` not present → fall back to heuristic:
   a. If ALL: plan has >2 tasks AND Agent Teams available → auto-delegate with worktree isolation. File conflicts are advisory only (resolver agent handles merge conflicts).
   b. Otherwise → standard serial execution

Note: All parallel execution uses git worktree isolation. File overlap no longer blocks parallel execution — the resolver agent handles merge conflicts at merge time.
```

Key change: Remove the "non-overlapping files" requirement from step 4a. File overlaps are now advisory, not blocking.

**bridge.py** — Update `detect_file_conflicts()` to return advisory severity:

Change the docstring from "Check for file boundary violations" to "Check for file overlaps that may produce merge conflicts (advisory)."

Add a `severity` key to each conflict dict: `"advisory"` (since worktrees provide isolation). This communicates to callers that conflicts are informational, not blocking.

```python
conflicts.append({"file": file_path, "tasks": owners, "severity": "advisory"})
```

**Verify:**
```bash
grep 'advisory' scripts/memory/bridge.py && grep 'worktree isolation' .claude/commands/implement.md && echo 'PASS'
```

**Done when:** implement.md no longer blocks on file conflicts; bridge.py marks conflicts as advisory.

### Task 3: Update resume.md + implementer.md for Worktrees
**Files:** `.claude/commands/resume.md`, `.claude/agents/implementer.md`
**Action:**

**resume.md** — Add worktree session detection to Step 3b (Team Implementation Recovery):

After the existing memory recovery block, add a new section:

```markdown
#### Worktree Session Recovery

Detect interrupted worktree sessions:

\`\`\`bash
python3 -c "
import sys, json; sys.path.insert(0, '.')
from scripts.memory.worktree import load_session
from pathlib import Path
root = Path('.')
session = load_session(root)
if session:
    print(f'### Interrupted Worktree Session')
    print(f'  Feature: {session.feature}, Plan: {session.plan_number}')
    print(f'  Phase: {session.phase}')
    print(f'  Base: {session.base_commit} on {session.base_branch}')
    completed = sum(1 for w in session.worktrees if w.status in ('completed', 'merged'))
    total = len(session.worktrees)
    print(f'  Progress: {completed}/{total} tasks')
    for w in session.worktrees:
        icon = {'created': '⏳', 'executing': '🔄', 'completed': '✅', 'merged': '🔀', 'conflict': '⚠️', 'cleaned': '🧹'}.get(w.status, '❓')
        print(f'  {icon} Task {w.task_index}: {w.name} [{w.status}]')
    if session.phase == 'executing':
        print(f'  Resume with: /team implement {session.feature} {session.plan_number}')
    elif session.phase == 'merging':
        print(f'  Continue merge from task {session.merge_order[len(session.merged_so_far)]}')
    elif session.phase in ('merged', 'verified'):
        print(f'  Ready to commit and clean up')
"
\`\`\`

Recovery options based on phase:
- **executing**: Re-run `/team implement` — bridge skips already-closed memory tasks, worktrees exist for in-progress ones
- **merging**: Continue `merge_session()` from last checkpoint (reads `mergedSoFar`)
- **merged/verified**: Just commit and cleanup
- **Any phase**: `cleanup_session()` to abort and remove all worktrees
```

**implementer.md** — Add commit step and worktree awareness:

After the existing "Verify" step (step 4) and before "Close" (step 5), add:

```markdown
5. **Commit**: Stage and commit your changes to the worktree branch:
   `git add -A && git commit -m "task(<feature>): <task-name>"`
```

Renumber Close → 6, Report → 7.

Add to Rules section:
- "You are working in a git worktree — an isolated copy of the repo with its own branch"
- "Always commit your changes before closing the memory issue"

**Verify:**
```bash
grep 'worktree' .claude/commands/resume.md && grep 'Commit' .claude/agents/implementer.md && echo 'PASS'
```

**Done when:** resume.md detects interrupted worktree sessions; implementer.md commits to worktree branch.

## Verification

After all tasks:
```bash
grep -c 'worktree' .claude/commands/team.md | xargs -I{} test {} -ge 5 && echo 'team.md PASS'
grep 'advisory' scripts/memory/bridge.py && echo 'bridge.py PASS'
grep 'load_session' .claude/commands/resume.md && echo 'resume.md PASS'
grep 'Commit' .claude/agents/implementer.md && echo 'implementer.md PASS'
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(worktree-parallel-agents): wire worktrees into team, implement, resume commands

- Replace shared-dir parallel execution with worktree isolation in team.md
- Update implement.md — file conflicts are advisory, not blocking
- Add worktree session recovery to resume.md
- Add commit step to implementer.md for worktree branches
- Update bridge.py detect_file_conflicts() to return advisory severity
```

---
*Planned: 2026-02-14*
