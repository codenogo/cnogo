# Status
<!-- effort: low -->

Show current position, progress, and next steps.

## Your Task

Read project state and provide clear status.

### Step 1: Read State from Memory

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"
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

### Step 3b: Memory Status

Include structured task status from the memory engine:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, prime, stats
from pathlib import Path
root = Path('.')
if is_initialized(root):
    print(prime(root=root))
    print()
    s = stats(root=root)
    print(f'Total: {s.get(\"total\", 0)} | Open: {s.get(\"open\", 0)} | Active: {s.get(\"in_progress\", 0)} | Ready: {s.get(\"ready\", 0)} | Blocked: {s.get(\"blocked\", 0)}')
else:
    print('Memory engine not initialized.')
"
```

Include the memory output in the status report alongside the git and artifact state.

#### Team Implementation Progress

If a team implementation is active, show task completion progress:

```bash
python3 -c "
import sys, json; sys.path.insert(0, '.')
from datetime import datetime, timezone
from scripts.memory import is_initialized, list_issues
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Load stale threshold from WORKFLOW.json (default 10 minutes)
    stale_minutes = 10
    wf_path = root / 'docs' / 'planning' / 'WORKFLOW.json'
    if wf_path.exists():
        try:
            wf = json.loads(wf_path.read_text())
            stale_minutes = wf.get('agentTeams', {}).get('staleIndicatorMinutes', 10)
        except Exception:
            pass
    now = datetime.now(timezone.utc)
    epics = list_issues(issue_type='epic', status='in_progress', root=root)
    for epic in epics:
        children = list_issues(parent=epic.id, root=root)
        if not children:
            continue
        done = sum(1 for c in children if c.status == 'closed')
        active = sum(1 for c in children if c.status == 'in_progress')
        total = len(children)
        print(f'### Team Implementation: {epic.title}')
        print(f'  Progress: {done}/{total} tasks complete, {active} in progress')
        for c in children:
            assignee = f' (@{c.assignee})' if c.assignee else ''
            if c.status == 'closed':
                print(f'  ✅ {c.id} {c.title}{assignee}')
            elif c.status == 'in_progress':
                age_str = ''
                stale = False
                if hasattr(c, 'updated_at') and c.updated_at:
                    try:
                        updated = datetime.fromisoformat(c.updated_at.replace('Z', '+00:00'))
                        age_min = max(0, int((now - updated).total_seconds() / 60))
                        age_str = f' — claimed {age_min}m ago'
                        stale = age_min > stale_minutes
                    except Exception:
                        pass
                icon = '⚠️' if stale else '🔄'
                suffix = ' (stale?)' if stale else ''
                print(f'  {icon} {c.id} {c.title}{assignee}{age_str}{suffix}')
            else:
                print(f'  ⏳ {c.id} {c.title}{assignee}')
"
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

- [Any blockers from memory engine]
```

### Step 5: Recommend Action

Based on state, suggest:

- If uncommitted changes: "Ready to `/review` and `/ship`?"
- If mid-plan: "Continue with `/implement [feature] [plan]`"
- If plans complete: "Ready for `/review`"
- If team implementation active: "Monitor with `/team status` for detailed teammate progress"
- If nothing in progress: "Start with `/discuss [feature]` or `/quick [task]`"

## Output

Clear status with recommended next action.
