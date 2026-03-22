# Context: lifecycle-auto-advance

## Current State

Phase truth is dual-tracked:
- **Old**: `memory.db` issues.phase + `.cnogo/feature-phases.json` — set manually via `phase-set`
- **New**: Work order status derived from delivery run + lane + review + ship state

The new model is canonical but the old phase isn't auto-synced. This causes stale phase display, wrong-phase warnings in commands, and user confusion.

## Key Files

| File | Role |
|------|------|
| `.cnogo/scripts/workflow/orchestration/work_order.py` | `sync_work_order()`, `_phase_from_status()`, `_derive_status()` |
| `.cnogo/scripts/memory/phases.py` | `set_feature_phase()`, `get_feature_phase()` |
| `.cnogo/scripts/memory/storage.py` | SQLite phase storage |
| `.cnogo/scripts/workflow/orchestration/watch.py` | Patrol findings |
| `.cnogo/scripts/workflow_memory.py` | CLI `phase-set`, `phase-get` commands |
| `.claude/commands/review.md` | Review command (reads phase) |
| `.claude/commands/ship.md` | Ship command (reads phase) |

## Existing Mapping

`_phase_from_status()` in `work_order.py` already maps:
- `queued|leased|planning|planned` → `plan`
- `implementing` → `implement`
- `reviewing` → `review`
- `shipping` → `ship`

`set_feature_phase()` in `phases.py` already:
- Validates forward-only transitions (warns on backward)
- Writes to both `feature-phases.json` and `memory.db`
- Triggers JSONL auto-export

## Decisions

- Phase auto-advance is a side-effect of `sync_work_order()`, not a separate job
- Backward transition warnings are suppressed during auto-sync
- Manual `phase-set` is preserved but deprecated
- Commands migrate to work order status first, phase as fallback

## Constraints

- No new dependencies
- Must not break existing 106 tests
- Must handle features not yet in work order system (fallback to phase)
