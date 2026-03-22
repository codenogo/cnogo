# Context: review-ship-automation

## Current State

The dispatcher can auto-plan features but stops there. After implementation completes, the operator must manually invoke `/review` then `/ship`. All the building blocks for automation exist but aren't wired together.

## Existing Automation Surface

| Component | Status | Location |
|-----------|--------|----------|
| `profile_auto_review()` | Implemented, returns bool | `profiles.py:449` |
| `profile_auto_ship()` | Implemented, returns bool | `profiles.py:527` |
| `write_review()` | Generates REVIEW.json with automated verdict | `checks/review.py` |
| `start_review()` + `set_review_stage()` + `set_review_verdict()` | Implemented | `orchestration/review.py` |
| `sync_review_state()` | Auto-derives review status | `orchestration/review.py` |
| `start_ship()` + `complete_ship()` | Implemented | `orchestration/ship.py` |
| `sync_ship_state()` | Auto-derives ship readiness | `orchestration/ship.py` |
| `build_ship_draft()` | Returns commit surface, message, PR body | `orchestration/ship_draft.py` |
| `ship_ready` gate | Comprehensive pre-ship validation | `checks/ship_ready.py` |
| Patrol staleness findings | Detects stuck review/ship states | `orchestration/watch.py` |
| `_automation_state()` | Shows current state + owner + reason | `orchestration/work_order.py` |

## Dispatcher Extension Pattern

The dispatcher already has this pattern for auto-plan (from the plan-factory work):
```
1. Scan lanes in relevant status
2. Check profile policy
3. Call existing function
4. Sync work order
5. Report success/skip/error
```

Auto-review and auto-ship follow the same pattern. The return payload from `dispatch_ready_work()` gets three new arrays: `autoReviewed`, `autoReviewSkipped`, `autoShipStarted`.

## Key Files

| File | Role |
|------|------|
| `.cnogo/scripts/workflow/orchestration/dispatcher.py` | Add auto-review + auto-ship after auto-plan |
| `.cnogo/scripts/workflow/orchestration/work_order.py` | Surface profile policy in automation state |
| `.cnogo/scripts/workflow/orchestration/watch.py` | Post-ship cleanup finding |
| `.cnogo/scripts/workflow/checks/review.py` | `write_review()` — headless invocation |
| `.cnogo/scripts/workflow/orchestration/review.py` | Stage/verdict automation |
| `.cnogo/scripts/workflow/orchestration/ship.py` | `start_ship()` headless invocation |
| `.cnogo/scripts/workflow/orchestration/ship_draft.py` | `build_ship_draft()` — no changes needed |
| `.cnogo/scripts/workflow/shared/profiles.py` | Profile hook source of truth |

## Decisions

- Auto-review generates REVIEW.json with automated verdict and auto-completes both stages. No reviewer agents spawned (that's a separate team-mode feature).
- Auto-ship prepares the draft and transitions to `in_progress` but does NOT execute git operations. The draft is stored in the automation state for the next operator (human or agent session) to execute.
- Post-ship cleanup is a patrol finding, not a completion gate.
- Git safety: auto-ship only marks `in_progress` — actual commit/push/PR is left to the operator.

## Constraints

- Python stdlib only
- No new dependencies
- 106+ tests must stay green
- Profile gating must be respected — `autoReview: false` means no auto-review
