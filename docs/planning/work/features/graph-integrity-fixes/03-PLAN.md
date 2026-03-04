# Plan 03: Fix P2 context() contract drift — expand to return all 6 neighborhood keys the CLI expects

## Goal
Fix P2 context() contract drift — expand to return all 6 neighborhood keys the CLI expects

## Tasks

### Task 1: Expand context() to return full neighborhood dict
**Files:** `.cnogo/scripts/context/__init__.py`
**Action:**
Rewrite context() to return all 7 keys: node, callers, callees, importers, imports, parent_classes, child_classes. Use the existing storage.get_related_nodes() for imports/heritage edges and storage.get_callees()/get_callers_with_confidence() for calls. Unwrap callers from (node, confidence) tuples to plain GraphNode list. The storage already has get_related_nodes(node_id, rel_type, direction) which handles IMPORTS, EXTENDS, and IMPLEMENTS edge types with incoming/outgoing direction. The callers_with_confidence() public method remains unchanged for users who need confidence scores.

**Micro-steps:**
- Update context() to query importers via storage.get_related_nodes(node_id, RelType.IMPORTS, 'incoming')
- Query imports via storage.get_related_nodes(node_id, RelType.IMPORTS, 'outgoing')
- Query parent_classes via storage.get_related_nodes(node_id, RelType.EXTENDS, 'outgoing') + storage.get_related_nodes(node_id, RelType.IMPLEMENTS, 'outgoing')
- Query child_classes via storage.get_related_nodes(node_id, RelType.EXTENDS, 'incoming') + storage.get_related_nodes(node_id, RelType.IMPLEMENTS, 'incoming')
- Change callers to return plain GraphNode list (unwrap confidence tuples) for CLI compatibility
- Verify all 7 keys are present in the returned dict via grep

**TDD:**
- required: `false`
- reason: kuzu not available in dev/test environment — verify via py_compile and grep

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
grep -c 'importers\|parent_classes\|child_classes' .cnogo/scripts/context/__init__.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
```

## Commit Message
```
fix(graph): expand context() to return full neighborhood (callers, callees, importers, imports, heritage)
```
