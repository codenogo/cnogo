# Context Engineering Fixes - Implementation Context

Apply all 6 improvements identified in the Manus context engineering review to improve cnogo's agent effectiveness.

**Source Review:** `docs/planning/work/review/2026-02-15-manus-context-engineering-REVIEW.md`

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| checkpoint() data source | Memory + plan artifacts | User chose richer context: read plan JSON for objective and remaining task names alongside memory state |
| Phase gating storage | Explicit `phase` column in issues table | User chose explicit over derived: more precise, enables programmatic transitions, worth the migration cost |
| history() function | New function in context.py | Returns formatted event log for error-learning; `show()` only returns current state, not the trail |
| Deterministic JSON | `sort_keys=True` on all json.dumps | Mechanical change across sync.py, bridge.py, storage.py, models.py |
| prime() restore hints | `verbose=True` param + footer hint | Keep default compact; verbose adds file paths from metadata and a restore command |
| Example diversity | Add "illustrative only" disclaimer to templates | Don't vary examples themselves (breaks cacheability); just clarify they're not to be copied literally |
| Schema migration | Bump SCHEMA_VERSION 1→2, ALTER TABLE ADD COLUMN | Safe: SQLite ADD COLUMN is atomic, backwards-compatible (new column has DEFAULT) |

## Constraints

- Python stdlib only — no external dependencies
- Max 3 tasks per plan — this feature will need 2 plans (6 fixes across ~10 files)
- Schema migration must be non-destructive (existing memory.db files must continue to work)
- `checkpoint()` must stay under 300 tokens output to remain useful as mid-execution injection
- `history()` should default to last 10 events, truncate data payloads to 200 chars

## Open Questions

- None — all decisions resolved during discussion

## Related Code

- `scripts/memory/context.py` — `prime()` lives here; `checkpoint()` and `history()` will be added here
- `scripts/memory/storage.py` — Schema, `migrate()`, `SCHEMA_VERSION`, `json.dumps()` calls
- `scripts/memory/bridge.py` — `generate_implement_prompt()` retry instructions, `json.dumps()` calls
- `scripts/memory/sync.py` — `export_jsonl()` uses `json.dumps(separators=...)` without sort_keys
- `scripts/memory/models.py` — `to_dict()` methods used by sync export
- `scripts/memory/__init__.py` — Public API surface; needs `checkpoint`, `history` exports
- `.claude/commands/implement.md` — Needs recitation step after each task completion
- `.claude/agents/implementer.md` — Needs retry-with-error-review instruction
- `.claude/commands/` (22 files with JSON examples) — Need "illustrative only" disclaimer

## Research

- `docs/planning/work/review/2026-02-15-manus-context-engineering-REVIEW.md` — Full gap analysis mapping 6 Manus lessons to cnogo

---
*Discussed: 2026-02-15*
