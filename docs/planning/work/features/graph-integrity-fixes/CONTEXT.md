# Graph Integrity Fixes

Addresses 6 verified bugs in the context graph engine (P0–P2), defers 1 incomplete feature, and confirms 1 finding as already resolved.

## Verified Findings (6 open)

### P0: Incremental reindex drops cross-file edges
- **File**: `__init__.py:92-99`
- **Bug**: `remove_nodes_by_file()` deletes all edges for changed files, but edge-building phases only run on `new_or_changed` files. Unchanged callers to changed symbols lose their CALLS edges permanently.
- **Fix**: After removing changed-file nodes, re-run edge phases for ALL files that reference changed symbols (reverse-dependency scan), not just changed files.

### P1: HybridSearch cache stale after reindex
- **File**: `__init__.py:49,163`
- **Bug**: `_hybrid_search` is lazily initialized but never reset when `index()` rebuilds the graph. Subsequent `search()` returns stale/empty results.
- **Fix**: Reset `self._hybrid_search = None` at start of `index()`.

### P1: Heritage edges drop non-CLASS children
- **File**: `heritage.py:42`
- **Bug**: `generate_id(NodeLabel.CLASS, ...)` hardcoded for child lookup. Interfaces, enums, and type aliases have different label prefixes, so `get_node()` returns None and edges are silently skipped.
- **Fix**: Look up child name in `class_index` (same as parent), resolving to the actual node ID regardless of label.

### P1: review_impact() entries missing 'label' key
- **File**: `__init__.py:235`
- **Bug**: Dict entries lack `label` key. CLI formatter at `workflow_memory.py:1017` reads `e['label']`, causing `KeyError`.
- **Fix**: Add `"label": ir.node.label.value` to the entry dict.

### P2: graph-flows doesn't auto-index
- **File**: `workflow_memory.py:883`
- **Bug**: `cmd_graph_flows()` calls `graph.flows()` directly without `graph.index()`. Other commands auto-index. Fresh repos report zero flows.
- **Fix**: Add `graph.index()` before `graph.flows()`, matching `cmd_graph_dead()` / `cmd_graph_coupling()`.

### P2: context() contract drift
- **File**: `__init__.py:201-208`
- **Bug**: Returns `{node, callers, callees}` but CLI expects `{node, callers, callees, importers, imports, parent_classes, child_classes}`. Callers are `(node, confidence)` tuples but formatter expects plain nodes.
- **Fix**: Expand `context()` to query and return all 6 neighborhood keys. Return plain `GraphNode` lists (keep `callers_with_confidence()` as separate method).

## Deferred

- **P2: Proximity feature** — `proximity.py` absent, `prioritize_files()` missing. Existing `prioritize_context()` works. New feature, not a bug fix.

## Resolved

- **P3: Post-commit hook skip** — Returns 0 on skip, which is correct. Hooks should not block commits.

## Constraints

- stdlib-only for core modules (kuzu is the single storage dep)
- Parameterized Cypher queries only
- Max 3 tasks per plan
- Heritage fix must handle CLASS, INTERFACE, TYPE_ALIAS, ENUM labels

## Plan Batching

Suggested 3-plan approach:
1. **Plan 01**: P0 (reindex edge repair) + P1 (HybridSearch reset) — both in `__init__.py`
2. **Plan 02**: P1 (heritage labels) + P1 (blast-radius label) + P2 (flows auto-index) — quick targeted fixes
3. **Plan 03**: P2 (context() contract expansion) — needs new storage queries
