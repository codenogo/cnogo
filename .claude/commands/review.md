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

### Step 3: Focused Manual Pass

Review high-risk areas not fully covered by automated checks:
- Security boundaries (auth, input validation, secrets, sensitive logging)
- Contract compatibility (API/schema/backward compatibility)
- Failure behavior (timeouts, retries, error surfaces)
- Test quality (edge cases and non-flaky behavior)
- Scope hygiene (no drive-by refactors)

Apply these skills in order for consistent review quality:
- `.claude/skills/code-review.md`
- `.claude/skills/boundary-and-sdk-enforcement.md`
- `.claude/skills/workflow-contract-integrity.md`
- `.claude/skills/artifact-token-budgeting.md`

Use Karpathy principles from `CLAUDE.md` as the decision rubric. Do not restate full principle text in artifacts; fill `principles[]` status/notes in `REVIEW.json`.

### Step 4: Verdict

Use `REVIEW.json.verdict`:
- `fail`: block merge; list blockers
- `warn`: call out risks and ask user whether to proceed
- `pass`: ready for `/ship`

If accepted (`pass` or approved `warn`) and memory is enabled:

```bash
python3 scripts/workflow_memory.py phase-set <feature-slug> ship
```

## Output

- Review verdict (`pass|warn|fail`)
- Key blockers/warnings with file references
- Token-savings summary from automated checks
- Clear next action (`fix`, `ship`, or `follow-up`)
