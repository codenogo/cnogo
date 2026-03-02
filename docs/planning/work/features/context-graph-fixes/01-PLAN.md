# Plan 01: Eliminate Cypher injection risk, fix heritage label coverage, correct CLI argument mismatches, and update misleading docstring

## Goal
Eliminate Cypher injection risk, fix heritage label coverage, correct CLI argument mismatches, and update misleading docstring

## Tasks

### Task 1: Parameterize all Cypher string interpolation
**Files:** `.cnogo/scripts/context/phases/exports.py`, `.cnogo/scripts/context/phases/community.py`, `.cnogo/scripts/context/phases/coupling.py`, `.cnogo/scripts/context/storage.py`
**Action:**
Replace all f-string/string interpolation in Cypher queries with KuzuDB $param parameterized queries. Site 1 (exports.py:16): file_path injection — HIGH risk. Sites 2-4 (community.py, coupling.py, storage.py): enum-derived values — LOW risk but bad pattern. Use conn.execute(query, {param: value}) syntax already established elsewhere in storage.py.

**Micro-steps:**
- Read each file and locate f-string Cypher queries
- Replace exports.py:16 f-string file_path interpolation with $fp parameterized query
- Replace community.py:48-52 types_list string-build with individual $t0/$t1/$t2 params
- Replace coupling.py:41-43 labels_list string-build with individual $l0/$l1/$l2 params
- Replace storage.py:374 types_list string-build with parameterized IN clause
- Syntax-check all 4 files with py_compile
- Grep to confirm zero remaining f-string Cypher patterns

**TDD:**
- required: `false`
- reason: All 4 files require kuzu at import time — tests cannot collect without kuzu installed. Changes are mechanical pattern replacements (f-string to $param) with no behavioral change.

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/context/phases/exports.py
python3 -m py_compile .cnogo/scripts/context/phases/community.py
python3 -m py_compile .cnogo/scripts/context/phases/coupling.py
python3 -m py_compile .cnogo/scripts/context/storage.py
python3 -c "import pathlib; code = pathlib.Path('.cnogo/scripts/context/phases/exports.py').read_text(); assert 'f\"' not in code and \"f'\" not in code, 'f-string remains in exports.py'"
```

**Done when:** [Observable outcome]

### Task 2: Fix heritage label filter and add_relationships() docstring
**Files:** `.cnogo/scripts/context/phases/heritage.py`, `.cnogo/scripts/context/storage.py`
**Action:**
In heritage.py _build_class_index(), expand label filter from ['class', 'interface'] to ['class', 'interface', 'type_alias'] so TypeScript type alias inheritance is captured. In storage.py add_relationships(), update docstring from 'Duplicate rel_ids are silently skipped' to accurately describe CREATE behavior and caller dedup responsibility.

**Micro-steps:**
- Read heritage.py _build_class_index() and locate label filter
- Add 'type_alias' to the IN clause alongside 'class' and 'interface'
- Read storage.py add_relationships() docstring
- Update docstring to clarify CREATE behavior and caller dedup requirement
- Syntax-check both files

**TDD:**
- required: `false`
- reason: Heritage test requires kuzu for collection. Docstring change is documentation-only with no code behavior change.

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/context/phases/heritage.py
python3 -m py_compile .cnogo/scripts/context/storage.py
python3 -c "import pathlib; code = pathlib.Path('.cnogo/scripts/context/phases/heritage.py').read_text(); assert 'type_alias' in code, 'type_alias not added to heritage'"
```

**Done when:** [Observable outcome]

### Task 3: Fix CLI wiring: remove invalid limit param from graph commands
**Files:** `.cnogo/scripts/workflow_memory.py`
**Action:**
In cmd_graph_suggest_scope() remove line 1130 (limit extraction) and limit=limit from the suggest_scope() call at line 1132. In cmd_graph_enrich() remove line 1160 (limit extraction) and limit=limit from the enrich_context() call at line 1162. The suggest_scope() and enrich_context() functions do not accept a limit parameter.

**Micro-steps:**
- Read cmd_graph_suggest_scope() and locate limit extraction and passing
- Remove limit variable and limit=limit from suggest_scope() call
- Read cmd_graph_enrich() and locate limit extraction and passing
- Remove limit variable and limit=limit from enrich_context() call
- Syntax-check workflow_memory.py

**TDD:**
- required: `false`
- reason: Graph commands require kuzu at import time. Fix is mechanical removal of invalid keyword argument.

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_memory.py
python3 -c "import pathlib; code = pathlib.Path('.cnogo/scripts/workflow_memory.py').read_text(); assert 'limit=limit' not in code.split('def cmd_graph_suggest_scope')[1].split('def cmd_graph_enrich')[0], 'limit=limit still in suggest_scope call'"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile .cnogo/scripts/context/phases/exports.py && python3 -m py_compile .cnogo/scripts/context/phases/community.py && python3 -m py_compile .cnogo/scripts/context/phases/coupling.py && python3 -m py_compile .cnogo/scripts/context/storage.py && python3 -m py_compile .cnogo/scripts/context/phases/heritage.py && python3 -m py_compile .cnogo/scripts/workflow_memory.py
python3 -m pytest tests/test_context_model.py tests/test_context_walker.py tests/test_context_analysis.py tests/test_context_cli.py tests/test_context_core.py tests/test_context_visualization.py -v
```

## Commit Message
```
fix(context-graph): parameterize Cypher queries, fix heritage labels, remove invalid CLI args
```
