# Plan 03: Implement import resolution, call tracing with confidence scoring, heritage extraction, and assemble the full indexing pipeline

## Goal
Implement import resolution, call tracing with confidence scoring, heritage extraction, and assemble the full indexing pipeline

## Tasks

### Task 1: Implement import resolution phase
**Files:** `scripts/context/phases/imports.py`, `tests/test_context_imports.py`
**Action:**
Import resolution phase. Build a file index mapping dotted module paths to FILE node IDs (e.g. 'scripts.memory' → 'file:scripts/memory/__init__.py:'). For each ImportInfo from parser, resolve to target file. Create IMPORTS edges with 'symbols' property listing imported names. Handle absolute imports (dotted path to filesystem), relative imports (dot-counting from source directory), and __init__.py packages. Skip stdlib and unresolvable third-party imports.

**Micro-steps:**
- Write tests for resolving absolute imports (import os → skip stdlib, import mymodule → resolve to file)
- Write tests for resolving from-imports (from mypackage import foo → IMPORTS edge to target file)
- Write tests for resolving relative imports (from . import sibling → resolve via directory)
- Write tests for skipping unresolvable imports (third-party packages)
- Run tests to verify RED
- Implement build_file_index(storage) mapping module paths to FILE node IDs
- Implement resolve_import(import_info, source_file, file_index) returning target file ID or None
- Implement process_imports(parse_results, storage) creating IMPORTS edges with symbols property
- Handle relative imports via dot-counting and directory resolution
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_imports.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_imports.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_imports.py -x
```

**Done when:** [Observable outcome]

### Task 2: Implement call tracing phase with confidence scoring
**Files:** `scripts/context/phases/calls.py`, `tests/test_context_calls.py`
**Action:**
Call tracing phase. For each CallInfo, find the containing symbol (caller) via bisect on line ranges, then resolve the target (callee) with priority: (1) same-file exact name match → confidence 1.0, (2) import-resolved match → 1.0, (3) self/cls receiver method on same class → 0.8, (4) global fuzzy match → 0.5. Create CALLS edges with confidence property. Blocklist common builtins (print, len, range, isinstance, hasattr, getattr, setattr, super, type, etc.) to reduce noise. Follow axon's calls.py pattern.

**Micro-steps:**
- Write tests for same-file call resolution (confidence 1.0)
- Write tests for import-resolved call resolution (confidence 1.0)
- Write tests for self/cls method calls resolving to class methods (confidence 0.8)
- Write tests for global fuzzy match (confidence 0.5)
- Write tests for blocklist filtering (builtins like print, len, isinstance skipped)
- Run tests to verify RED
- Implement build_name_index(storage) mapping symbol names to node IDs
- Implement build_file_symbol_index(parse_results) for per-file symbol lookup via bisect
- Implement find_containing_symbol(line, file_symbols) using bisect for caller attribution
- Implement resolve_call(call_info, source_file, name_index, file_index, import_map)
- Implement confidence scoring: same-file=1.0, import-resolved=1.0, receiver-method=0.8, global=0.5
- Implement CALL_BLOCKLIST (print, len, isinstance, range, enumerate, etc.)
- Implement process_calls(parse_results, storage) creating CALLS edges
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_calls.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_calls.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_calls.py -x
```

**Done when:** [Observable outcome]

### Task 3: Implement heritage phase and assemble full indexing pipeline
**Files:** `scripts/context/phases/heritage.py`, `scripts/context/phases/symbols.py`, `scripts/context/phases/__init__.py`, `scripts/context/__init__.py`, `tests/test_context_heritage.py`, `tests/test_context_pipeline.py`
**Action:**
Heritage phase resolves class inheritance. For each (class_name, 'extends', parent_name) tuple from parser, find both nodes in storage and create EXTENDS edge. Same for IMPLEMENTS. Symbols phase creates FUNCTION/CLASS/METHOD/INTERFACE/TYPE_ALIAS/ENUM nodes from ParseResult symbols + DEFINES edges from FILE to each symbol. Assemble full pipeline in ContextGraph.index(): (1) walk files, (2) compare hashes for incremental, (3) remove stale nodes, (4) parse changed files, (5) run phases: structure → symbols → imports → calls → heritage, (6) update file hashes. Implement ContextGraph.query(name) as simple name match on nodes table.

**Micro-steps:**
- Write tests for heritage extraction (EXTENDS edges for class inheritance)
- Write tests for symbols phase (creating FUNCTION/CLASS/METHOD nodes + DEFINES edges from ParseResult)
- Write tests for full pipeline: index a small Python project and verify nodes/edges
- Run tests to verify RED
- Implement process_heritage(parse_results, storage) creating EXTENDS and IMPLEMENTS edges
- Implement process_symbols(parse_results, storage) creating symbol nodes + DEFINES edges
- Wire all phases into ContextGraph.index(): walk → structure → symbols → imports → calls → heritage
- Implement incremental logic: compare file hashes, only re-parse changed files, remove stale nodes
- Update __init__.py exports and ContextGraph.query() to search nodes by name
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_heritage.py tests/test_context_pipeline.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_heritage.py tests/test_context_pipeline.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_heritage.py tests/test_context_pipeline.py -x
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_imports.py tests/test_context_calls.py tests/test_context_heritage.py tests/test_context_pipeline.py -x
```

## Commit Message
```
feat(context-graph): add import resolution, call tracing, heritage extraction, and full indexing pipeline
```
