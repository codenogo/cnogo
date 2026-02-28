# Memory Engine Fixes - Implementation Context

## Background

The memory engine review (`docs/planning/work/review/20260214-memory-engine-REVIEW.md`) identified 1 critical blocker and 8 warnings. This feature addresses all of them across 3 plans grouped by theme.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Scope | All fixes (B-1, W-1, W-2, W-4, W-5, W-6, W-7, W-8) | Clean up all known issues in one feature cycle |
| W-3 (dynamic SQL) | Already fixed — `_ALLOWED_FIELDS` whitelist at `storage.py:223-227` | No code change needed; mark resolved |
| Concurrency | `BEGIN IMMEDIATE` + retry-on-busy with exponential backoff | Robustness under multi-agent high contention |
| Plan grouping | 3 plans by theme (sync, atomicity, graph safety) | Keeps related changes together for easier review |

## Scope Update (Planning Phase)

Code audit during planning revealed that **7 of 8 review issues were already fixed** in the current codebase (with tagged comments: B-1, W-1, W-4, W-5, W-6, W-7, W-8). Original 3-plan scope reduced to 1 plan.

### Already Fixed
| Issue | Evidence |
|-------|----------|
| B-1 (events export) | `sync.py:55,165` — events exported and imported |
| W-1 (child counter) | `__init__.py:140` — `BEGIN IMMEDIATE` |
| W-4 (schema validation) | `sync.py:26-31,217` — `_VALID_STATUSES/TYPES`, `_obj_to_issue()` |
| W-5 (DFS bound) | `__init__.py:628` — `_CYCLE_MAX_ITERATIONS = 10_000` |
| W-6 (claim lock) | `__init__.py:307` — `BEGIN IMMEDIATE` |
| W-7 (FK validation) | `sync.py:143-156` — `id_exists()` check |
| W-8 (stats txn) | `storage.py:572` — `BEGIN` + `ROLLBACK` |

### Plan 01: Remaining Fixes
| Task | Issue | Files |
|------|-------|-------|
| Consolidate `rebuild_blocked_cache` and fix W-2 | W-2 + dedup | `graph.py`, `__init__.py`, `sync.py` |
| Add retry-on-SQLITE_BUSY helper | New | `storage.py` |
| Wire retry into write operations | New | `__init__.py` |

## Constraints

- Python stdlib only — no external dependencies
- SQLite WAL mode must be preserved
- Existing public API signatures must not change (backwards compatible)
- Max 3 tasks per plan
- All changes must pass `python3 .cnogo/scripts/workflow_validate.py`

## Open Questions

- None — all decisions resolved during discussion

## Related Code

- `.cnogo/scripts/memory/__init__.py` — Public API (touched by all 3 plans)
- `.cnogo/scripts/memory/storage.py` — SQLite storage layer (touched by plans 1-3)
- `.cnogo/scripts/memory/sync.py` — JSONL sync (plan 1)
- `.cnogo/scripts/memory/graph.py` — Blocked cache and cycle detection (plan 3)
- `.cnogo/scripts/memory/context.py` — Context generation (read-only, unaffected)
- `.cnogo/scripts/memory/identity.py` — ID generation (read-only, unaffected)

## Review Reference

- `docs/planning/work/review/20260214-memory-engine-REVIEW.md`

---
*Discussed: 2026-02-14*
