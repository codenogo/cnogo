# Context: context-graph

> Full stdlib port of axon's context graph into cnogo.

## Summary

Port [axon](https://github.com/harshkedia177/axon)'s code knowledge graph into cnogo as a new `scripts/context/` package. Stdlib-only, Python-first, SQLite-backed. Gives workflow commands structural code understanding: call graphs, import dependencies, inheritance hierarchies.

## Key Decisions

### Architecture
- **Package**: `scripts/context/` (new, parallel to `scripts/memory/`)
- **Storage**: `.cnogo/graph.db` (separate from `memory.db`)
- **API**: OOP `ContextGraph` class with `index()`, `query()`, `impact()`, `context()`, `is_indexed()`

### Indexing Strategy
- **Explicit CLI**: `python3 scripts/workflow_memory.py graph-index`
- **Auto**: triggered by `/review` and `/plan` when graph is stale
- **Hook**: PostCommit hook for incremental re-index
- **Incremental**: file hash tracking from day one — only re-parse changed files

### MVP Scope (Core 6 Phases)
1. **File walking** — `pathlib.rglob()` + gitignore filtering
2. **Structure** — File/Folder nodes + CONTAINS edges
3. **Python parsing** — `ast` module → Function/Class/Method nodes + DEFINES edges
4. **Import resolution** — IMPORTS edges between files
5. **Call tracing** — CALLS edges with confidence scoring (1.0/0.8/0.5)
6. **Heritage** — EXTENDS/IMPLEMENTS edges for class inheritance

### Post-MVP Phases (Status)
- ~~Impact analysis (BFS blast radius)~~ — Plan 04
- ~~Dead code detection (multi-pass reachability)~~ — Plan 05
- ~~Structural coupling (Jaccard similarity)~~ — Plan 06
- ~~Review/workflow integration~~ — Plans 07, 09
- ~~Community detection (label propagation)~~ — Plan 08
- ~~Execution flow tracing (entry point BFS)~~ — Plan 10
- **BM25 search (SQLite FTS5 + porter stemming)** — Plan 11 (next)
- **USES_TYPE edges (type reference linking)** — Plan 12
- **EXPORTS edges (__all__ export linking)** — Plan 13

### Data Model (ported from axon)
- **10 node types**: File, Folder, Function, Class, Method, Interface, TypeAlias, Enum, Community, Process
- **11 relationship types**: CONTAINS, DEFINES, CALLS, IMPORTS, EXTENDS, IMPLEMENTS, USES_TYPE, EXPORTS, MEMBER_OF, STEP_IN_PROCESS, COUPLED_WITH
- **Node ID format**: `{label}:{file_path}:{symbol_name}` (deterministic)

## Constraints
- Python 3.10+ stdlib only
- Max 800 lines per file
- Must not break existing memory engine or workflow commands

### Search (Plan 11)
- **FTS5** virtual table over symbol names, signatures, and docstrings
- **Porter stemming** tokenizer (user choice — better recall for natural language)
- **Docstrings** extracted via `ast.get_docstring()`, stored in `nodes.content` column
- FTS table populated during `index()` pipeline, rebuilt on incremental reindex

### Type References (Plan 12)
- **USES_TYPE edges** from `ParseResult.type_refs` (already parsed, not yet persisted)
- Connects symbols to their type annotations (param types, return types)

### Exports (Plan 13)
- **EXPORTS edges** from `ParseResult.exports` (already parsed from `__all__`, not yet linked)
- Connects files to their publicly exported symbols

## Open Questions
- Should `graph-search` CLI support prefix/wildcard queries in addition to BM25 full-text?

## Related
- Brainstorm: `docs/planning/work/ideas/context-graph/BRAINSTORM.md`
- Axon source: https://github.com/harshkedia177/axon
- Memory engine: `scripts/memory/`
