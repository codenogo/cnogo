# Plan 03: Rebuild core indexing phases (structure, symbols, imports) and wire up ContextGraph.index() end-to-end

## Goal
Rebuild core indexing phases (structure, symbols, imports) and wire up ContextGraph.index() end-to-end

## Tasks

### Task 1: Structure and symbols phases
**Files:** `.cnogo/scripts/context/phases/structure.py`, `.cnogo/scripts/context/phases/symbols.py`, `tests/test_context_structure.py`, `tests/test_context_model.py`
**Action:**
Rebuild structure.py and symbols.py phases to work with new KuzuDB storage and multi-language parse results. Structure phase creates FILE/FOLDER nodes and CONTAINS relationships. Symbols phase creates symbol nodes (FUNCTION, CLASS, METHOD, etc.) from ParseResult.symbols and DEFINES relationships.

**Micro-steps:**
- Write failing tests for structure phase: given walker FileEntry list, creates FILE and FOLDER nodes in KuzuDB storage
- Implement structure.py: process_structure(files, storage) creates FILE nodes per file, FOLDER nodes per directory, CONTAINS relationships (folder->file, parent_folder->child_folder)
- Write failing tests for symbols phase: given parse results, creates FUNCTION/CLASS/METHOD/INTERFACE/TYPE_ALIAS/ENUM nodes
- Implement symbols.py: process_symbols(parse_results, storage) creates symbol nodes from SymbolInfo IR with DEFINES relationships (file->symbol)
- Run all passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_structure.py tests/test_context_model.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_structure.py tests/test_context_model.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_structure.py tests/test_context_model.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Imports phase
**Files:** `.cnogo/scripts/context/phases/imports.py`, `tests/test_context_imports.py`
**Action:**
Rebuild imports.py to handle multi-language import resolution. Must resolve Python imports (from x import y, import x) and TypeScript/JS imports (import {y} from './x', require('./x')). Create IMPORTS relationships between importing symbol/file and imported symbol/file.

**Micro-steps:**
- Write failing tests for imports phase: resolves import targets across Python (from x import y) and TypeScript (import {y} from 'x') styles
- Implement imports.py: process_imports(parse_results, storage) creates IMPORTS relationships between source file/symbol and target symbol
- Handle cross-language import resolution: resolve module paths to file nodes, resolve named imports to symbol nodes
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_imports.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_imports.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_imports.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: Wire up ContextGraph.index() end-to-end
**Files:** `.cnogo/scripts/context/__init__.py`, `tests/test_context_pipeline.py`
**Action:**
Create the initial ContextGraph class in __init__.py with constructor, index(), is_indexed(), query(), nodes_in_file(), and close(). The index() method runs the full pipeline: walk files -> compare hashes -> remove stale -> structure phase -> parse with tree-sitter -> symbols phase -> imports phase. Use ThreadPoolExecutor for concurrent file parsing (Axon pattern). This gives us a working end-to-end indexer for the first time.

**Micro-steps:**
- Write failing integration test: create a temp repo with .py and .ts files, call ContextGraph(repo).index(), verify FILE/FOLDER/FUNCTION/CLASS nodes exist in storage
- Implement ContextGraph.__init__() with KuzuDB storage at .cnogo/graph.kuzu/
- Implement ContextGraph.index() pipeline: walk -> hash check -> structure -> parse -> symbols -> imports
- Implement ContextGraph.is_indexed(), query(), nodes_in_file(), close()
- Wire up incremental indexing (hash comparison, stale file removal)
- Run passing integration tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_pipeline.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_pipeline.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_pipeline.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_structure.py tests/test_context_imports.py tests/test_context_pipeline.py -v 2>&1 | tail -10
```

## Commit Message
```
feat(context-graph): core phases (structure, symbols, imports) + ContextGraph.index()
```
