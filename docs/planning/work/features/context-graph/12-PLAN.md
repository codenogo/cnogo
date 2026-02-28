# Plan 12: Persist USES_TYPE edges from parsed type annotations, connecting symbols to their type references in the graph.

## Goal
Persist USES_TYPE edges from parsed type annotations, connecting symbols to their type references in the graph.

## Tasks

### Task 1: Create types phase module and wire into index pipeline
**Files:** `scripts/context/phases/types.py`, `scripts/context/__init__.py`, `tests/test_context_graph.py`
**Action:**
Create a new types phase module at scripts/context/phases/types.py. Build a symbol index (name → node ID) from CLASS, INTERFACE, TYPE_ALIAS, ENUM nodes in storage. For each TypeRef in ParseResult.type_refs, find the source symbol (function/method containing the annotation by matching file_path + line range) and the target type node. Create USES_TYPE edges from source → target. Wire process_types() into the index() pipeline after process_heritage(). Follow heritage.py pattern for structure.

**Micro-steps:**
- Write failing tests: USES_TYPE edges created from function parameter annotations, USES_TYPE edges created from return type annotations, USES_TYPE edges resolve to same-file class nodes, no edges for unresolvable type names
- Run tests to verify RED
- Create scripts/context/phases/types.py with process_types() following heritage.py pattern — build symbol index, iterate ParseResult.type_refs, resolve to target node, create USES_TYPE edges
- Add process_types() call to index() pipeline in __init__.py after process_heritage()
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q -k type`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q -k type`

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
feat(context-graph): add USES_TYPE edges from type annotations via types phase
```
