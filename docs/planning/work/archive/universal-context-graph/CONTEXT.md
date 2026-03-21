# Context: Universal Context Graph

## Goal

Replace cnogo's Python-only context graph engine with a universal multi-language code intelligence engine. The current engine uses stdlib `ast` and SQLite — the new engine uses tree-sitter, KuzuDB, Leiden community detection, semantic embeddings, and live file watching.

## Inspiration

[Axon](https://github.com/harshkedia177/axon) — a graph-powered code intelligence engine with nearly identical node model, edge types, and 12-phase pipeline. Proves the architecture works universally with tree-sitter + KuzuDB.

## Decisions

| Area | Decision |
|------|----------|
| Architecture | Replace `scripts/context/` entirely — delete old, build new in same location |
| Parsing | tree-sitter (py-tree-sitter + per-language grammars) |
| Storage | KuzuDB (graph-native, Cypher queries) |
| Community detection | Leiden algorithm (igraph + leidenalg) |
| Search | Hybrid: BM25 + semantic vectors (384-dim) + fuzzy |
| Embeddings | BAAI/bge-small-en-v1.5 |
| File watching | watchfiles (live re-index) |
| Coupling | Jaccard + git history change coupling |
| Dependencies | requirements-graph.txt, pip installed via install.sh |
| Stdlib constraint | Removed for graph module |
| Interface | CLI subcommands + Python API only (no MCP server) |
| Data location | `.cnogo/graph.kuzu/` (project-specific), `~/.cache/cnogo/models/` (shared) |

## Constraints

- Old `scripts/context/` deleted entirely — no adapter layer
- All 14 analysis phases re-implemented with new deps
- Existing CLI subcommands and workflow.py functions must keep working
- install.sh handles pip install of graph deps
- Tree-sitter grammars installed as pip packages

## Open Questions

- Which tree-sitter grammars for initial release?
- watchfiles: background subprocess or `graph-index --watch`?
- Minimum Python version across all new deps?

## Plan Roadmap (from brainstorm)

1. Core engine — tree-sitter parsers + KuzuDB + walker + structure/symbols/imports phases
2. Relationship phases — calls, heritage, types, exports + hybrid search
3. Analysis phases — Leiden communities, git coupling, dead code, flows, impact
4. Embeddings + watchfiles + CLI integration
5. Delete old context/ module, update all references
