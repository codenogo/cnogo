# Graph Proximity Mechanism

## Problem

The `graph-prioritize` CLI command expects BFS-based proximity ranking from focal symbols, but `prioritize_context()` only counts total connections (no BFS, no focal symbols, no distance). The function signature doesn't match the CLI caller either.

## Decisions

| Area | Decision |
|------|----------|
| Algorithm | Bidirectional BFS over all edge types. Rank files by shortest distance to any seed node. |
| Input | Hybrid: `--symbols` (focal names) and `--files` (file paths). Falls back to centrality if neither given. |
| Architecture | New `phases/proximity.py` with BFS logic. `ContextGraph.prioritize_files()` delegates to it. `workflow.py` updated. |
| Depth | Default max depth 3, configurable via `--max-depth`. |
| Output | `[{path, distance, reason}]` — matches CLI formatter expectations. |
| Contract fix | `prioritize_context()` signature updated to accept `focal_symbols`, `max_files`, `max_depth`. |

## Constraints

- Python stdlib only (`collections.deque` for BFS)
- Parameterized Cypher queries
- Graceful handling of disconnected graphs and empty graphs

## Related Code

- `.cnogo/scripts/context/phases/proximity.py` (new)
- `.cnogo/scripts/context/__init__.py` — `prioritize_files()` method
- `.cnogo/scripts/context/workflow.py` — `prioritize_context()` wrapper
- `.cnogo/scripts/context/storage.py` — edge traversal queries
- `.cnogo/scripts/workflow_memory.py` — CLI `graph-prioritize` command + arg parser

## Prior Work

Deferred from `graph-integrity-fixes` (finding P2-proximity-defer).
