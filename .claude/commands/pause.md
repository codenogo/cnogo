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
# What feature/task is in progress
cat docs/planning/STATE.md | head -20

# Recent files touched
git diff --name-only HEAD~3..HEAD 2>/dev/null || git diff --name-only
```

### Step 3: Create Handoff

Update `docs/planning/STATE.md` with handoff section:

```markdown
## Session Handoff

**Paused:** [timestamp]
**Branch:** [current branch]
**Checkout:** [directory name if relevant]

### Last Action
[What was just completed]

### In Progress
[What was being worked on]

### Next Step
[Exactly what to do next - be specific]

### Context
[Any important context that won't be obvious]

### Open Files
[Files that were being edited]
- `path/to/file.ts` — [what was being done]
- `path/to/other.ts` — [what was being done]

### Uncommitted Changes
```
[output of git status --porcelain]
```

### Mental State
[Any decisions made but not documented, gotchas discovered, etc.]
```

### Step 3b: Memory Sync (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), persist all task state:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, sync, prime
from pathlib import Path
root = Path('.')
if is_initialized(root):
    sync(root)
    print('Memory state synced to .cnogo/issues.jsonl')
    print()
    print(prime(root=root))
"
```

This exports the full memory state to JSONL (git-tracked), making session handoff more robust. The `prime()` output can be included in the handoff section for quick context recovery.

### Step 4: Verify State is Saved

```bash
# Ensure STATE.md is saved
cat docs/planning/STATE.md | grep -A 30 "Session Handoff"
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
