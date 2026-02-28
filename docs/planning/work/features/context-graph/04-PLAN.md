# Plan 04: Implement impact analysis (BFS blast radius) and expose the context graph via CLI commands on workflow_memory.py

## Goal
Implement impact analysis (BFS blast radius) and expose the context graph via CLI commands on workflow_memory.py

## Tasks

### Task 1: Impact analysis phase (BFS blast radius)
**Files:** `scripts/context/phases/impact.py`, `scripts/context/__init__.py`, `tests/test_context_impact.py`
**Action:**
BFS-based impact analysis. Given a file path, find all symbols defined in that file, then BFS outward through CALLS (reverse — who calls these symbols), IMPORTS (reverse — who imports this file), and EXTENDS (reverse — who inherits from classes here). Return results as ImpactResult dataclass (node, depth, edge_type) sorted by depth then name. Support max_depth parameter (default 3). Handle cycles via visited set. Add ImpactResult to model.py.

**Micro-steps:**
- Write failing tests for impact_analysis(): single-file direct callers, transitive callers via BFS, depth-limited BFS, cycle handling
- Run tests to confirm RED
- Implement impact_analysis(storage, file_path, max_depth) in phases/impact.py: collect FILE node IDs for path, gather all DEFINES symbols, BFS outward via CALLS/IMPORTS/EXTENDS edges, track visited set, return list of ImpactResult(node, depth, edge_type)
- Wire impact phase into ContextGraph.impact() replacing NotImplementedError stub
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_impact.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_impact.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_impact.py tests/test_context_pipeline.py -x
```

**Done when:** [Observable outcome]

### Task 2: Context query method (node neighborhood)
**Files:** `scripts/context/__init__.py`, `scripts/context/storage.py`, `tests/test_context_query.py`
**Action:**
Implement ContextGraph.context(node_id) replacing NotImplementedError stub. Add get_related_nodes(node_id, rel_type, direction='outgoing'|'incoming') to GraphStorage for generic edge traversal. context() returns a dict: {node: GraphNode, callers: [...], callees: [...], importers: [...], imports: [...], parent_classes: [...], child_classes: [...]}. Each list contains GraphNode instances. If node_id not found, raise ValueError.

**Micro-steps:**
- Write failing tests for ContextGraph.context(): returns callers, callees, importers, parent classes, child classes for a given node ID
- Run tests to confirm RED
- Add get_related_nodes(node_id, rel_type, direction) to GraphStorage — generic relationship traversal
- Implement ContextGraph.context(node_id) returning dict with callers/callees/imports/extends/extended_by keys
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_query.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_query.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_query.py tests/test_context_graph.py -x
```

**Done when:** [Observable outcome]

### Task 3: CLI exposure via workflow_memory.py
**Files:** `.cnogo/scripts/workflow_memory.py`, `tests/test_context_cli.py`
**Action:**
Add 4 subcommands to workflow_memory.py: (1) graph-index — runs ContextGraph.index(), prints node/relationship/file counts. (2) graph-query <name> — runs query(), prints results as name | file | line | label table. (3) graph-impact <file_path> [--depth N] — runs impact(), prints results grouped by depth. (4) graph-context <node_id> — runs context(), prints neighborhood. All subcommands instantiate ContextGraph(repo_path='.') and close() after use. Use argparse subparsers consistent with existing CLI pattern.

**Micro-steps:**
- Write failing tests for CLI subcommands: graph-index, graph-query, graph-impact, graph-context
- Run tests to confirm RED
- Add graph-index subcommand: calls ContextGraph(repo_path).index(), prints stats (node count, file count)
- Add graph-query subcommand: calls query(name), prints matching nodes as table
- Add graph-impact subcommand: calls impact(file_path, max_depth), prints blast radius as tree
- Add graph-context subcommand: calls context(node_id), prints neighborhood summary
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_cli.py -x
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_*.py -x
python3 .cnogo/scripts/workflow_memory.py graph-index --help
```

## Commit Message
```
feat(context-graph): add impact analysis, context queries, and CLI exposure
```
