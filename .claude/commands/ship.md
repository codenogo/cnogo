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

### Step 4b: Memory Close (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), close the feature epic and sync:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, list_issues, close, sync
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Close all open issues for this feature
    feature = '<feature-slug>'  # Infer from branch name or memory
    issues = list_issues(feature_slug=feature, root=root)
    closed = 0
    for issue in issues:
        if issue.status != 'closed':
            close(issue.id, reason='shipped', actor='claude', root=root)
            closed += 1
    sync(root)
    print(f'Shipped: closed {closed} memory issues for {feature}')
"
```

### Step 5: Clean Up (optional)

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
