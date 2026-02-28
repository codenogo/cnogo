# Context: context-graph-next

**Feature:** Context Graph Next — Workflow Wiring, Visualization, Context Optimization

## Background

The context graph (PR #28) and workflow integration (PR #29) are shipped. The graph provides a complete Python code knowledge graph with 14 CLI commands and 3 workflow functions. This feature extends the graph in three directions: deeper workflow wiring, visualization, and context window optimization.

## Decisions

### 1. Deeper Workflow Wiring

**Auto-populate plan files[]**: When `/plan` creates tasks, `graph-suggest-scope` results auto-fill the `files[]` array instead of being purely advisory. The graph's keyword search and impact analysis provide a reliable starting point for task file scoping.

**Test coverage mapping**: Map test functions to production code they call via CALLS edges. During `/review`, surface "untested callers" as warnings — functions that are called by changed code but have no test calling them.

**API contract break detection**: When a function signature changes between the indexed version and the current version, flag all callers that may break. This integrates into `/review` blast-radius analysis as a severity indicator.

### 2. Graph Visualization

Support both **Mermaid** and **DOT/Graphviz** output formats via a `--format` flag:
- Mermaid: inline in markdown, renders on GitHub, Claude can read/write natively
- DOT: more powerful layout, requires graphviz installed, better for large graphs
- Default: Mermaid (no external tools required)

New CLI command: `graph-viz` with options for scope (file, module, or full graph) and depth.

### 3. Context Window Optimization

Use graph proximity (call/import distance from focal point) to prioritize which files Claude should read. Instead of blindly including files, rank by graph distance from the symbols being worked on.

### 4. Housekeeping

Split `test_context_graph.py` (1026 lines, max 800) into logical test modules.

## Constraints

- Python stdlib only
- All CLI commands follow `graph-*` naming pattern
- Workflow integrations remain graceful (`enabled: false` on failure)
- Max 3 tasks per plan
- Mermaid as default visualization (no graphviz dependency required)

## Open Questions

- Context optimization: new workflow function or extend `enrich_context`?
- Test coverage mapping: how to reliably distinguish test files from production files?
- API contract detection: structural (AST) vs string-based signature comparison?

## Estimated Plans

| Plan | Scope | Tasks |
|------|-------|-------|
| 01 | Test file split + test coverage mapping | 3 |
| 02 | Graph visualization (Mermaid + DOT) | 3 |
| 03 | API contract detection + auto-populate plan files[] | 3 |
| 04 | Context window optimization | 2-3 |

## Related Code

- `scripts/context/__init__.py` — ContextGraph class
- `scripts/context/workflow.py` — workflow integration functions
- `scripts/context/phases/calls.py` — CALLS edge creation
- `scripts/context/phases/impact.py` — BFS impact analysis
- `tests/test_context_graph.py` — test file to split
- `.claude/commands/plan.md` — plan command (auto-populate target)
- `.claude/commands/review.md` — review command (contract detection target)
