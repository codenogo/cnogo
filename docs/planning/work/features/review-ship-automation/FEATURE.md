# Feature: Review & Ship Automation

**Slug**: review-ship-automation
**Parent Shape**: control-plane-consolidation
**Priority**: P1

## User Outcome

When profile allows, review starts automatically after review-readiness and ship starts automatically after review passes. Manual gates preserved for profiles that require them. The loop goes from implementation-complete to PR-created without operator intervention for high-autonomy profiles.

## Scope

### Auto-Review (dispatcher tick)

1. **Detection**: After auto-plan, scan lanes in `implementing` status where `review_readiness == "ready"` and `profile_auto_review(profile) == True`.
2. **Invoke**: Call `write_review()` to generate REVIEW.json with automated verdict from checks + invariants.
3. **Stage completion**: Auto-complete both stages (`spec-compliance`, `code-quality`) using the automated verdict. Set findings from the automated check output.
4. **Verdict**: Set final verdict to match the automated verdict (pass/warn/fail).
5. **Sync**: Update delivery run review state + work order.

### Auto-Ship (dispatcher tick)

1. **Detection**: Scan lanes where `ship.status == "ready"` and `profile_auto_ship(profile) == True`.
2. **Start**: Call `start_ship(run)` to transition to `in_progress`.
3. **Draft**: Call `build_ship_draft(root, feature)` to get commit surface, message, and PR body.
4. **Stage result**: Store the draft in the work order's automation state so the operator (human or agent) can see what would be committed.
5. **Git ops boundary**: The actual `git add/commit/push/gh pr create` stays outside the dispatcher. The dispatcher prepares everything and surfaces it. The patrol watches for stale `ship.in_progress` state.

### Work Order Automation State

6. **Profile policy surfacing**: Update `_automation_state()` in `work_order.py` to include profile policy hints (requires tracking, requires PR, auto-review allowed, auto-ship allowed).
7. **Next action enrichment**: When auto-review/auto-ship is available, automation state should say "auto-review will run on next dispatcher tick" instead of "run /review manually".

### Post-Ship Cleanup (patrol)

8. **Best-effort**: Patrol detects `ship.status == "completed"` and surfaces feature-lifecycle-closure as a finding, not a gate.

## Out of Scope

- Spawning reviewer agents (team mode integration — separate feature)
- Automatic git commit/push/PR creation inside the dispatcher (too risky without explicit opt-in)
- Changes to the phase system (handled by `lifecycle-auto-advance`)

## Key Files

| File | Change |
|------|--------|
| `dispatcher.py` | Add auto-review and auto-ship paths after auto-plan in dispatch tick |
| `work_order.py` | Surface profile policy in automation state |
| `watch.py` | Add post-ship cleanup finding |
| `review.py` (checks) | Ensure `write_review()` can be called programmatically from dispatcher |
| `review.py` (orchestration) | Ensure `start_review()` + `set_review_stage()` + `set_review_verdict()` work in headless mode |
| `ship.py` | Ensure `start_ship()` works in headless mode |
| `ship_draft.py` | No changes needed — already returns structured data |

## Success Criteria

- Dispatcher auto-reviews lanes where profile allows and review is ready
- Dispatcher auto-starts ship where profile allows and review passes
- Work order automation state includes profile policy hints
- Patrol surfaces post-ship cleanup as finding
- Manual profiles (`autoReview: false`) are unaffected
- All 106+ existing tests pass + new tests for auto-review and auto-ship paths
