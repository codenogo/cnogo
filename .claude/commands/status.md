# Status
<!-- effort: low -->

Show current position, progress, and next steps.

## Your Task

Read project state and provide clear status.

### Step 1: Read State

```bash
cat docs/planning/STATE.md
```

### Step 2: Check Git State

```bash
# Current branch
git branch --show-current

# Uncommitted changes
git status --porcelain

# Commits ahead of origin
git log origin/main..HEAD --oneline 2>/dev/null || echo "No remote tracking"

# Recent commits
git log -5 --oneline
```

### Step 2b: Check Optional Git Hook Enforcement

If you want workflow checks to run when committing **outside Claude**, install repo-local hooks.

Check whether hooks are installed:

```bash
HOOKS_PATH=$(git config --get core.hooksPath || true)
if [ "$HOOKS_PATH" != ".githooks" ]; then
  echo "⚠️ Git hooks not installed (core.hooksPath != .githooks)."
  echo "   To enable: ./scripts/install-githooks.sh"
else
  echo "✅ Git hooks installed (core.hooksPath=.githooks)"
fi
```

### Step 3: Check Work in Progress

```bash
# List active features
ls docs/planning/work/features/ 2>/dev/null

# List quick tasks
ls docs/planning/work/quick/ 2>/dev/null | tail -5
```

### Step 4: Generate Status Report

Output:

```markdown
## Current Status

**Branch:** feature/xyz
**Uncommitted changes:** 3 files
**Commits ready to push:** 2

## Active Work

### Feature: [feature-name]
- Status: Planning / Implementing / Review
- Plans: 01 ✅, 02 🔄, 03 ⏳
- Current: Implementing Plan 02

### Quick Tasks
- 015-fix-typo ✅
- 016-add-logging 🔄

## Recent Activity

| Commit | Message | When |
|--------|---------|------|
| abc123 | feat: add X | 2 hours ago |
| def456 | fix: Y | 3 hours ago |

## Next Steps

1. [Most immediate action]
2. [Following action]

## Blockers

- [Any blockers from STATE.md]
```

### Step 5: Recommend Action

Based on state, suggest:

- If uncommitted changes: "Ready to `/review` and `/ship`?"
- If mid-plan: "Continue with `/implement [feature] [plan]`"
- If plans complete: "Ready for `/review`"
- If nothing in progress: "Start with `/discuss [feature]` or `/quick [task]`"

## Output

Clear status with recommended next action.
