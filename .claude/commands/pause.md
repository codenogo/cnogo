# Pause

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
