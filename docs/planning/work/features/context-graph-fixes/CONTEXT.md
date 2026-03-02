# Context Graph Fixes

Address the 15 findings from the standing code review (WARN 9/14) of the universal context graph module.

## Source

[Standing Code Review](../universal-context-graph/REVIEW.md) — 2026-03-01

## Decisions

### Security (P0)
- **Parameterize all Cypher interpolation** — Replace f-string and string interpolation in `exports.py:16`, `community.py:48`, `coupling.py:41-43`, and `storage.py:374` with `$param` parameterized queries.

### Correctness (P1)
- **Fix `add_relationships()` docstring** — Update to match CREATE behavior. All callers already deduplicate via seen sets.
- **Fix heritage lookup** — Add `INTERFACE` and `TYPE_ALIAS` to `_build_class_index()` so TypeScript interface inheritance works.
- **Wire HybridSearch** — `ContextGraph.search()` should use `HybridSearch` (BM25+semantic+fuzzy) when embeddings exist, fall back to CONTAINS-based search otherwise.
- **Remove invalid `limit` param** — `cmd_graph_suggest_scope` and `cmd_graph_enrich` pass `limit=` that `suggest_scope()` / `enrich_context()` don't accept.
- **Fix task key `name` -> `title`** — Task description dicts use `"title"`, not `"name"`. CLI output scripts access wrong key.

### Maintainability (P2)
- **Lazy-import storage** — Move `from storage import GraphStorage` inside `ContextGraph.__init__()` to break the kuzu cascade import.
- **Add public storage methods** — Replace 12+ `_require_conn()` / `_storage` access sites with proper public methods on `GraphStorage`.
- **Extract `_is_entry_point()`** — Deduplicate identical logic from `dead_code.py` and `flows.py`.

### Performance (P2)
- **Pre-fetch in impact BFS** — Eliminate N+1 by building a node dict before BFS traversal.
- **Batch-fetch in community detection** — Replace per-member `_query_node_name()` with a single bulk query.

## Plan Strategy (3 plans, 3 tasks each)

| Plan | Focus | Tasks |
|------|-------|-------|
| 01 | Security + Quick Correctness + CLI Wiring | Parameterize Cypher, fix heritage+docstring, fix CLI wiring |
| 02 | Lazy Imports + Encapsulation | Lazy import, public storage methods, shared utility |
| 03 | Performance + HybridSearch | Impact N+1, community N+1, wire HybridSearch |

## Deferred

- O(n^2) coupling optimization
- Batch node insertion in `add_nodes()`
- ANN index for semantic search
- Multi-line signature extraction in `contracts.py`

## Constraints

- All 118 existing tests must pass
- No new external dependencies
- Backward-compatible ContextGraph API
- Storage schema unchanged

---
*Discussed: 2026-03-01, updated 2026-03-02*
