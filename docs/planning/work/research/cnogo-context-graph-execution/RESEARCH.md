# Research: How cnogo Execution Works with the Integrated Context Graph

**Date:** 2026-02-28
**Mode:** local (repo-only)

## Architecture

The context graph is a **separate SQLite database** (`.cnogo/graph.db`) modeling code structure as a directed graph. It is deliberately decoupled from the memory engine (`.cnogo/memory.db`) — no bidirectional data flow.

| System | Database | Tracks |
|--------|----------|--------|
| Context graph | `.cnogo/graph.db` | Code structure: files, symbols, calls, imports, heritage, types, exports |
| Memory engine | `.cnogo/memory.db` | Workflow state: issues, tasks, dependencies, phases |

## Indexing Pipeline (10 phases)

```
walk files → compare SHA256 hashes → reprocess changed files only
    ↓
1. structure   — FILE/FOLDER nodes + CONTAINS edges
2. symbols     — FUNCTION/CLASS/METHOD nodes + DEFINES edges
3. imports     — IMPORTS edges between files
4. calls       — CALLS edges with confidence (1.0/0.8/0.5)
5. heritage    — EXTENDS/IMPLEMENTS edges
6. types       — USES_TYPE edges from annotations
7. exports     — EXPORTS edges from __all__ + is_exported flag
8. flows       — Process nodes from entry point BFS
9. FTS rebuild — BM25 full-text search index
10. hash update — Store SHA256 for next incremental run
```

## Three Integration Points

### 1. Automatic during `/review` (passive)

`workflow_checks_core.py:_graph_impact_section()` runs automatically:
- Auto-indexes the graph for freshness
- Runs BFS impact analysis on each changed file (max depth 3)
- Populates `REVIEW.json["impactAnalysis"]` with affected files, symbols, per-file breakdown
- Gracefully degrades: returns `{"enabled": false, "error": "..."}` on failure

### 2. PostCommit hook (passive)

After every `git commit`, the PostToolUse hook fires:
- `.cnogo/hooks/hook-post-commit-graph.sh` → `workflow_hooks.py:post_commit_graph()`
- Runs incremental reindex (only changed files)
- Keeps graph fresh for subsequent queries

### 3. CLI subcommands (active, on-demand)

11 `graph-*` commands available without memory engine:

| Command | Purpose |
|---------|---------|
| `graph-index` | Build/update graph |
| `graph-query <name>` | Find symbols by name |
| `graph-impact <file>` | BFS blast radius |
| `graph-context <node_id>` | Neighborhood (callers, callees, imports, heritage) |
| `graph-dead` | Unreferenced symbols |
| `graph-coupling` | Jaccard similarity pairs |
| `graph-communities` | Label propagation clusters |
| `graph-flows` | Entry point execution paths |
| `graph-search <query>` | BM25 full-text search |
| `graph-blast-radius` | Auto-detect changed files + impact |
| `graph-status` | Counts, staleness |

## Current Gaps

The graph is **well-integrated for passive analysis** but **underutilized for active workflow assistance**:

| Command | Graph Integration | Status |
|---------|-------------------|--------|
| `/review` | Auto impact analysis in REVIEW.json | Active |
| PostCommit | Auto incremental reindex | Active |
| `/plan` | None — file scope is manual | Gap |
| `/implement` | None — scope discipline is manual | Gap |
| `/discuss` | None — related code discovery is manual | Gap |

## Recommendation

**Highest-value next integrations:**

1. **`/plan` file scope suggestion** — Use `graph-impact` and `graph-context` to auto-suggest which files a task should touch, based on the symbols it needs to modify
2. **`/implement` scope validation** — After each task, verify changes don't have unintended blast radius beyond declared file scope
3. **`/discuss` context enrichment** — Auto-query callers/callees/heritage to surface architectural constraints before decisions

## Open Questions

- Should graph queries during `/plan` be opt-in or automatic?
- How should fuzzy (0.5 confidence) CALLS edges be treated in scope validation?
- Should the graph support cross-language analysis in a future milestone?
