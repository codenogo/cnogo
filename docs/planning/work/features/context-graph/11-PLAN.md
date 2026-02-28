# Plan 11: Add BM25 full-text search over symbol names, signatures, and docstrings using SQLite FTS5 with porter stemming.

## Goal
Add BM25 full-text search over symbol names, signatures, and docstrings using SQLite FTS5 with porter stemming.

## Tasks

### Task 1: Add FTS5 table and search methods to GraphStorage
**Files:** `scripts/context/storage.py`, `tests/test_context_storage.py`
**Action:**
Add FTS5 virtual table to storage schema using content-sync mode (content=nodes). The FTS table indexes name, signature, and content columns. Add rebuild_fts() for full rebuild after batch inserts, search(query, limit) for BM25-ranked queries, and FTS cleanup in remove_nodes_by_file(). Use tokenize='porter unicode61' for stemmed matching.

**Micro-steps:**
- Write tests: FTS table created on initialize(), search returns ranked results by BM25, search returns empty for no match, FTS entries removed when nodes are removed, FTS handles special characters gracefully
- Run tests to verify RED (no search method exists)
- Add CREATE VIRTUAL TABLE nodes_fts USING fts5(name, signature, content, content=nodes, content_rowid=rowid, tokenize='porter unicode61') to initialize()
- Add rebuild_fts() method that runs INSERT INTO nodes_fts(nodes_fts) VALUES('rebuild')
- Add search(query, limit=20) method that queries nodes_fts with bm25() ranking and joins back to nodes table
- Add FTS cleanup to remove_nodes_by_file() so FTS stays in sync on incremental reindex
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_storage.py -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_storage.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_storage.py -x -q
```

**Done when:** [Observable outcome]

### Task 2: Extract docstrings in symbols phase and wire FTS rebuild into index pipeline
**Files:** `scripts/context/python_parser.py`, `scripts/context/phases/symbols.py`, `scripts/context/__init__.py`, `tests/test_context_graph.py`
**Action:**
Add docstring extraction to the parser and symbols phase. In python_parser.py, add a docstring field to SymbolInfo and extract via ast.get_docstring() in _extract_symbols(). In symbols.py, pass the docstring as the content field on GraphNode. In __init__.py, call storage.rebuild_fts() after all phases complete in index() to sync the FTS index. This ensures FTS is always up-to-date after any indexing run.

**Micro-steps:**
- Write tests: docstrings populated in content field after indexing, FTS search finds symbols by docstring keywords, FTS search finds symbols by partial name
- Run tests to verify RED
- Add docstring field to SymbolInfo dataclass in python_parser.py
- Extract docstrings via ast.get_docstring() in _extract_symbols() for functions, classes, and methods
- Pass docstring to content field when creating GraphNode in symbols.py process_symbols()
- Add storage.rebuild_fts() call at end of index() pipeline in __init__.py (after all phases, before hash update)
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_graph.py -x -q
```

**Done when:** [Observable outcome]

### Task 3: Add search() API method and graph-search CLI subcommand
**Files:** `scripts/context/__init__.py`, `scripts/workflow_memory.py`, `tests/test_context_graph.py`, `tests/test_context_cli.py`
**Action:**
Add search() method to ContextGraph class that auto-indexes then delegates to storage.search(). Add cmd_graph_search() CLI handler with human-readable table output (name, file, label, score) and --json mode. Register graph-search subparser with --repo, --query (required positional), --limit (default 20), --json flags.

**Micro-steps:**
- Write tests: ContextGraph.search() returns ranked results, search() with limit, search() exported in package; CLI tests: graph-search --help, empty repo, with indexed symbols, --json output, --limit flag
- Run tests to verify RED
- Add search(query, limit=20) method to ContextGraph that delegates to storage.search()
- Add cmd_graph_search() to workflow_memory.py with human-readable and --json output, --limit flag
- Register graph-search subparser with --repo, --query, --limit, --json arguments
- Add graph-search to _graph_cmds set and dispatch dict
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py tests/test_context_cli.py -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py tests/test_context_cli.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_graph.py tests/test_context_cli.py -x -q
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_storage.py tests/test_context_graph.py tests/test_context_cli.py -x -q
```

## Commit Message
```
feat(context-graph): add BM25 full-text search with FTS5 porter stemming, docstring extraction, and graph-search CLI
```
