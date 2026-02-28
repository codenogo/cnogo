# Plan 05: Detect dead code (unreferenced symbols) and entry points, expose results via ContextGraph.dead_code() and CLI graph-dead command

## Goal
Detect dead code (unreferenced symbols) and entry points, expose results via ContextGraph.dead_code() and CLI graph-dead command

## Tasks

### Task 1: Dead code detection phase
**Files:** `scripts/context/phases/dead_code.py`, `scripts/context/storage.py`, `tests/test_context_dead_code.py`
**Action:**
Create dead code detection phase. Add storage helpers get_all_symbol_nodes() and mark_dead_nodes(). Implement detect_dead_code() with entry point heuristics (test_ prefix, __main__, __init__ exports, main()). A symbol is dead if it has no incoming CALLS, IMPORTS, EXTENDS, or IMPLEMENTS edges and is not an entry point.

**Micro-steps:**
- Write failing tests for detect_dead_code() — unreferenced function is dead, called function is not, entry points (__main__ guard, test_ prefix, __init__ exports) are not dead, methods called via CALLS edge are not dead, class with EXTENDS incoming is not dead
- Run tests to confirm RED
- Add get_all_symbol_nodes() to GraphStorage — returns all FUNCTION/CLASS/METHOD/ENUM nodes
- Add mark_dead_nodes(node_ids) to GraphStorage — bulk UPDATE is_dead=1
- Create scripts/context/phases/dead_code.py with DeadCodeResult dataclass and detect_dead_code(storage) function
- Implement entry point heuristics: __main__ guard callers, test_ prefix functions, __init__.py exported names, main() functions
- Implement dead detection: symbol nodes with zero incoming CALLS/IMPORTS/EXTENDS/IMPLEMENTS edges and not entry points
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_dead_code.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_dead_code.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_dead_code.py -x
```

**Done when:** [Observable outcome]

### Task 2: Wire into ContextGraph
**Files:** `scripts/context/__init__.py`, `tests/test_context_graph.py`
**Action:**
Add dead_code() method to ContextGraph class. Import and delegate to detect_dead_code(). Return list of DeadCodeResult. Do not integrate into index() pipeline — keep as separate analysis call.

**Micro-steps:**
- Write failing tests for ContextGraph.dead_code() — returns DeadCodeResult list, marks is_dead on nodes in storage, empty result when all symbols referenced
- Run tests to confirm RED
- Import detect_dead_code and DeadCodeResult in __init__.py
- Add dead_code() method to ContextGraph that calls detect_dead_code(self._storage) and returns results
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -k dead`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -k dead`

**Verify:**
```bash
python3 -m pytest tests/test_context_graph.py -x -k dead
```

**Done when:** [Observable outcome]

### Task 3: CLI graph-dead subcommand
**Files:** `.cnogo/scripts/workflow_memory.py`, `tests/test_context_cli.py`
**Action:**
Add graph-dead subcommand to workflow_memory.py. Handler indexes the repo, runs dead_code(), prints each dead symbol as 'DEAD  label:name  file:line'. Add to _graph_cmds set. Register argparse subparser with --repo flag.

**Micro-steps:**
- Write failing tests for graph-dead CLI — --help works, empty repo returns 0, indexed repo with dead code lists dead symbols with file:line format
- Run tests to confirm RED
- Add cmd_graph_dead handler that opens graph, runs index(), then dead_code(), prints results
- Register graph-dead argparse subparser with --repo flag
- Add to dispatch table and _graph_cmds set
- Run tests to confirm GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x -k dead`
- passingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x -k dead`

**Verify:**
```bash
python3 -m pytest tests/test_context_cli.py -x -k dead
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_*.py -x
python3 .cnogo/scripts/workflow_memory.py graph-dead --help
```

## Commit Message
```
feat(context-graph): add dead code detection with entry point heuristics and CLI exposure
```
