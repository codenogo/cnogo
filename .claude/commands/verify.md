# Verify: $ARGUMENTS
<!-- effort: high -->

User acceptance testing. Confirms the feature actually works as expected.

## When to Use

After all plans for a feature are implemented, before `/review`.

## Your Task

Verify "$ARGUMENTS" works end-to-end from a user's perspective.

### Note: CI vs Human Verification

- Use `/verify-ci $ARGUMENTS` for non-interactive checks (CI-friendly).
- Use `/verify $ARGUMENTS` for human acceptance testing (this command).

### Step 1: Load Feature Context

```bash
# Read what was built
cat docs/planning/work/features/$ARGUMENTS/CONTEXT.md
cat docs/planning/work/features/$ARGUMENTS/*-SUMMARY.md
```

### Step 2: Extract Testable Deliverables

From CONTEXT.md and summaries, identify what the user should now be able to do:

```markdown
## Deliverables to Verify

1. [ ] User can [action 1]
2. [ ] User can [action 2]
3. [ ] System handles [edge case]
4. [ ] Error shows when [error condition]
```

### Step 3: Walk Through Each Deliverable

For each deliverable:

1. **Present** — "Can you verify: [deliverable]?"
2. **Wait** — User tests manually
3. **Record** — User responds: ✅ Pass | ❌ Fail | ⚠️ Partial

If user reports failure:
- Ask for specific symptoms
- Note exact error messages
- Capture steps to reproduce

### Step 4: Technical Verification

1. **Check Logs:**
   ```bash
   # If Sentry MCP is configured:
   claude mcp use sentry query "issue.handled:no"
   
   # Or check local logs:
   [grep commands for local logs]
   ```

2. **Check Coverage:**
   If confidence is low, spawn a test generation agent:
   ```bash
   /spawn tests Generate integration tests for this feature
   ```

### Step 5: Diagnose Failures

For each failure, spawn a debug investigation:

```markdown
## Failure: [Deliverable]

**Symptoms:** [What user observed]
**Expected:** [What should have happened]
**Steps to reproduce:**
1. [Step]
2. [Step]

### Investigation

[Search relevant code]
[Check logs if available]
[Identify root cause]

### Fix Required

**File:** `path/to/file.ts`
**Issue:** [What's wrong]
**Fix:** [What needs to change]
```

### Step 6: Create Fix Plans (if failures found)

For each failure, create a fix plan:

`docs/planning/work/features/$ARGUMENTS/FIX-NN-PLAN.md`

```markdown
# Fix Plan: [Issue]

## Problem
[Root cause from investigation]

## Tasks

### Task 1: [Fix]
**Files:** `path/to/file.ts`
**Action:** [Specific fix]
**Verify:** [How to verify fix]
```

### Step 7: Generate Verification Report

Create:

- `docs/planning/work/features/$ARGUMENTS/VERIFICATION.md`
- `docs/planning/work/features/$ARGUMENTS/VERIFICATION.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per verification: `VERIFICATION.md` + `VERIFICATION.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Validation**: run `python3 scripts/workflow_validate.py` after writing the artifacts.

`VERIFICATION.json` contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "timestamp": "2026-01-24T00:00:00Z",
  "results": [
    { "deliverable": "User can ...", "status": "pass|fail|partial", "notes": "..." }
  ],
  "failed": [{ "deliverable": "User can ...", "fixPlan": "FIX-01-PLAN.md" }]
}
```

For the human-readable report, create `docs/planning/work/features/$ARGUMENTS/VERIFICATION.md`:

```markdown
# Verification Report: $ARGUMENTS

## Summary

| Status | Count |
|--------|-------|
| ✅ Passed | N |
| ❌ Failed | N |
| ⚠️ Partial | N |

## Results

### ✅ Passed

1. User can [action] — Verified [date]

### ❌ Failed

1. User can [action]
   - **Symptom:** [what happened]
   - **Root cause:** [why]
   - **Fix plan:** `FIX-01-PLAN.md`

### ⚠️ Partial

1. User can [action]
   - **Works:** [what works]
   - **Doesn't work:** [what doesn't]
   - **Fix plan:** `FIX-02-PLAN.md`

## Next Steps

- [ ] Execute fix plans: `/implement $ARGUMENTS FIX-01`
- [ ] Re-verify after fixes

---
*Verified: [date]*
```

## Output

- Verification summary
- Fix plans created (if needed)
- Clear next action

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
