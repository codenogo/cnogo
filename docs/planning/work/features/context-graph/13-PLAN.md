# Plan 13: Persist EXPORTS edges from __all__ lists, connecting FILE nodes to their publicly exported symbol nodes.

## Goal
Persist EXPORTS edges from __all__ lists, connecting FILE nodes to their publicly exported symbol nodes.

## Tasks

### Task 1: Create exports phase module and wire into index pipeline
**Files:** `scripts/context/phases/exports.py`, `scripts/context/__init__.py`, `tests/test_context_graph.py`
**Action:**
Create a new exports phase module at scripts/context/phases/exports.py. For each file in parse_results, iterate ParseResult.exports (names from __all__). For each exported name, find the symbol node in the same file (FUNCTION, CLASS, METHOD). Create an EXPORTS edge from FILE → symbol. Also set is_exported=True on the symbol node via a storage update. Follow the heritage.py/imports.py pattern for structure. Wire process_exports() into index() after process_types().

**Micro-steps:**
- Write failing tests: EXPORTS edges created from __all__ list, exported symbols have is_exported=True, no edges for names not found in graph, multiple exports from same file
- Run tests to verify RED
- Create scripts/context/phases/exports.py with process_exports() — iterate ParseResult.exports, resolve each name to a symbol node in the same file, create EXPORTS edge from FILE → symbol and set is_exported=True on the symbol node
- Add process_exports() call to index() pipeline in __init__.py after process_types()
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q -k export`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q -k export`

**Verify:**
```bash
python3 -m pytest tests/test_context_graph.py -x -q
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_graph.py -x -q
```

## Commit Message
```
feat(context-graph): add EXPORTS edges from __all__ via exports phase
```
