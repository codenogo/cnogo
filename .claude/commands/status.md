# Status
<!-- effort: low -->

Show current position and next actions.

## Your Task

### Step 1: Memory Status (Primary)

```bash
python3 .cnogo/scripts/workflow_memory.py prime --limit 8
python3 .cnogo/scripts/workflow_memory.py stats
python3 .cnogo/scripts/workflow_memory.py work-list --needs-attention --json
```

If memory is not initialized, report that and continue with git/artifact status.

### Step 2: Git Status

```bash
git branch --show-current
git status --porcelain
git log origin/main..HEAD --oneline 2>/dev/null || echo "No remote tracking"
git log -5 --oneline
```

### Step 2.5: Initiative Context (If Applicable)

Detect if the current feature has a `parentShape` link. Extract the feature slug from the current branch (e.g., `feature/my-feature` → `my-feature`), then check:

```bash
python3 -c "
import json, pathlib, sys
slug = '$(git branch --show-current | sed \"s|^feature/||\")'
for name in ['CONTEXT.json', 'FEATURE.json']:
    p = pathlib.Path(f'docs/planning/work/features/{slug}/{name}')
    if p.exists():
        data = json.loads(p.read_text())
        ps = data.get('parentShape', {})
        if ps and ps.get('path'):
            parts = pathlib.Path(ps['path']).parts
            idx = parts.index('ideas') + 1 if 'ideas' in parts else -1
            if idx > 0: print(parts[idx]); sys.exit(0)
print('')
"
```

If a shape slug is returned, run:

```bash
python3 .cnogo/scripts/workflow_memory.py initiative-show <shape-slug> --json
```

Include a compact initiative section in the output:
- Initiative name and progress (N/M completed)
- Per-feature status line (slug | status | reviewVerdict)
- Pending shapeFeedback count (if any)
- Initiative-level next action

If no `parentShape` link exists, skip this step silently.

### Step 3: Artifact Status

```bash
ls docs/planning/work/features/ 2>/dev/null
ls docs/planning/work/quick/ 2>/dev/null | tail -10
```

If team execution is active, recommend `/team status` for detailed teammate progress.

### Step 4: Summarize

Report:
- current branch + dirty/clean state
- active feature/work-order progress from memory
- commits ahead of remote
- token optimization drift from `python3 .cnogo/scripts/workflow_checks.py discover --since-days 7` (optional)
- immediate next action

### Step 5: Recommended Next Command

Choose one:
- `/implement <feature> <plan>` when mid-plan
- `/review` when implementation is complete
- `/ship` when review passed
- `/discuss <feature>` or `/quick <task>` when idle

## Output

Concise status summary plus one recommended next step.
