# Quick: $ARGUMENTS
<!-- effort: medium -->

Fast path for small fixes and ad-hoc tasks. Skips discuss/plan ceremony.

## When to Use

- Bug fixes
- Config changes
- Small features (≤1 hour)
- One-off tasks
- Documentation updates

## When NOT to Use

- Changes touching multiple services
- New APIs or contracts
- Database schema changes
- Anything needing rollback planning

Use `/discuss` + `/plan` instead.

## Your Task

Execute "$ARGUMENTS" with minimal ceremony but full verification.

### Step 0: Create a Branch (Required)

Quick fixes should happen on a branch off `main` (or your default branch), then shipped via PR.

```bash
# Ensure up-to-date main (optional if you can't pull)
git checkout main
git pull

# Create a fix branch
git checkout -b fix/<slug>
```

If the repo uses `master` instead of `main`, use `master` as the base branch.

### Step 1: Understand Scope

Read the request and identify:
- Files likely to change
- Tests that should exist
- How to verify it works

If scope seems large (>5 files, >2 hours), suggest full workflow instead.

### Step 2: Create Quick Plan

Create `docs/planning/work/quick/NNN-[slug]/PLAN.md`:

```markdown
# Quick: $ARGUMENTS

## Goal
[What this accomplishes]

## Files
- `path/to/file.ts`

## Approach
[Brief description]

## Verify
```bash
[How to verify]
```
```

Number sequentially: `001`, `002`, etc.

Also create a machine-checkable contract:

- `docs/planning/work/quick/NNN-[slug]/PLAN.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per artifact: `PLAN.md` + `PLAN.json`, `SUMMARY.md` + `SUMMARY.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `timestamp`.
- **ID/slug alignment**: directory name MUST match `NNN-<slug>`, and the contract should match that `id` and `slug`.
- **Validation**: run `python3 scripts/workflow_validate.py` before asking to `/ship`.

Contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "id": "001",
  "slug": "fix-typo",
  "goal": "What this accomplishes",
  "files": ["path/to/file.ts"],
  "verify": ["npm test --silent"],
  "timestamp": "2026-01-24T00:00:00Z"
}
```

### Step 3: Implement

1. Make the changes
2. Run verification
3. Run tests for affected code

### Step 4: Create Summary

Create `docs/planning/work/quick/NNN-[slug]/SUMMARY.md`:

```markdown
# Quick Summary: $ARGUMENTS

## Outcome
✅ Complete

## Changes
| File | Change |
|------|--------|
| `path/to/file` | [what] |

## Verification
[Results]

## Commit
`abc123f` - [message]

---
*Completed: [date]*
```

Also create:

- `docs/planning/work/quick/NNN-[slug]/SUMMARY.json`

Contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "id": "001",
  "slug": "fix-typo",
  "outcome": "complete|partial|failed",
  "changes": [{ "file": "path/to/file", "change": "what changed" }],
  "verification": ["...command outputs or notes..."],
  "commit": { "hash": "abc123f", "message": "..." },
  "timestamp": "2026-01-24T00:00:00Z"
}
```

### Step 5: Memory Tracking (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), create and close a quick task issue:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create, close
from pathlib import Path
root = Path('.')
if is_initialized(root):
    issue = create(
        '<task description>',
        issue_type='quick',
        labels=['quick'],
        description='<brief summary of what was done>',
        root=root,
    )
    close(issue.id, reason='completed', root=root)
    print(f'Quick task tracked: {issue.id}')
"
```

If memory is not initialized, skip this step.

### Step 6: Commit

```bash
git add -A
git commit -m "fix([scope]): $ARGUMENTS"
```

### Step 7: Prompt Next Step

Ask user:
- "Ready to `/ship`?"
- "Or continue with another `/quick`?"

## Output

- What was changed
- Verification results
- Ready for `/ship`

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
