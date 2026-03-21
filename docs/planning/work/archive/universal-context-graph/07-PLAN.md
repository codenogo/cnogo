# Plan 07: Watchfiles live re-indexing, remaining analysis phases (test coverage, proximity, contracts), and visualization

## Goal
Watchfiles live re-indexing, remaining analysis phases (test coverage, proximity, contracts), and visualization

## Tasks

### Task 1: Watchfiles live re-indexing
**Files:** `.cnogo/scripts/context/watcher.py`, `tests/test_context_watcher.py`
**Action:**
Create watcher.py using watchfiles library for live file monitoring. FileWatcher watches for changes to supported file extensions, triggers incremental ContextGraph.index() on each change batch. Uses native OS events (FSEvents on macOS, inotify on Linux). Integrates into CLI as graph-index --watch.

**Micro-steps:**
- Write failing tests: watcher detects file changes and triggers incremental re-index on supported file types
- Implement watcher.py using watchfiles library: FileWatcher class that monitors repo for changes to supported file extensions
- On change event: call ContextGraph.index() for incremental update (hash-based, only re-processes changed files)
- Support start/stop lifecycle and callback hooks for change notification
- Integrate as graph-index --watch CLI flag (runs watcher in foreground until Ctrl+C)
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_watcher.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_watcher.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_watcher.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Test coverage, proximity, and contracts phases
**Files:** `.cnogo/scripts/context/phases/test_coverage.py`, `.cnogo/scripts/context/phases/proximity.py`, `.cnogo/scripts/context/phases/contracts.py`, `tests/test_context_analysis.py`, `tests/test_context_proximity.py`, `tests/test_context_contracts.py`
**Action:**
Rebuild three remaining phases. Test coverage: detect test files via multi-language naming patterns (test_*.py, *.test.ts, *.spec.js, etc.), walk CALLS edges from test symbols to production code. Proximity: BFS file ranking from focal symbol seeds. Contracts: extract and compare function/method signatures to detect breaking changes.

**Micro-steps:**
- Write failing tests for test_coverage: detect test files by naming convention across languages (test_*.py, *.test.ts, *.spec.js), walk CALLS edges to production symbols
- Implement test_coverage.py: multi-language test file detection + CALLS edge walking for coverage analysis
- Write failing tests for proximity: BFS-based file ranking from focal symbol nodes
- Implement proximity.py: rank_by_proximity(storage, focal_ids, max_depth) returns files sorted by graph distance
- Write failing tests for contracts: signature comparison between stored and current code
- Implement contracts.py: extract_current_signatures and compare_signatures for multi-language code
- Run all passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_analysis.py tests/test_context_proximity.py tests/test_context_contracts.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_analysis.py tests/test_context_proximity.py tests/test_context_contracts.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_analysis.py tests/test_context_proximity.py tests/test_context_contracts.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: Visualization (Mermaid + DOT)
**Files:** `.cnogo/scripts/context/visualization.py`, `tests/test_context_visualization.py`
**Action:**
Rebuild visualization.py for KuzuDB backend. _collect_subgraph uses Cypher queries for BFS subgraph collection. render_mermaid and render_dot produce valid Mermaid/DOT output with language-aware styling (different colors per language). Same public API: scope (file/module/full), center node, depth, format (mermaid/dot).

**Micro-steps:**
- Write failing tests: render_mermaid and render_dot produce valid output for multi-language graphs; _collect_subgraph works with KuzuDB storage
- Implement visualization.py: _collect_subgraph(storage, scope, center, depth) using Cypher BFS queries on KuzuDB
- Implement render_mermaid(nodes, edges) producing Mermaid flowchart syntax
- Implement render_dot(nodes, edges) producing Graphviz DOT syntax
- Support scopes: file (single file symbols), module (directory), full (all nodes)
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_visualization.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_watcher.py tests/test_context_analysis.py tests/test_context_proximity.py tests/test_context_contracts.py tests/test_context_visualization.py -v 2>&1 | tail -10
```

## Commit Message
```
feat(context-graph): watchfiles + test coverage/proximity/contracts phases + visualization
```
