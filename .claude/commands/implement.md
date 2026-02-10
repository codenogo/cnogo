# Implement: $ARGUMENTS
<!-- effort: high -->

Execute a plan with verification after each task.

## Arguments

`/implement <feature> <plan-number>`

Example: `/implement websocket-notifications 01`

## Your Task

Execute the specified plan for "$ARGUMENTS".
**Tip:** For complex plans, use Plan Mode (`Shift+Tab`) to strategize the execution steps before writing code.

### Principle Reminder (Use Skills Library)

Apply **Karpathy Principles** from `docs/skills.md` during implementation:

- Surgical Changes (minimize diff, avoid drive-by refactors)
- Goal-Driven Execution (verify after each task; loop until proven)

### Step 1: Load Plan

1. Read `docs/planning/work/features/[feature]/[NN]-PLAN.md`
2. Read `docs/planning/work/features/[feature]/[NN]-PLAN.json` (contract)
3. Read `docs/planning/work/features/[feature]/CONTEXT.md` for decisions
4. Verify prerequisites are met

If plan not found, list available plans and ask user to specify.

### Step 2: Execute Tasks

For each task in the plan:

1. **Announce** — "Starting Task N: [name]"
2. **Read** — Load the files mentioned in the task
3. **Implement** — Make the changes as specified
4. **Verify** — Run the verification command
5. **Report** — "Task N complete" or "Task N failed: [reason]"

If verification fails:
- Diagnose the issue
- Fix and re-verify
- If stuck after 2 attempts, pause and ask user

### Step 3: Run Plan Verification

After all tasks, run the plan's verification commands.

### Step 4: Commit

Create atomic commit with the message from the plan:
```bash
git add -A
git commit -m "[commit message from plan]"
```

### Step 5: Create Summary

Create/update `docs/planning/work/features/[feature]/[NN]-SUMMARY.md`:

```markdown
# Plan NN Summary

## Outcome
✅ Complete | ⚠️ Partial | ❌ Failed

## Changes Made

| File | Change |
|------|--------|
| `path/to/file` | [what changed] |

## Verification Results

- Task 1: ✅ [output]
- Task 2: ✅ [output]
- Task 3: ✅ [output]
- Plan verification: ✅ [output]

## Issues Encountered

[Any problems and how they were resolved]

## Commit

`abc123f` - [commit message]

---
*Implemented: [date]*
```

Also create a machine-checkable contract:

- `docs/planning/work/features/[feature]/[NN]-SUMMARY.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per summary: `NN-SUMMARY.md` + `NN-SUMMARY.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Outcome required**: `outcome` MUST be `complete|partial|failed`.
- **Validation**: run `python3 scripts/workflow_validate.py` after writing the summary.

Contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "planNumber": "01",
  "outcome": "complete|partial|failed",
  "changes": [{ "file": "path/to/file", "change": "what changed" }],
  "verification": [{ "task": 1, "result": "pass|fail", "details": "..." }],
  "commit": { "hash": "abc123f", "message": "..." },
  "timestamp": "2026-01-24T00:00:00Z"
}
```

### Step 6: Update State

Update `docs/planning/STATE.md`:
```
## Current Focus
- Feature: [feature]
- Plan 01: ✅ Complete
- Plan 02: 🔄 In progress
- Next: /implement [feature] 02
```

## Output

After completion:
- Summary of changes
- Any issues encountered
- Next plan to execute (if any)
- Or ready for `/review` if all plans complete

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
