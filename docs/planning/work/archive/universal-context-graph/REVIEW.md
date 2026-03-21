# Universal Context Graph — Standing Code Review

**Branch**: main (post-merge)
**Scope**: Full `.cnogo/scripts/context/` package — 29 files, ~7,080 LOC
**Date**: 2026-03-01

## Verdict: WARN (9/14)

The context graph is a solid v1 implementation with clean architecture and comprehensive feature coverage. However, multiple concerns across security, performance, correctness, and maintainability prevent a clean pass. None are blockers individually, but the cumulative weight warrants a warn verdict.

---

## Scoring

| Axis | Score | Notes |
|------|-------|-------|
| Correctness | 1 | `add_relationships()` docstring/behavior mismatch; heritage hardcodes CLASS only; HybridSearch unused |
| Security | 1 | `exports.py:16` f-string interpolation in Cypher with dynamic file_path; 3 more controlled-value interpolations |
| Contract Compliance | 2 | All planning artifacts complete (8 plans, summaries, reviews, CONTEXT.json/md) |
| Performance | 1 | N+1 queries in impact.py and community.py; O(n^2) coupling; linear semantic search; no batch node insertion |
| Maintainability | 1 | 6+ phases access `storage._require_conn()` directly; all workflow functions access `g._storage`; cascade import failure from module-level kuzu |
| Test Coverage | 1 | 30 test files exist but all fail without kuzu installed due to eager import cascade; pure-Python parts untestable via package |
| Scope Discipline | 2 | Codebase is focused on stated purpose |

**Total: 9/14** — No 0s in critical axes, but 5 of 7 axes scored 1.

---

## Blockers (score = 0)

None.

## Concerns (score = 1)

### Security

1. **exports.py:16** — f-string interpolation of `file_path` directly into Cypher query:
   ```python
   f"MATCH (n:GraphNode) WHERE n.file_path = '{file_path}' AND n.label IN ..."
   ```
   If a file path contains single quotes (e.g., `file's_name.py`), this breaks the query or enables injection. Should use parameterized query (`$fp` parameter).

2. **community.py:48, coupling.py:41-43, storage.py:374** — String interpolation in Cypher `IN` clauses. Current callers only pass controlled enum constants, but the method signatures accept arbitrary strings. Low risk but poor pattern.

### Correctness

3. **storage.py:282** — `add_relationships()` docstring says "Duplicate rel_ids are silently skipped" but implementation uses `CREATE`, not `MERGE`. Duplicate rel_ids will create duplicate relationships in the graph.

4. **heritage.py** — `_build_class_index()` hardcodes lookup to `NodeLabel.CLASS` only. Nodes with `NodeLabel.INTERFACE` label won't be found as parents/children for EXTENDS/IMPLEMENTS relationships.

5. **__init__.py:156-158** — `ContextGraph.search()` delegates to `storage.search()` (CONTAINS-based, 3-field scoring). The purpose-built `HybridSearch` engine in `search.py` (BM25 + semantic + fuzzy via Reciprocal Rank Fusion) is completely unused by the main API.

### Performance

6. **impact.py:81** — `storage.get_node(node_id)` called per node in BFS loop (N+1 pattern). Then again at line 105 for the same nodes when building results. Should pre-fetch or cache.

7. **community.py:120** — `_query_node_name(storage, nid)` called per member node in every community. Each call does a full node-by-ID query. Should batch-fetch all member nodes.

8. **coupling.py:98-99** — O(n^2) pairwise comparison of all symbol nodes. Acceptable for small codebases but will not scale.

9. **search.py `_semantic_search()`** — Linear O(n) scan over all embeddings per query. No approximate nearest neighbor index.

10. **storage.py:165** — `add_nodes()` executes one MERGE+SET per node. No batch optimization.

### Maintainability

11. **Private API access** — 6 phase files directly call `storage._require_conn()` to run raw Cypher:
    - `imports.py:21`, `calls.py:22`, `heritage.py`, `exports.py:14`, `community.py:47`, `coupling.py:40`

    All 6 workflow functions in `workflow.py` access `g._storage` directly. This breaks encapsulation — storage internals can't change without updating 12+ call sites.

12. **Module-level kuzu import** — `storage.py` imports `kuzu` at line 15. `__init__.py` re-exports `GraphStorage` at module level (line 11). This means importing *any* symbol from `scripts.context` requires kuzu installed — even `GraphNode`, `NodeLabel`, `walk()`, etc. Pure-Python components are unnecessarily coupled to the C-extension dependency.

13. **Fragile positional destructuring** — `_row_to_node()` (storage.py:75) unpacks a 15-element list positionally. Adding/reordering columns in the schema will silently corrupt data instead of raising clear errors.

14. **Duplicate logic** — `_is_entry_point()` exists in both `dead_code.py` and `flows.py` with identical implementation.

### Test Coverage

15. **Cascade import failure** — All 30 test files fail with `ModuleNotFoundError: No module named 'kuzu'` when run outside the project venv. The eager import cascade means even tests for pure-Python components (model, walker, parser_base) fail.

---

## Improvements (non-blocking suggestions)

1. **Wire HybridSearch into ContextGraph** — The RRF-based search in `search.py` is significantly more capable than the CONTAINS-based search in `storage.py`. Consider `ContextGraph.search()` delegating to `HybridSearch` when embeddings are available, falling back to CONTAINS.

2. **Add public query methods to GraphStorage** — Instead of phases calling `_require_conn()`, add methods like `get_symbol_nodes_by_file(file_path)`, `get_symbol_index()`, `get_class_index()`. This keeps Cypher queries centralized.

3. **Lazy imports in `__init__.py`** — Defer `from scripts.context.storage import GraphStorage` to inside `ContextGraph.__init__()`. This would let `from scripts.context.model import GraphNode` work without kuzu.

4. **Batch node insertion** — Use KuzuDB's `COPY FROM` or batch parameter binding instead of per-node MERGE loops.

5. **Pre-fetch nodes in BFS** — In `impact.py`, fetch all candidate nodes once into a dict before starting BFS instead of querying per-node.

6. **Extract shared `_is_entry_point()`** — Move to a shared utility in the phases package.

---

## Evidence

- Read all 29 source files in `.cnogo/scripts/context/` (~7,080 LOC)
- Attempted test suite: 30 test files, all fail with `ModuleNotFoundError: No module named 'kuzu'` (system Python 3.14 lacks kuzu)
- Previous review (Plan 08): 118/118 tests passing in project venv, 18 CLI subcommands verified
- Cross-referenced storage.py schema DDL against `_row_to_node()` column order
- Verified string interpolation patterns against KuzuDB parameterized query support

## Next Actions

- **Fix exports.py:16** — Replace f-string with parameterized `$fp` query (security)
- **Fix add_relationships() docstring or implementation** — Either use MERGE or remove dedup claim (correctness)
- **Wire HybridSearch into API** — The search.py engine is purpose-built but unused (correctness/value)
- **Add public storage methods for phase queries** — Reduce `_require_conn()` call sites (maintainability)
- **Lazy-import storage in __init__.py** — Break kuzu cascade dependency (maintainability/testability)

---
*Reviewed: 2026-03-01 — Standing code review on main*
