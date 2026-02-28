# Plan 04: Add context window optimization using graph proximity to rank files by relevance to focal symbols

## Goal
Add context window optimization using graph proximity to rank files by relevance to focal symbols

## Tasks

### Task 1: Add graph proximity ranking algorithm and prioritize_files() method
**Files:** `scripts/context/phases/proximity.py`, `scripts/context/__init__.py`, `tests/test_context_proximity.py`
**Action:**
Create BFS-based proximity ranking. rank_by_proximity(storage, focal_node_ids, max_depth=5) computes minimum graph distance from focal symbols through CALLS, IMPORTS, EXTENDS, USES_TYPE edges (both directions). Groups results by file and returns files ranked by minimum symbol distance (closest first). Add prioritize_files(focal_symbols, max_files=20) to ContextGraph that accepts symbol names or node IDs, resolves them, runs proximity ranking, and returns [{file_path, min_distance, connected_symbols}].

**Micro-steps:**
- Write failing test for rank_by_proximity() and ContextGraph.prioritize_files()
- Run test to verify RED
- Create scripts/context/phases/proximity.py with BFS-based proximity ranking
- Implement rank_by_proximity(storage, focal_node_ids, max_depth) returning files ranked by min distance
- Add prioritize_files(focal_symbols, max_files) public method to ContextGraph
- Run test to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_proximity.py -v -k test_proximity`
- passingVerify:
  - `python3 -m pytest tests/test_context_proximity.py -v -k test_proximity`

**Verify:**
```bash
python3 -m pytest tests/test_context_proximity.py -v
```

**Done when:** [Observable outcome]

### Task 2: Add prioritize_context() workflow function and graph-prioritize CLI command
**Files:** `scripts/context/workflow.py`, `scripts/workflow_memory.py`, `tests/test_context_proximity.py`
**Action:**
Add prioritize_context(repo_path, focal_symbols, max_files=20) to workflow.py as the 4th workflow function. Returns {enabled, ranked_files: [{path, distance, reason}], focal_symbols_resolved}. Follows graceful degradation pattern. Add graph-prioritize CLI: --symbols (comma-separated names), --max-files N (default 20), --json flag. This enables graph-informed context selection instead of blind file inclusion.

**Micro-steps:**
- Write failing test for prioritize_context() workflow function
- Run test to verify RED
- Add prioritize_context(repo_path, focal_symbols, max_files) to workflow.py with graceful degradation
- Add graph-prioritize subcommand to workflow_memory.py with --symbols and --max-files flags
- Run test to verify GREEN
- Verify CLI outputs ranked file list

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_proximity.py -v -k test_prioritize_workflow`
- passingVerify:
  - `python3 -m pytest tests/test_context_proximity.py -v -k test_prioritize_workflow`

**Verify:**
```bash
python3 -m pytest tests/test_context_proximity.py -v
python3 scripts/workflow_memory.py graph-prioritize --help 2>&1 | grep -q prioritize
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_proximity.py -v
python3 scripts/workflow_memory.py graph-prioritize --help 2>&1 | grep -q prioritize
```

## Commit Message
```
feat(context-graph-next): add context window optimization via graph proximity ranking
```
