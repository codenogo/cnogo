# Plan 01: Fix P0 Kuzu NOT IN syntax crash, P2 hook warning, and P3 graph-stats missing relationships

## Goal
Fix P0 Kuzu NOT IN syntax crash, P2 hook warning, and P3 graph-stats missing relationships

## Tasks

### Task 1: Fix Kuzu NOT IN syntax + add regression test
**Files:** `.cnogo/scripts/context/storage.py`, `tests/test_context_storage.py`
**Action:**
Change 'n.file_path NOT IN [{placeholders}]' to 'NOT n.file_path IN [{placeholders}]' at storage.py:435. Add regression test that creates cross-file edges and verifies get_reverse_dependency_files returns the correct source files while excluding the queried files themselves.

**Micro-steps:**
- Add test_get_reverse_dependency_files to test_context_storage.py: set up 3 nodes across 2 files with a cross-file CALLS edge, call get_reverse_dependency_files with the target file, assert the source file is returned
- Run test — expect failure (Kuzu rejects NOT IN syntax)
- In storage.py:435, change 'n.file_path NOT IN [{placeholders}]' to 'NOT n.file_path IN [{placeholders}]'
- Run test — expect pass

**TDD:**
- required: `true`
- failingVerify:
  - `PYTHONPATH=.cnogo python3 -m pytest tests/test_context_storage.py::test_get_reverse_dependency_files -q`
- passingVerify:
  - `PYTHONPATH=.cnogo python3 -m pytest tests/test_context_storage.py::test_get_reverse_dependency_files -q`

**Verify:**
```bash
PYTHONPATH=.cnogo python3 -m pytest tests/test_context_storage.py -q
```

**Done when:** [Observable outcome]

### Task 2: Improve post-commit hook skip warning
**Files:** `.cnogo/scripts/workflow_hooks.py`
**Action:**
Replace 'Graph reindex skipped: graph venv not found' at line 546 with a more actionable message like '[cnogo] Graph reindex skipped: graph venv not found. Run: python3 -m venv .cnogo/.venv && .cnogo/.venv/bin/pip install kuzu tree-sitter tree-sitter-languages'

**Micro-steps:**
- At workflow_hooks.py:546, replace the minimal message with an actionable warning including install instructions
- Verify py_compile passes

**TDD:**
- required: `false`
- reason: Hook behavior depends on filesystem state (venv existence). Warning text change is cosmetic — verified by py_compile.

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
```

**Done when:** [Observable outcome]

### Task 3: Add relationships count to _graph_stats()
**Files:** `.cnogo/scripts/workflow_memory.py`
**Action:**
Add 'relationships': graph._storage.relationship_count() to the dict returned by _graph_stats() at workflow_memory.py:669. Also update the text output format at cmd_graph_index line 684 to include the relationship count.

**Micro-steps:**
- At workflow_memory.py:667-669, add relationship_count = graph._storage.relationship_count() and include 'relationships': relationship_count in the returned dict
- Verify py_compile passes

**TDD:**
- required: `false`
- reason: Kuzu storage not available in dev test env. Verified by py_compile and manual inspection of _graph_stats return dict.

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_memory.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
PYTHONPATH=.cnogo python3 -m pytest tests/test_context_storage.py -q
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
python3 -m py_compile .cnogo/scripts/workflow_memory.py
```

## Commit Message
```
fix(graph): Kuzu NOT IN syntax, hook warning, and graph-stats relationships
```
