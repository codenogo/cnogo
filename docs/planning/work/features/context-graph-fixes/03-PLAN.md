# Plan 03: Eliminate N+1 query patterns in impact and community phases, wire HybridSearch into ContextGraph.search() with CONTAINS fallback

## Goal
Eliminate N+1 query patterns in impact and community phases, wire HybridSearch into ContextGraph.search() with CONTAINS fallback

## Tasks

### Task 1: Pre-fetch nodes in impact.py BFS to eliminate N+1
**Files:** `.cnogo/scripts/context/phases/impact.py`
**Action:**
In impact_analysis(), after fetching file_nodes and building seed_ids, pre-fetch all graph nodes into a cache dict: `all_nodes = storage.get_all_nodes(); node_cache = {n.id: n for n in all_nodes}`. Then replace both `storage.get_node(node_id)` calls (line 81 in BFS loop and line 105 in results loop) with `node_cache.get(node_id)`. This eliminates two N+1 query patterns — the BFS loop no longer calls get_node() per visited node, and the results loop no longer re-fetches each impacted node.

**Micro-steps:**
- Add a pre-fetch of all nodes into a dict at the start of impact_analysis()
- Replace storage.get_node(node_id) on line 81 (BFS loop) with dict lookup
- Replace storage.get_node(node_id) on line 105 (results loop) with dict lookup
- Run py_compile on impact.py
- Grep to confirm no storage.get_node() calls remain in impact_analysis()

**TDD:**
- required: `false`
- reason: kuzu not installed in dev env; verification via py_compile and pattern assertions

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/context/phases/impact.py
python3 -c "import subprocess; r=subprocess.run(['grep','-n','storage.get_node','.cnogo/scripts/context/phases/impact.py'],capture_output=True,text=True); assert r.stdout.strip()=='', f'N+1 pattern still present: {r.stdout}'; print('impact.py N+1 eliminated')"
```

**Done when:** [Observable outcome]

### Task 2: Batch-fetch member names in community.py to eliminate N+1
**Files:** `.cnogo/scripts/context/phases/community.py`
**Action:**
In detect_communities(), after the early return for empty edges, pre-fetch all node names: `all_nodes = storage.get_all_nodes(); name_lookup = {n.id: n.name for n in all_nodes}`. Replace line 109 (`member_names = [_query_node_name(storage, nid) for nid in member_node_ids]`) with `member_names = [name_lookup.get(nid, nid) for nid in member_node_ids]`. Then remove the `_query_node_name()` helper function (lines 50-55) as it is no longer used. This eliminates the N+1 pattern of calling storage.get_node() per community member.

**Micro-steps:**
- Add a pre-fetch of all node names into a lookup dict at the start of detect_communities()
- Replace _query_node_name() list comprehension on line 109 with dict lookups
- Remove the _query_node_name() helper function (lines 50-55)
- Run py_compile on community.py
- Grep to confirm no _query_node_name calls remain

**TDD:**
- required: `false`
- reason: kuzu not installed in dev env; verification via py_compile and pattern assertions

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/context/phases/community.py
python3 -c "import subprocess; r=subprocess.run(['grep','-n','_query_node_name','.cnogo/scripts/context/phases/community.py'],capture_output=True,text=True); assert r.stdout.strip()=='', f'N+1 helper still present: {r.stdout}'; print('community.py N+1 eliminated')"
```

**Done when:** [Observable outcome]

### Task 3: Wire HybridSearch into ContextGraph.search() with CONTAINS fallback
**Files:** `.cnogo/scripts/context/__init__.py`
**Action:**
In ContextGraph.__init__(), add `self._hybrid_search = None` (None = not attempted, False = unavailable). Add a `_get_hybrid_search()` method that lazily creates a HybridSearch instance, calls build_index(), caches it, and returns it. On ImportError or any exception, set `self._hybrid_search = False` and return None. Update `search()` to call `_get_hybrid_search()`: if available, run hybrid search and convert each SearchResult to (GraphNode, float) by looking up nodes via `self._storage.get_node(r.node_id)`; if None, fall back to `self._storage.search()`. This preserves the existing `list[tuple[GraphNode, float]]` return type.

**Micro-steps:**
- Add _hybrid_search attribute (initially None) in ContextGraph.__init__()
- Add _get_hybrid_search() private method that lazily initializes HybridSearch
- Handle ImportError for rank_bm25 by marking hybrid as unavailable (use False sentinel)
- Update search() to try HybridSearch first, fall back to storage.search()
- Convert HybridSearch SearchResult objects to (GraphNode, float) tuples for API compatibility
- Run py_compile on __init__.py
- Verify model import still works without kuzu

**TDD:**
- required: `false`
- reason: kuzu and rank_bm25 not installed in dev env; verification via py_compile and import test

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/context/__init__.py
cd .cnogo && python3 -c "from scripts.context.model import NodeLabel; print('lazy import OK')"
python3 -c "import ast; tree=ast.parse(open('.cnogo/scripts/context/__init__.py').read()); methods=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert '_get_hybrid_search' in methods, f'Missing _get_hybrid_search'; print('HybridSearch wired')"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile .cnogo/scripts/context/phases/impact.py
python3 -m py_compile .cnogo/scripts/context/phases/community.py
python3 -m py_compile .cnogo/scripts/context/__init__.py
cd .cnogo && python3 -c "from scripts.context.model import NodeLabel; print('lazy import OK')"
```

## Commit Message
```
perf(context-graph): eliminate N+1 queries in impact/community, wire HybridSearch with fallback
```
