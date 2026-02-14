# Resume
<!-- effort: low -->

Restore context from a paused session.

## Your Task

Pick up where the last session left off.

### Step 1: Load Handoff

```bash
cat docs/planning/STATE.md
```

Look for the `## Session Handoff` section.

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

Detect interrupted team implementations (in-progress epics with incomplete children):

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, list_issues
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
            print(f'  Completed: {len(done)}, In Progress: {len(active)}, Remaining: {len(remaining)}')
            for c in active:
                print(f'  > {c.id} {c.title} (@{c.assignee}) — was in progress')
            for c in remaining[:5]:
                print(f'  - {c.id} {c.title} — ready to resume')
            print(f'  Resume with: /team implement {epic.feature_slug} {epic.plan_number}')
"
```

When resuming a team implementation, the memory engine preserves all task state. The new team session will see which tasks are done, which were in progress (and need re-claiming), and which are still blocked.

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

After successful resume, update STATE.md:

```markdown
## Session Handoff

*Resumed [timestamp] — handoff cleared*
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
