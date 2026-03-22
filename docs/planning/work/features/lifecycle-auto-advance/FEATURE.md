# Feature: Lifecycle Auto-Advance

**Slug**: lifecycle-auto-advance
**Parent Shape**: control-plane-consolidation
**Priority**: P0

## User Outcome

Phase truth is always consistent with work order status. No manual `phase-set` needed. Patrol detects and remediates phase divergence. Commands read work order status as primary truth.

## Scope

1. **Phase auto-advance in work_order_sync**: When `sync_work_order()` derives a new status, call `set_feature_phase()` with the corresponding phase from `_phase_from_status()`. Handle backward-transition warnings gracefully (suppress when auto-syncing).
2. **Patrol phase consistency check**: Add a check to `watch.py` patrol that warns when `feature-phases.json` phase disagrees with work order derived phase. Auto-remediate by syncing phase forward.
3. **Command migration**: Update `/review` and `/ship` commands to read work order automation state as primary truth, with phase as fallback for features not yet in the work order system.
4. **Deprecation**: Mark manual `phase-set` as compatibility-only in CLI help. Add stderr notice when called manually that auto-advance is now the default path.

## Out of Scope

- Removing the phase system entirely (backward compat needed)
- Auto-starting review or ship (that's `review-ship-automation`)
- Changing observation/contradiction behavior (that's `memory-context-depth`)

## Risks

- Backward phase transition warnings during auto-sync if work order status regresses (e.g., from `shipping` back to `reviewing` on review fail). Mitigation: suppress backward warnings when triggered by auto-sync, only warn on manual phase-set.
- Commands that gate on phase may break if phase reads change. Mitigation: audit all phase-reading commands before changing.

## Success Criteria

- `sync_work_order()` auto-advances phase as side-effect
- Patrol detects and warns on phase/status divergence
- `/review` and `/ship` commands work correctly reading work order status
- All 106+ existing tests pass
- Manual `phase-set` still works but emits deprecation notice
