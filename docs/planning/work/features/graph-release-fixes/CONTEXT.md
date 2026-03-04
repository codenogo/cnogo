# Graph Release Fixes (P0/P2/P3)

## Problem

Three bugs block release-readiness. Two P1 proximity findings are tracked separately in `feature/graph-proximity`.

## Findings

| ID | Priority | Issue |
|----|----------|-------|
| P0-kuzu-not-in-syntax | P0 | `get_reverse_dependency_files()` uses `NOT IN` which Kuzu rejects. Incremental reindex crashes. |
| P2-hook-silent-skip | P2 | Post-commit hook returns 0 with weak warning when graph venv absent. |
| P3-graph-stats-relationships | P3 | `_graph_stats()` omits `relationships` count from JSON output. |

## Decisions

| Area | Decision |
|------|----------|
| P0 fix | Change `n.file_path NOT IN [...]` to `NOT n.file_path IN [...]`. Add regression test. |
| P2 fix | Keep exit 0, improve warning to include actionable guidance. |
| P3 fix | Add `relationships: relationship_count()` to `_graph_stats()`. |

## Out of Scope

- P1 graph-prioritize API drift → `feature/graph-proximity`
- P1 Proximity feature not implemented → `feature/graph-proximity`

## Constraints

- Stdlib only, parameterized Cypher, hooks must not block commits
- Max 3 tasks per plan

## Related Code

- `.cnogo/scripts/context/storage.py` — P0 fix
- `.cnogo/scripts/workflow_hooks.py` — P2 fix
- `.cnogo/scripts/workflow_memory.py` — P3 fix
- `tests/test_context_storage.py` — P0 regression test
