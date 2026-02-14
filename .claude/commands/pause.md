# Pause
<!-- effort: low -->

Create a session handoff for resuming later.

## When to Use

- Stopping mid-feature
- Switching to another checkout
- End of day
- Context window getting full

## Your Task

Capture current state for seamless resume.

### Step 1: Capture Git State

```bash
# Current branch
git branch --show-current

# Uncommitted changes
git status --porcelain

# Stash if needed
git stash list
```

### Step 2: Identify Open Work

```bash
# Query memory for current state
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"

# Recent files touched
git diff --name-only HEAD~3..HEAD 2>/dev/null || git diff --name-only
```

### Step 3: Store Handoff in Memory

Store handoff context as metadata on the active epic (or as a standalone note):

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, list_issues, update, sync
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Find active epic to attach handoff
    epics = list_issues(issue_type='epic', status='in_progress', root=root)
    if not epics:
        epics = list_issues(issue_type='epic', status='open', root=root)
    if epics:
        epic = epics[0]
        update(epic.id, metadata={**epic.metadata, 'handoff': '<HANDOFF_TEXT>'}, root=root)
        print(f'Handoff stored on {epic.id} ({epic.feature_slug})')
    sync(root)
    print('Memory synced to .cnogo/issues.jsonl')
"
```

Compose the `<HANDOFF_TEXT>` as a compact string:

```
Paused: [timestamp] | Branch: [branch] | Last: [last action] | Next: [next step] | Files: [file1, file2] | Notes: [mental state]
```

### Step 4: Verify Handoff Saved

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import list_issues
from pathlib import Path
epics = list_issues(issue_type='epic', status='open', root=Path('.'))
for e in epics:
    h = e.metadata.get('handoff', '')
    if h:
        print(f'{e.id} ({e.feature_slug}): {h[:200]}')
"
```

### Step 5: Optional - Stash Changes

If user wants to switch branches:

```bash
git stash push -m "WIP: [feature] - [timestamp]"
```

Record stash in handoff:
```markdown
### Stashed
`stash@{0}` — WIP: [feature] - [timestamp]
```

## Output

```markdown
## ⏸️ Session Paused

**Branch:** feature/xyz
**Uncommitted:** 3 files
**Next:** [specific next action]

To resume:
```bash
cd [directory]
claude
/resume
```
```
