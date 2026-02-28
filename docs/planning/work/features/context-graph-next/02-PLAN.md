# Plan 02: Add graph visualization with Mermaid and DOT output formats via a new graph-viz CLI command

## Goal
Add graph visualization with Mermaid and DOT output formats via a new graph-viz CLI command

## Tasks

### Task 1: Create visualization module with Mermaid and DOT renderers
**Files:** `scripts/context/visualization.py`, `tests/test_context_visualization.py`
**Action:**
Create visualization module with two renderers sharing common graph traversal. _collect_subgraph(storage, scope, center, depth) collects nodes and edges within scope via BFS. render_mermaid(nodes, edges) produces Mermaid flowchart. render_dot(nodes, edges) produces DOT digraph. Scope options: 'file' (single file's symbols), 'module' (directory), 'full' (entire graph). Depth limits BFS from center node. Node labels show symbol name and type; edge labels show relationship type.

**Micro-steps:**
- Write failing tests for render_mermaid() and render_dot() functions
- Run tests to verify RED
- Create scripts/context/visualization.py with _collect_subgraph(storage, scope, center, depth)
- Implement render_mermaid(nodes, edges) producing valid Mermaid flowchart syntax
- Implement render_dot(nodes, edges) producing valid DOT/Graphviz digraph syntax
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v`
- passingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v`

**Verify:**
```bash
python3 -m pytest tests/test_context_visualization.py -v
```

**Done when:** [Observable outcome]

### Task 2: Add visualize() method to ContextGraph and graph-viz CLI command
**Files:** `scripts/context/__init__.py`, `scripts/workflow_memory.py`, `tests/test_context_visualization.py`
**Action:**
Add ContextGraph.visualize(scope='file'|'module'|'full', center=None, depth=3, format='mermaid'|'dot') that delegates to visualization module. Add graph-viz CLI command: --format mermaid|dot (default: mermaid), --scope file|module|full (default: file), --depth N (default: 3), --center PATH (file or symbol). Output goes to stdout for piping/redirection.

**Micro-steps:**
- Write failing test for ContextGraph.visualize() method
- Run test to verify RED
- Add visualize(scope, center, depth, format) method to ContextGraph
- Add graph-viz subcommand to workflow_memory.py with --format, --scope, --depth, --center flags
- Run tests to verify GREEN
- Verify CLI produces valid Mermaid output end-to-end

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v -k test_visualize`
- passingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v -k test_visualize`

**Verify:**
```bash
python3 -m pytest tests/test_context_visualization.py -v
python3 scripts/workflow_memory.py graph-viz --help 2>&1 | grep -q viz
```

**Done when:** [Observable outcome]

### Task 3: End-to-end visualization tests with indexed graph
**Files:** `tests/test_context_visualization.py`
**Action:**
Add end-to-end tests that create a temp repo with sample Python files, index it, then verify visualization output. Verify: Mermaid contains expected flowchart nodes/edges and is parseable, DOT contains expected digraph structure. Test scope filtering (file scope shows only that file's symbols, module scope shows directory, full shows all). Test depth limiting reduces output for deep graphs.

**Micro-steps:**
- Write integration test that indexes sample code and generates Mermaid output
- Write integration test that indexes sample code and generates DOT output
- Verify Mermaid output contains expected node labels and edges
- Verify DOT output contains expected digraph structure
- Test scope filtering (file vs module vs full) and depth limiting
- Run full test suite

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v -k test_e2e`
- passingVerify:
  - `python3 -m pytest tests/test_context_visualization.py -v -k test_e2e`

**Verify:**
```bash
python3 -m pytest tests/test_context_visualization.py -v
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_visualization.py -v
python3 scripts/workflow_memory.py graph-viz --help 2>&1 | grep -q viz
```

## Commit Message
```
feat(context-graph-next): add graph visualization with Mermaid and DOT output formats
```
