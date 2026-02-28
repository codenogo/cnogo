# Review
<!-- effort: medium -->

Comprehensive quality gate before merge, optimized for package-aware automation.

## Your Task

Review current changes for correctness, safety, and ship readiness.

### Step 0: Phase Check (Warn, Do Not Block)

If memory is enabled and feature slug is known:

```bash
python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>
```

Expected before `/review`: `implement` or `review`.

### Step 1: Scope

Collect quick context (changed files + branch state):

```bash
git branch --show-current
git status --porcelain
git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only
```

### Step 2: Run Automated Review (Primary Path)

Run package-aware checks and write artifacts in one step:

```bash
python3 .cnogo/scripts/workflow_checks.py review --feature <feature-slug>
```

If feature slug is unknown, omit the flag:

```bash
python3 .cnogo/scripts/workflow_checks.py review
```

If `WORKFLOW.json` has empty `packages[]`, the checker auto-runs:
`python3 .cnogo/scripts/workflow_detect.py --write-workflow`
then continues.

This writes:
- `docs/planning/work/features/<feature>/REVIEW.md`
- `docs/planning/work/features/<feature>/REVIEW.json`
- Includes token telemetry (`tokenTelemetry`) and compact output with optional `fullOutputPath` hints for failed checks.

Or (if no feature inferred):
- `docs/planning/work/review/<timestamp>-REVIEW.md`
- `docs/planning/work/review/<timestamp>-REVIEW.json`

Then validate workflow artifacts:

```bash
python3 .cnogo/scripts/workflow_validate.py --json --feature <feature-slug>
```

### Step 3: Stage 1 — Spec Compliance (must run first)

Run a strict spec pass before any code-quality judgment:

1. Scope + intent match vs plan goal
2. Contract compliance (artifacts + lifecycle)
3. Changed-scope discipline (no drive-by edits)

Update `REVIEW.json`:
- `stageReviews[0].stage = "spec-compliance"`
- set `stageReviews[0].status = pass|warn|fail`
- fill `stageReviews[0].findings[]` + `stageReviews[0].evidence[]`

If spec stage is `fail`, stop and return blockers.

### Step 4: Stage 2 — Code Quality (only after spec stage passes)

Apply `.claude/skills/performance-review.md` and supporting skills:
- `.claude/skills/code-review.md`
- `.claude/skills/security-scan.md`
- `.claude/skills/release-readiness.md`
- `.claude/skills/boundary-and-sdk-enforcement.md`
- `.claude/skills/workflow-contract-integrity.md`
- `.claude/skills/artifact-token-budgeting.md`

Update `REVIEW.json`:
- `stageReviews[1].stage = "code-quality"`
- set `stageReviews[1].status = pass|warn|fail`
- fill `stageReviews[1].findings[]` + `stageReviews[1].evidence[]`
- fill `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]`, `principleNotes[]`

Re-run validator after stage updates:

```bash
python3 .cnogo/scripts/workflow_validate.py --json --feature <feature-slug>
```

### Step 5: Verdict

Score 7 axes (0-2 each) per `.claude/skills/performance-review.md` rubric:

- **Pass** (≥ 11/14, no 0 in Correctness/Security/Contract Compliance): ready for `/ship`
- **Warn** (≥ 11/14 with concerns, or 9-10): call out risks and ask user whether to proceed
- **Fail** (< 9, or any 0 in Correctness/Security/Contract Compliance): block merge; list blockers

If accepted (`pass` or approved `warn`) and memory is enabled:

```bash
python3 .cnogo/scripts/workflow_memory.py phase-set <feature-slug> ship
```

## Output

- Review verdict (`pass|warn|fail`)
- Key blockers/warnings with file references
- Token-savings summary from automated checks
- Clear next action (`fix`, `ship`, or `follow-up`)
