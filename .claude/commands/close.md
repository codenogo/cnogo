# Close: $ARGUMENTS
<!-- effort: low -->

Post-merge cleanup. Keeps `STATE.md` current and optionally archives feature artifacts after merge into `main`.

## Arguments

`/close <feature-slug>`

Example: `/close websocket-notifications`

## Your Task

After a feature is merged, update state and file organization.

### Step 1: Confirm Merge

Confirm with git:

```bash
git branch --show-current
git log -5 --oneline
```

If the user provides a PR number, include it in notes.

### Step 2: Update `docs/planning/STATE.md`

Update:

- **Current Focus**: set Feature to `None` (or next feature if already known)
- **Status**: `Idle` (or next status)
- Clear any active **Session Handoff** (mark as cleared)
- Add a line in **Recent Decisions** indicating the merge (feature slug + PR if known)

### Step 3: Archive Feature Artifacts (Optional)

If user confirms, move:

`docs/planning/work/features/$ARGUMENTS/` → `docs/planning/archive/features/$ARGUMENTS/`

```bash
mkdir -p docs/planning/archive/features
mv "docs/planning/work/features/$ARGUMENTS" "docs/planning/archive/features/$ARGUMENTS"
```

### Step 4: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- What was updated in `STATE.md`
- Whether artifacts were archived
- Next recommended action (`/brainstorm`, `/discuss`, or `/quick`)

