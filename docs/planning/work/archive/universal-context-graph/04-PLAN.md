# Plan 04: Rebuild relationship phases: calls (with confidence), heritage, types, and exports

## Goal
Rebuild relationship phases: calls (with confidence), heritage, types, and exports

## Tasks

### Task 1: Calls phase with confidence scoring
**Files:** `.cnogo/scripts/context/phases/calls.py`, `tests/test_context_calls.py`
**Action:**
Rebuild calls.py to create CALLS relationships from ParseResult.calls (CallInfo IR). Resolution strategy: exact name match -> class.method match -> fuzzy match. Assign confidence: 1.0 (exact method on known class), 0.7 (exact function name), 0.3 (unresolved/fuzzy). Store confidence in relationship properties.

**Micro-steps:**
- Write failing tests: given parse results with CallInfo entries, creates CALLS relationships with confidence scores (1.0 for method-on-known-class, 0.7 for function calls, 0.3 for unresolved)
- Implement calls.py: process_calls(parse_results, storage) resolves call targets to graph nodes, creates CALLS relationships with confidence property
- Handle cross-file call resolution via storage lookups
- Support method calls on class instances by resolving class type -> method
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_calls.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_calls.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_calls.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Heritage and types phases
**Files:** `.cnogo/scripts/context/phases/heritage.py`, `.cnogo/scripts/context/phases/types.py`, `tests/test_context_heritage.py`, `tests/test_context_types_exports.py`
**Action:**
Rebuild heritage.py for EXTENDS/IMPLEMENTS relationships from ParseResult.heritage. Rebuild types.py for USES_TYPE relationships from ParseResult.type_refs. Both phases resolve names to existing graph nodes via storage lookups. Heritage supports Python (class Foo(Bar)), TypeScript (class Foo extends Bar implements IBaz).

**Micro-steps:**
- Write failing tests for heritage: EXTENDS relationships for class inheritance, IMPLEMENTS for interface implementation
- Implement heritage.py: process_heritage(parse_results, storage) resolves base class/interface names to nodes, creates EXTENDS/IMPLEMENTS relationships
- Write failing tests for types: USES_TYPE relationships for type annotations
- Implement types.py: process_types(parse_results, storage) resolves TypeRef entries to type nodes, creates USES_TYPE relationships
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_heritage.py tests/test_context_types_exports.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_heritage.py tests/test_context_types_exports.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_heritage.py tests/test_context_types_exports.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: Exports phase and integrate all relationship phases into index()
**Files:** `.cnogo/scripts/context/phases/exports.py`, `.cnogo/scripts/context/__init__.py`, `tests/test_context_core.py`
**Action:**
Rebuild exports.py for EXPORTS relationships. Update ContextGraph.index() to include all relationship phases in order: structure -> symbols -> imports -> calls -> heritage -> types -> exports. Integration tests verify full phase pipeline produces correct node and relationship counts for a mixed-language repo.

**Micro-steps:**
- Write failing tests for exports: EXPORTS relationships for module-level __all__, TypeScript export statements
- Implement exports.py: process_exports(parse_results, storage) marks symbols as exported and creates EXPORTS relationships
- Update ContextGraph.index() to run calls, heritage, types, exports phases after symbols/imports
- Write integration test: index a multi-file Python+TS repo and verify all relationship types exist
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_core.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_core.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_core.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_calls.py tests/test_context_heritage.py tests/test_context_types_exports.py tests/test_context_core.py -v 2>&1 | tail -10
```

## Commit Message
```
feat(context-graph): relationship phases (calls, heritage, types, exports)
```
