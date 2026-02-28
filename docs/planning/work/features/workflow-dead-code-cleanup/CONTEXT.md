# Workflow Dead Code Cleanup

## Goal

Remove dead code, stale artifacts, and outdated comments identified through a comprehensive codebase audit.

## Audit Findings

### Dead Functions (11 in `.cnogo/scripts/memory/__init__.py`)

Exported in `__all__` but never called externally:

| Function | Origin Module |
|----------|--------------|
| `plan_to_task_descriptions` | core.py |
| `generate_implement_prompt` | core.py |
| `detect_file_conflicts` | core.py |
| `create_session` | sessions.py |
| `get_conflict_context` | core.py |
| `save_session` | sessions.py |
| `run_watchdog_checks` | watchdog.py |
| `load_ledger` | ledger.py |
| `save_ledger` | ledger.py |
| `create_ledger` | ledger.py |
| `check_stale_tasks` | core.py |

### Stale Planning Artifacts (3 orphaned features)

| Feature | State | Issue |
|---------|-------|-------|
| `event-hardening` | REVIEW-only | No CONTEXT or PLANs |
| `context-engineering-fixes` | CONTEXT + REVIEW | No PLANs or SUMMARYs |
| `overstory-workflow-patterns` | 3 PLANs, no SUMMARYs | Last touched 2026-02-14 |

### Outdated Comments

- "Phase 3" stubs in `memory/__init__.py` reference future work that's already completed or superseded.

## Decisions

1. **Remove 11 dead function wrappers** from `.cnogo/scripts/memory/__init__.py` and their `__all__` entries
2. **Archive 3 stale feature directories** to `docs/planning/work/archive/`
3. **Remove outdated Phase 3 comments** in memory package
4. **Keep** wrapper script pattern (`workflow_checks.py` / `workflow_validate.py`) — intentional design
5. **Keep** `_repo_root()` variant in `workflow_validate_core.py` — functional difference, not duplication
6. **Leave** old config key references in historical planning docs — historical record

## Constraints

- stdlib-only
- Must pass `workflow_validate.py` after all changes
- Dead function removal must not break any import paths
- Archive preserves original structure
