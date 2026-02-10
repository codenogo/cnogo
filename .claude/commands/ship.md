# Ship Current Changes
<!-- effort: high -->

Commit, push, and create PR. Final step after `/review` passes.

## Your Task

Ship the current changes to a PR.

### Step 1: Pre-flight Checks

```bash
# Ensure we're not on main/master
current_branch=$(git branch --show-current)
if [ "$current_branch" = "main" ] || [ "$current_branch" = "master" ]; then
    echo "ERROR: Cannot ship from main/master. Create a feature branch first."
    exit 1
fi

# Ensure working directory is clean or has changes to commit
git status --porcelain
```

### Step 2: Stage and Commit (if uncommitted changes)

If there are uncommitted changes:

```bash
git add -A
git commit -m "[type]([scope]): [description]"
```

**Commit message format:**
- `feat(scope): add new feature`
- `fix(scope): fix bug description`
- `refactor(scope): refactor description`
- `docs(scope): update documentation`
- `test(scope): add tests for feature`
- `chore(scope): maintenance task`

Infer the appropriate type and scope from the changes.

### Step 3: Push

```bash
git push -u origin $(git branch --show-current)
```

### Step 4: Create PR

Use GitHub CLI:

```bash
gh pr create \
    --title "[PR title based on commits]" \
    --body "[Generated PR body]"
```

**PR Body Template:**

```markdown
## Summary

[One paragraph describing what this PR does]

## Changes

- [Bullet point changes]

## Testing

- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual verification complete

## Related

- Closes #[issue] (if applicable)
- Docs: `docs/planning/work/features/[feature]/`
```

### Step 5: Update State

Update `docs/planning/STATE.md`:
```
## Current Focus
- Feature: [feature]
- Status: PR created
- PR: #[number] or [URL]
- Next: Await review / merge
```

### Step 6: Clean Up (optional)

If user confirms:
```bash
# Switch back to main
git checkout main
git pull
```

## Output

- PR URL
- Summary of what was shipped
- Next steps (await review, or next feature)
