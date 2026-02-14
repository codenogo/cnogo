# Resume
<!-- effort: low -->

Restore context from a paused session.

## Your Task

Pick up where the last session left off.

### Step 1: Load Handoff from Memory

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, list_issues, prime
from pathlib import Path
root = Path('.')
if is_initialized(root):
    print(prime(root=root))
    print()
    epics = list_issues(issue_type='epic', status='open', root=root)
    if not epics:
        epics = list_issues(issue_type='epic', status='in_progress', root=root)
    for e in epics:
        h = e.metadata.get('handoff', '')
        if h:
            print(f'Handoff ({e.feature_slug}): {h}')
"
```

Look for handoff metadata on active epics.

### Step 2: Verify Git State

```bash
# Check we're on the right branch
git branch --show-current

# Check for uncommitted changes
git status --porcelain

# Check for stashes
git stash list
```

Compare with handoff. If mismatched:
- Wrong branch → `git checkout [branch from handoff]`
- Missing changes → `git stash pop` (if stashed)
- Extra changes → Alert user

### Step 3: Restore Context

Read the files mentioned in "Open Files":

```bash
# Load each file mentioned
cat [file1]
cat [file2]
```

### Step 3b: Memory Context (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), load structured task state:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, prime, ready, list_issues, import_jsonl
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Rebuild from JSONL if DB is stale
    import_jsonl(root)

    # Show context summary
    print(prime(root=root))

    # Show in-progress work
    active = list_issues(status='in_progress', root=root)
    if active:
        print('### Continue Working On')
        for t in active:
            print(f'  - {t.id} {t.title} (@{t.assignee})')

    # Show ready tasks
    ready_tasks = ready(root=root)
    if ready_tasks:
        print('### Ready to Start')
        for t in ready_tasks[:5]:
            print(f'  - {t.id} {t.title}')
"
```

When memory is available, the structured task state replaces the need to parse markdown handoff prose. The `prime()` output gives a compact summary of open work, ready tasks, and blockers.

#### Team Implementation Recovery

Detect interrupted team implementations and release stale claims:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, list_issues, release
from pathlib import Path
root = Path('.')
if is_initialized(root):
    epics = list_issues(issue_type='epic', root=root)
    for epic in epics:
        if epic.status == 'closed':
            continue
        children = list_issues(parent=epic.id, root=root)
        if not children:
            continue
        done = [c for c in children if c.status == 'closed']
        active = [c for c in children if c.status == 'in_progress']
        remaining = [c for c in children if c.status == 'open']
        if active or remaining:
            print(f'### Interrupted: {epic.title}')
            print(f'  Completed: {len(done)}/{len(children)}')
            # Release stale in_progress claims from dead agents
            for c in active:
                print(f'  Releasing stale claim: {c.id} {c.title} (@{c.assignee})')
                release(c.id, actor='resume-recovery', root=root)
            remaining_count = len(active) + len(remaining)
            print(f'  {remaining_count} task(s) ready for re-execution')
            print(f'  Resume with: /team implement {epic.feature_slug} {epic.plan_number}')
"
```

**Duplicate prevention**: When `/team implement` runs after recovery, the bridge module reads the plan JSON. For each task:
- If the task's `memoryId` is already **closed** → skip (already done)
- If the task's `memoryId` is **open** (released above) → create TaskCreate entry and re-execute
- This prevents duplicate work: only incomplete tasks are re-created in the new team session

#### Worktree Session Recovery

Detect interrupted worktree sessions:

```bash
python3 -c "
import sys, json; sys.path.insert(0, '.')
from scripts.memory import load_session
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
        remaining = len(session.merged_so_far)
        if remaining < len(session.merge_order):
            print(f'  Continue merge from task {session.merge_order[remaining]}')
        else:
            print(f'  All merges done — ready to finalize')
    elif session.phase in ('merged', 'verified'):
        print(f'  Ready to commit and clean up')
"
```

Recovery options based on phase:
- **executing**: Re-run `/team implement` — bridge skips already-closed memory tasks, worktrees exist for in-progress ones
- **merging**: Continue `merge_session()` from last checkpoint (reads `mergedSoFar`)
- **merged/verified**: Just commit and cleanup
- **Any phase**: `cleanup_session()` to abort and remove all worktrees

### Step 4: Load Feature Context

If working on a feature:

```bash
# Load feature docs
cat docs/planning/work/features/[feature]/CONTEXT.md
cat docs/planning/work/features/[feature]/*-PLAN.md | head -100
cat docs/planning/work/features/[feature]/*-SUMMARY.md 2>/dev/null
```

### Step 5: Present Resume Summary

```markdown
## ▶️ Session Resumed

**From:** [timestamp from handoff]
**Branch:** [branch]
**Feature:** [feature name]

### Where We Left Off
[Last action from handoff]

### Current State
- Uncommitted changes: [N files]
- Plan progress: [X of Y tasks complete]

### Next Step
[Next step from handoff]

### Context Loaded
- `path/to/file.ts` — [purpose]
- `path/to/other.ts` — [purpose]

### Team Recovery (if applicable)
[Show interrupted team implementations from memory and suggest `/team implement` to resume]

### Mental Notes
[Mental state from handoff]
```

### Step 6: Clear Handoff

After successful resume, clear handoff metadata from the active epic:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import list_issues, update
from pathlib import Path
root = Path('.')
epics = list_issues(issue_type='epic', status='open', root=root)
if not epics:
    epics = list_issues(issue_type='epic', status='in_progress', root=root)
for e in epics:
    if e.metadata.get('handoff'):
        meta = {k: v for k, v in e.metadata.items() if k != 'handoff'}
        update(e.id, metadata=meta, root=root)
        print(f'Handoff cleared from {e.id}')
"
```

### Step 7: Confirm Ready

Ask user:
```
Ready to continue with: [next step from handoff]? (y/n)
```

If yes, proceed with the next step.
If no, ask what they'd like to do instead.

## Output

- Context restored
- Clear summary of where we are
- Ready to continue
