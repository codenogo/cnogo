# Plan 02: Fix P1 heritage edge label bug, P1 blast-radius KeyError, and P2 flows auto-index

## Goal
Fix P1 heritage edge label bug, P1 blast-radius KeyError, and P2 flows auto-index

## Tasks

### Task 1: Fix heritage edges for non-CLASS children
**Files:** `.cnogo/scripts/context/phases/heritage.py`
**Action:**
In process_heritage(), line 42, replace `child_id = generate_id(NodeLabel.CLASS, file_path, child_name)` with a lookup in class_index: `child_id = class_index.get(child_name)`. Then the `if storage.get_node(child_id) is None` check (line 43) becomes `if child_id is None` (matching the parent_id pattern on line 46-48). This resolves the actual node ID regardless of whether the child is a CLASS, INTERFACE, TYPE_ALIAS, or ENUM.

**Micro-steps:**
- Replace hardcoded generate_id(NodeLabel.CLASS, ...) child lookup with class_index.get(child_name) lookup, matching how parent_name is already resolved
- If child_name is not in class_index, skip (same as parent_name miss)
- Verify py_compile and grep that NodeLabel.CLASS is no longer used in child_id generation

**TDD:**
- required: `false`
- reason: kuzu not available in dev/test environment — verify via py_compile and grep

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/phases/heritage.py', doraise=True)"
! grep -n 'generate_id(NodeLabel.CLASS' .cnogo/scripts/context/phases/heritage.py
```

**Done when:** [Observable outcome]

### Task 2: Add missing 'label' key to review_impact() entries
**Files:** `.cnogo/scripts/context/__init__.py`
**Action:**
In review_impact(), change the entries.append line from `{"name": ir.node.name, "file_path": ir.node.file_path, "depth": ir.depth}` to `{"name": ir.node.name, "label": ir.node.label.value, "file_path": ir.node.file_path, "depth": ir.depth}`. This matches the CLI formatter expectation at workflow_memory.py:1017.

**Micro-steps:**
- In review_impact(), add 'label': ir.node.label.value to the entry dict on line 235
- Verify the dict now contains all 4 keys expected by workflow_memory.py:1017

**TDD:**
- required: `false`
- reason: kuzu not available in dev/test environment — verify via grep assertion

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
grep -n '"label".*ir.node.label.value' .cnogo/scripts/context/__init__.py
```

**Done when:** [Observable outcome]

### Task 3: Add auto-index to graph-flows CLI command
**Files:** `.cnogo/scripts/workflow_memory.py`
**Action:**
In cmd_graph_flows(), add `graph.index()` on the line before `flows = graph.flows(max_depth=max_depth)` (line 883). This matches the auto-index pattern used by cmd_graph_dead (line 787) and cmd_graph_coupling (line 816).

**Micro-steps:**
- Add graph.index() call in cmd_graph_flows() before graph.flows(), matching the pattern in cmd_graph_dead() and cmd_graph_coupling()
- Verify the index() call is present via grep

**TDD:**
- required: `false`
- reason: Integration command — verify via grep that graph.index() precedes graph.flows()

**Verify:**
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/workflow_memory.py', doraise=True)"
grep -A2 'def cmd_graph_flows' .cnogo/scripts/workflow_memory.py | head -10
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/phases/heritage.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/context/__init__.py', doraise=True)"
python3 -c "import py_compile; py_compile.compile('.cnogo/scripts/workflow_memory.py', doraise=True)"
```

## Commit Message
```
fix(graph): heritage label lookup, blast-radius KeyError, and flows auto-index
```
