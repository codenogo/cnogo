# Shape: Control-Plane Consolidation

**Initiative**: control-plane-consolidation
**Status**: Active — most foundations landed, finishing the delta

---

## Problem

cnogo's lifecycle was split between two models: the old memory-phase system (`discuss` → `plan` → `implement` → `review` → `ship`) and the new Work Order/Lane/Delivery Run control plane. The new model is now substantially real — lanes lease work, dispatcher auto-plans, observations flow back to shape — but transitional seams remain. Phase truth is still dual-tracked, review and ship gates are manual where they could be automatic, and the memory layer captures observations but doesn't yet use them to make the loop smarter.

## What's Already Landed

| Component | Module | Status |
|-----------|--------|--------|
| Feature lanes with lease/heartbeat/reclaim | `lane.py` | Complete, tested |
| Work orders with automation state + lane health | `work_order.py` | Complete, tested |
| Dispatcher: ready → queued → leased → planned | `dispatcher.py` | Complete, tested |
| Deterministic plan factory | `plan_factory.py` | Complete, tested |
| Shape feedback sync (contradictions, attention, review findings) | `dispatcher.sync_shape_feedback()` | Complete, tested |
| Runtime root abstraction for worktrees | `runtime_root.py` | Complete |
| Observations, contradictions, cards | `insights.py` | Complete, tested |
| Context generation (prime/checkpoint with work order focus) | `context.py` | Functional, basic |
| `/discuss` deprecated → redirects to `/shape` | `discuss.md` | Done |
| CLI: dispatch-ready, plan-auto, lane-*, work-order-* | `workflow_memory.py` | Done |
| 106 tests passing | test suite | Green |

## What's Still Partial

### 1. Phase auto-advance is missing

The old phase system (`feature-phases.json` + `memory.db`) doesn't auto-sync from work order status. When a delivery run reaches `reviewing`, the phase stays at `implement` until someone manually calls `phase-set`. This causes:
- `/ship` warns about wrong phase even though work order says shipping
- `prime()` shows stale phase information
- State divergence between old and new systems

### 2. Review and ship stages have unnecessary manual gates

Review readiness is derived automatically, but `/review` must be invoked manually even when the profile says `autoReview: true`. Ship readiness is derived automatically, but `/ship` must be invoked manually even when the profile says `autoShip: true`. The profile hooks (`profile_auto_review()`, `profile_auto_ship()`) exist in code but aren't wired into the dispatcher or patrol.

**Resolution**: All building blocks exist — `write_review()` generates automated verdicts, `build_ship_draft()` generates full drafts, profile hooks return booleans. The fix is wiring: extend the dispatcher tick to auto-review and auto-ship after auto-plan, following the same scan-check-call-sync-report pattern. Auto-ship prepares the draft but does NOT execute git ops (safety boundary). Promoted to `ready`.

### 3. Post-ship cleanup is not automated

Ship completion marks the work order as `completed` but doesn't:
- Auto-advance phase to `ship`
- Run feature-lifecycle-closure checks
- Clean up lane/worktree resources
- File follow-up items from review findings

### 4. Context generation is minimal

Observations and contradictions are persisted correctly but `prime()` output is basic. No feature-specific context composition around active work orders and lanes. Cards exist but aren't deeply used in context synthesis.

## Constraints

| Constraint | Source |
|------------|--------|
| Python stdlib only | PROJECT.md |
| No external services | PROJECT.md |
| Max 3 tasks per plan | WORKFLOW contract |
| Forward-only phase transitions (advisory) | Memory engine |
| 106 tests must stay green | Current baseline |

## Global Decisions

1. **The new model is canonical.** Work Order + Lane + Delivery Run is the source of truth. Old phase becomes a derived, compatibility-only view.
2. **Phase auto-advance is a side-effect of work order sync.** When work order status changes, phase is updated automatically. No more manual `phase-set`.
3. **Profile automation hooks drive the loop.** `autoReview`, `autoShip`, `autoPlan` in profile config determine whether transitions are automatic or manual.
4. **Patrol owns recovery and escalation.** Stale lanes, failed reviews, and stuck ships get escalated by patrol, not by the user remembering to check.

## Recommended Sequence

```
1. lifecycle-auto-advance (P0)
2. review-ship-automation (P1)
3. memory-context-depth (P2)
```

---

## Next Shaping Moves

- Materialize `lifecycle-auto-advance` as a ready feature (all dependencies resolved, scope clear)
- `review-ship-automation` depends on `lifecycle-auto-advance` (needs phase truth to be canonical first)
- `memory-context-depth` is independent but lower priority — can run in parallel with review-ship-automation
