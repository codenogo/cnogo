# Rollback: $ARGUMENTS
<!-- effort: medium -->

Quickly revert recent changes when something goes wrong.

## Arguments

`/rollback` — Interactive mode, shows recent commits to choose from
`/rollback last` — Revert the last commit
`/rollback <commit-hash>` — Revert a specific commit
`/rollback branch` — Reset to origin/main (discard local changes)

## Your Task

Safely revert changes based on the user's request.

### Step 1: Assess Current State

```bash
echo "=== Current Branch ==="
git branch --show-current

echo ""
echo "=== Recent Commits ==="
git log --oneline -10

echo ""
echo "=== Uncommitted Changes ==="
git status --porcelain

echo ""
echo "=== Commits Ahead of Origin ==="
git log origin/main..HEAD --oneline 2>/dev/null || echo "No remote tracking"
```

### Step 2: Handle Arguments

#### If no argument (interactive):

Show the user:
1. Last 5 commits with hashes and messages
2. Ask which one to revert to
3. Confirm before proceeding

#### If `last`:

```bash
echo "⚠️ Reverting last commit..."
LAST_COMMIT=$(git log -1 --format="%h %s")
echo "Commit to revert: $LAST_COMMIT"
```

Then ask user to confirm before running:
```bash
git revert HEAD --no-edit
```

#### If `<commit-hash>`:

```bash
echo "⚠️ Reverting commit: $ARGUMENTS"
git show --oneline --stat $ARGUMENTS | head -20
```

Then ask user to confirm before running:
```bash
git revert $ARGUMENTS --no-edit
```

#### If `branch`:

⚠️ **DANGEROUS** — This discards all local changes.

```bash
echo "⚠️ WARNING: This will discard ALL local changes!"
echo ""
echo "Changes that will be lost:"
git status --porcelain
echo ""
echo "Commits that will be lost:"
git log origin/main..HEAD --oneline
```

Require explicit confirmation: "Type 'DISCARD' to confirm"

Then:
```bash
git fetch origin
git reset --hard origin/main
```

### Step 3: Verify Rollback

After any rollback:

```bash
echo "=== Rollback Complete ==="
echo ""
echo "Current HEAD:"
git log -1 --oneline

echo ""
echo "Build check..."
# Run quick build to verify state
if [ -f pom.xml ]; then
    mvn compile -q && echo "✅ Build OK" || echo "❌ Build failed"
elif [ -f package.json ]; then
    npm run build --silent 2>/dev/null && echo "✅ Build OK" || echo "⚠️ No build script"
elif [ -f go.mod ]; then
    go build ./... && echo "✅ Build OK" || echo "❌ Build failed"
fi
```

## Safety Rules

1. **Never force push** — Rollbacks create new commits, preserving history
2. **Always confirm** — Show what will change before acting
3. **Check for uncommitted work** — Warn if there are unstaged changes
4. **Verify after rollback** — Run build to ensure valid state

## Output

- What was rolled back
- New commit hash (for revert commits)
- Build verification result
- Next recommended action
