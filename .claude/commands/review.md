# Review
<!-- effort: medium -->

Comprehensive quality gate before merge, optimized for package-aware automation.

## Your Task

Review current changes for correctness, safety, and ship readiness.

### Step 0: Phase Check (Warn, Do Not Block)

If memory is enabled and feature slug is known:

```bash
python3 scripts/workflow_memory.py phase-get <feature-slug>
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
python3 scripts/workflow_checks.py review --feature <feature-slug>
```

If feature slug is unknown, omit the flag:

```bash
python3 scripts/workflow_checks.py review
```

If `WORKFLOW.json` has empty `packages[]`, the checker auto-runs:
`python3 scripts/workflow_detect.py --write-workflow`
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
python3 scripts/workflow_validate.py
```

### Step 3: Performance Review (Final Gate)

Apply `.claude/skills/performance-review.md` as the primary final-gate review procedure. This orchestrates sub-skills in a deterministic 6-step sequence with a 7-axis scoring rubric:

1. **Scope + Intent** — changes match plan goal, no out-of-scope modifications
2. **Code Review Checklist** — via `.claude/skills/code-review.md`
3. **Contract Compliance** — planning artifacts + multi-agent safety
4. **Security / OWASP Quick Pass** — via `.claude/skills/security-scan.md`
5. **PRR-lite** — via `.claude/skills/release-readiness.md`
6. **Validation Baseline Diff** — verify-before vs verify-after

Additional skill checks for workflow-specific concerns:
- `.claude/skills/boundary-and-sdk-enforcement.md`
- `.claude/skills/workflow-contract-integrity.md`
- `.claude/skills/artifact-token-budgeting.md`

Fill `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]` in `REVIEW.json`. Record scoring summary in `principleNotes[]`.

### Step 4: Verdict

Score 7 axes (0-2 each) per `.claude/skills/performance-review.md` rubric:

- **Pass** (≥ 11/14, no 0 in Correctness/Security/Contract Compliance): ready for `/ship`
- **Warn** (≥ 11/14 with concerns, or 9-10): call out risks and ask user whether to proceed
- **Fail** (< 9, or any 0 in Correctness/Security/Contract Compliance): block merge; list blockers

If accepted (`pass` or approved `warn`) and memory is enabled:

```bash
python3 scripts/workflow_memory.py phase-set <feature-slug> ship
```

## Output

- Review verdict (`pass|warn|fail`)
- Key blockers/warnings with file references
- Token-savings summary from automated checks
- Clear next action (`fix`, `ship`, or `follow-up`)
