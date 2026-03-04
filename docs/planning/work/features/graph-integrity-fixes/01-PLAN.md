# Plan 01: Fix P0 incremental reindex edge loss and P1 HybridSearch cache staleness in ContextGraph.index()

## Goal
Fix P0 incremental reindex edge loss and P1 HybridSearch cache staleness in ContextGraph.index()

## Tasks

### Task 1: Fix incremental reindex to preserve cross-file edges
**Files:** `.cnogo/scripts/context/__init__.py`, `.cnogo/scripts/context/storage.py`
**Action:**
Add storage.get_reverse_dependency_files(changed_fps) that runs: MATCH (n:GraphNode)-[r:CodeRelation]->(m:GraphNode) WHERE m.file_path IN $fps AND n.file_path NOT IN $fps RETURN DISTINCT n.file_path. In index(), before remove_nodes_by_file, collect reverse deps. After processing new_or_changed through all phases, also re-parse the affected unchanged files (using walk entries or reading from disk) and run the edge-building phases (imports, calls, heritage, types, exports) with those parse results merged in. Do NOT re-run process_symbols or process_structure for unchanged files since their nodes are already correct.

**Micro-steps:**
- Add get_reverse_dependency_files(file_paths) method to GraphStorage that returns distinct file paths with edges pointing into the given files
- In ContextGraph.index(), before removing changed-file nodes, call get_reverse_dependency_files() to collect affected unchanged files
- After edge-building phases run for new_or_changed, re-parse affected unchanged files and run edge phases (calls, imports, heritage, types, exports) for them
- Verify with py_compile that both files compile cleanly

**TDD:**
- required: `false`
- reason: kuzu not available in dev/test environment — verify via py_compile and grep assertions

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/storage.py', doraise=True)"
```

**Done when:** [Observable outcome]

### Task 2: Reset HybridSearch cache on reindex
**Files:** `.cnogo/scripts/context/__init__.py`
**Action:**
Add `self._hybrid_search = None` as the first line inside index() (before the walk call). This resets the lazy sentinel so the next search() call triggers a fresh build_index() against updated storage.

**Micro-steps:**
- Add self._hybrid_search = None as the first line of index() method body
- Verify the sentinel protocol: None=not attempted, False=unavailable, instance=ready

**TDD:**
- required: `false`
- reason: kuzu not available in dev/test environment — verify via grep assertion

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
grep -n '_hybrid_search = None' .cnogo/scripts/context/__init__.py | grep -v '__init__' | head -5
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/storage.py', doraise=True)"
```

## Commit Message
```
fix(graph): preserve cross-file edges on incremental reindex and reset search cache
```
