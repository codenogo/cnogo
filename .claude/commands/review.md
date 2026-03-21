# Review
<!-- effort: medium -->

Quality gate.

## Your Task

## Steps

1. **Branch + scope**
   - Check `git branch --show-current` and `git status --porcelain`.
   - Review should run on `feature/<feature-slug>`.
   - Run `python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>`; expected phase: `implement` or `review`.
   - Load the feature-level Work Order with `python3 .cnogo/scripts/workflow_memory.py work-show <feature-slug> --json`.
   - Load the latest Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-show <feature-slug> --json`.
   - If `planVerifyPassed=true` but `reviewReadiness.status != ready`, run `python3 .cnogo/scripts/workflow_memory.py run-review-ready <feature-slug> --json` once, then reload the Delivery Run.
   - Stop unless `reviewReadiness.status == ready`, unless the Delivery Run already has `review.status == in_progress|completed`.

2. **Automated review**
   - Run `python3 .cnogo/scripts/workflow_checks.py review --feature <feature-slug>`.
   - This must stop if there is no linked Delivery Run, or if the latest run is not review-ready.
   - On a review-ready run, it writes `REVIEW.md` and `REVIEW.json` with `automatedVerdict` and `verdict: pending`, auto-syncs the linked Delivery Run into `review.status = in_progress`, and merges profile-required reviewers into `REVIEW.json.reviewers[]`.
   - Validate with `python3 .cnogo/scripts/workflow_validate.py --json --feature <feature-slug>`.

3. **Stage 1: spec compliance**
   - Check plan intent, contract compliance, and changed-scope discipline.
   - Update `REVIEW.json stageReviews[0]` with `pass|warn|fail`, findings, evidence.
   - If you edit `REVIEW.json` manually, re-sync with `python3 .cnogo/scripts/workflow_memory.py run-review-sync <feature-slug>`.
   - If this stage fails, stop.

4. **Stage 2: code quality**
   - Apply `.claude/skills/performance-review.md` plus code review, security, release-readiness, workflow-contract-integrity, and artifact-token-budgeting.
   - If Agent Teams is enabled and `WORKFLOW.json.agentTeams.defaultCompositions.review` is configured, always spawn that set first (`code-reviewer`, `security-scanner`, `perf-analyzer`).
   - Record the spawned reviewer agent names in `REVIEW.json.reviewers[]`.
   - Update `stageReviews[1]`, `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]`, and `principleNotes[]`.
   - Re-run the validator. If you edited `REVIEW.json` manually, run `python3 .cnogo/scripts/workflow_memory.py run-review-sync <feature-slug>`.

5. **Verdict**
   - Use the 7-axis rubric from `.claude/skills/performance-review.md`.
   - Set `pass`, `warn`, or `fail`.
   - `REVIEW.json.verdict` stays `pending` until both stage reviews are complete. Only then set it to `pass|warn|fail`.
   - Sync the final artifact with `python3 .cnogo/scripts/workflow_memory.py run-review-sync <feature-slug>`.
   - Confirm Work Order review state with `python3 .cnogo/scripts/workflow_memory.py work-next <feature-slug> --json`.
   - If accepted and memory is enabled, run `python3 .cnogo/scripts/workflow_memory.py phase-set <feature-slug> ship`.
