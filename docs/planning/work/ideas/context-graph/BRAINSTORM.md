# Brainstorm: Context Graph for cnogo (Axon Port)

> Port axon's code knowledge graph into cnogo's workflow engine.

## Problem Statement

cnogo workflow commands (`/review`, `/plan`, `/ship`) operate on files and git diffs but lack structural understanding of code. When reviewing a change to `UserService.validate()`, the workflow doesn't know that 47 functions depend on that return type, 3 execution flows pass through it, and `payment_handler.py` changes alongside it 80% of the time. This structural blindness limits review scope accuracy, plan task decomposition, and ship safety checks.

[axon](https://github.com/harshkedia177/axon) solves this with a graph-powered code intelligence engine: 10 node types, 11 relationship types, 12-phase ingestion pipeline, impact analysis, community detection, and change coupling — all indexed once and queryable per-symbol.

## Questions Asked

| # | Question | Answer |
|---|----------|--------|
| 1 | Primary job-to-be-done? | All four: smarter /review scope, better /plan auto-scoping, full codebase understanding, change coupling insights |
| 2 | Dependency constraint? | Port axon's core into cnogo (build it ourselves) |
| 3 | Language support? | Porting axon — not integrating with it externally |

## Constraints

- cnogo is currently stdlib-only (Python 3.10+, no pip)
- Porting axon requires addressing: tree-sitter (parsing), kuzu (graph DB), igraph+leidenalg (communities), fastembed (embeddings)
- Must integrate with existing memory engine (SQLite-backed)
- Must enhance existing commands, not replace them
- install.sh is the single distribution mechanism

## Axon Component Portability Analysis

| Axon Component | External Dep | Stdlib Alternative | Quality Loss |
|----------------|-------------|-------------------|-------------|
| Python parsing | tree-sitter | `ast` module | Minimal — ast is mature for Python |
| TS/JS parsing | tree-sitter | None (skip initially) | No TS/JS support in MVP |
| Graph storage | KuzuDB | SQLite (nodes/edges tables) | No Cypher; custom SQL queries instead |
| BFS/impact | Pure Python | `collections.deque` | None — already stdlib-compatible |
| Community detection | igraph + leidenalg | Tarjan's SCC or label propagation | Simpler clusters, no modularity score |
| Change coupling | subprocess + git | Same | None — already stdlib-compatible |
| Embeddings | fastembed (ONNX) | TF-IDF with `math`+`collections` | Keyword-only, no semantic similarity |
| Hybrid search | BM25 + vector + fuzzy | BM25 + fuzzy (Levenshtein) | No vector search; BM25 is strong alone |
| File watching | watchfiles (Rust) | `os.stat` polling or skip | Slower; can use git-based delta instead |

## Candidate Directions

### A. Full Stdlib Port (Python-First MVP)

**Summary**: Port axon's graph model and core algorithms into cnogo using only stdlib. Start with Python-only parsing via `ast` module. SQLite for storage. Pure Python BFS, BM25, community detection.

**Who it serves**: Any Python project using cnogo. Later phases add multi-language.

**Architecture sketch**:
```
scripts/graph/
  __init__.py          # Public API: index(), query(), impact(), context()
  model.py             # Node/Edge dataclasses (port from axon)
  storage.py           # SQLite backend (nodes, edges, properties tables)
  parsers/
    __init__.py
    python_parser.py   # ast module parser → SymbolInfo, CallInfo, ImportInfo
  pipeline/
    __init__.py
    structure.py       # File/Folder nodes + CONTAINS edges
    symbols.py         # Function/Class/Method nodes + DEFINES edges
    calls.py           # CALLS edges with confidence scoring
    imports.py         # IMPORTS edges
    heritage.py        # EXTENDS/IMPLEMENTS edges
    types.py           # USES_TYPE edges
    coupling.py        # Git co-change → COUPLED_WITH edges
    communities.py     # Label propagation or SCC-based clustering
  analysis/
    impact.py          # Depth-grouped BFS traversal
    dead_code.py       # Multi-pass reachability
    flows.py           # Entry point detection + BFS flow tracing
  search/
    bm25.py            # BM25 ranking (pure Python)
    fuzzy.py           # Levenshtein distance matching
```

**In-scope**: Python AST parsing, call graph, impact analysis, dead code, change coupling, BM25 search, SQLite storage, workflow command integration.

**Out-of-scope**: TypeScript/JS, vector embeddings, Cypher query language, real-time file watching.

**Risks**:
1. `ast` module doesn't resolve cross-module calls well → confidence scoring mitigates
2. Community detection without igraph produces simpler clusters → label propagation is adequate for workflow use cases
3. Large codebases may be slow without optimized storage → SQLite indexes + incremental re-index

**MVP slice** (3 plans):
1. Graph model + SQLite storage + Python parser (structure, symbols, calls, imports)
2. Impact analysis + dead code detection + change coupling
3. Workflow integration: `/review` blast radius, `/plan` scope hints, `/ship` safety

---

### B. Layered Dependencies (Progressive Enhancement)

**Summary**: Build a stdlib core that works everywhere, with optional `pip install` for enhanced features. Tree-sitter unlocks multi-language. igraph unlocks better communities. fastembed unlocks semantic search.

**Architecture sketch**:
```
scripts/graph/
  core/               # stdlib-only (always available)
    model.py, storage.py, pipeline/, analysis/, search/
  optional/           # imported conditionally
    treesitter_parser.py   # tree-sitter Python/TS/JS
    leiden_communities.py  # igraph + leidenalg
    vector_search.py       # fastembed embeddings
  __init__.py         # Feature detection: try import, fallback to core
```

**Tradeoffs vs A**:
- Pro: Multi-language support when deps available
- Pro: Better community detection and semantic search when deps available
- Con: Two code paths to maintain (core + optional)
- Con: Violates cnogo's "zero deps" simplicity promise
- Con: install.sh must handle optional pip installs

**Risks**:
1. Feature parity divergence between core and optional layers
2. Testing matrix doubles (with/without each optional dep)
3. User confusion about which features require what

**MVP slice**: Same as A for core, plus tree-sitter integration in plan 4.

---

### C. Minimal Deps Port (tree-sitter only)

**Summary**: Accept tree-sitter as the single external dependency. Everything else is stdlib. This gets multi-language parsing (the hardest part to replicate) while keeping the rest pure.

**Rationale**: tree-sitter is the only axon dependency that has no adequate stdlib replacement. Graph storage (SQLite), algorithms (BFS, BM25), and git analysis (subprocess) all have strong stdlib implementations. Community detection can use label propagation. Only parsing truly needs tree-sitter for quality multi-language support.

**Tradeoffs vs A**:
- Pro: Python + TypeScript + JavaScript from day one
- Pro: Accurate parsing (tree-sitter is battle-tested)
- Con: Requires `pip install tree-sitter tree-sitter-python tree-sitter-typescript`
- Con: install.sh must handle pip dependency
- Con: Breaks the "zero deps" guarantee

**Risks**:
1. tree-sitter binary wheels may not exist for all platforms
2. pip requirement alienates users who chose cnogo for zero deps
3. tree-sitter API changes between versions

**MVP slice**: Same as A but with tree-sitter replacing ast module.

---

### D. Research-First Prototype (Validate Before Building)

**Summary**: Build the smallest possible prototype (Python-only, in-memory graph, no SQLite persistence) to validate that graph-powered insights actually improve `/review` and `/plan` quality. If validated, proceed with full port (Direction A).

**Architecture**: Single-file prototype (`scripts/graph_prototype.py`, <400 lines) that:
- Parses Python with `ast`
- Builds in-memory adjacency lists
- Runs BFS impact analysis on a changed symbol
- Outputs blast radius report

**Tradeoffs vs A**:
- Pro: Validates value before investing in full port
- Pro: Can be built in 1 plan (1-3 tasks)
- Con: Throwaway code if we proceed to full port
- Con: Doesn't test persistence, search, or community detection

**MVP slice**: 1 plan, 2 tasks: (1) prototype parser + graph, (2) wire into `/review` as experimental output.

## Recommendation

| Priority | Direction | Rationale |
|----------|-----------|-----------|
| **Primary** | **A. Full Stdlib Port** | Honors cnogo's zero-deps constraint. Python-first is pragmatic — most Claude Code projects are Python. `ast` module is surprisingly capable for call graph extraction. SQLite is already proven in memory engine. |
| **Backup** | **B. Layered** | If stdlib-only Python parsing proves insufficient (complex metaprogramming, decorators), the layered approach lets us add tree-sitter without rewriting. |

**Why not C**: Adding tree-sitter as a hard requirement is a bigger constraint violation than the value it provides in MVP. Multi-language can come later via the layered approach.

**Why not D**: The user's intent is clear ("port axon"). A research prototype adds a validation step that delays the actual port. The value of structural code understanding for review/plan/ship is well-established by axon's 370-star traction.

## Next Step

```
/discuss "Full stdlib port of axon's context graph into cnogo"
```
