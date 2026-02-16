# Verify CI: $ARGUMENTS
<!-- effort: medium -->

Non-interactive verification for CI/nightly/pre-merge.

## Arguments

`/verify-ci <feature>`

## Your Task

Run automated verification for `$ARGUMENTS` and persist machine-checkable artifacts.

### Step 1: Quick Sanity Check

```bash
ls docs/planning/work/features/$ARGUMENTS >/dev/null
```

If the feature directory does not exist, stop and ask for the correct slug.

### Step 2: Run Package-Aware Verification (Primary Path)

```bash
python3 scripts/workflow_checks.py verify-ci $ARGUMENTS
```

This writes:
- `docs/planning/work/features/$ARGUMENTS/VERIFICATION-CI.md`
- `docs/planning/work/features/$ARGUMENTS/VERIFICATION-CI.json`

If no packages are configured in `WORKFLOW.json`, checks are recorded as skipped (artifact still written).

### Step 3: Validate Workflow Artifacts

```bash
python3 scripts/workflow_validate.py
```

## Output

- Overall CI status (lint/types/tests/invariants)
- Location of written artifacts
- Recommended next action (`/review`, fix failures, or update WORKFLOW packages)
