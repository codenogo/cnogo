# Resume

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
