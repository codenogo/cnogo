# Plan 01: Establish context graph foundation: data model, SQLite storage backend, and ContextGraph class skeleton

## Goal
Establish context graph foundation: data model, SQLite storage backend, and ContextGraph class skeleton

## Tasks

### Task 1: Port graph data model from axon
**Files:** `scripts/context/model.py`, `tests/test_context_model.py`
**Action:**
Port axon's GraphNode/GraphRelationship dataclasses and NodeLabel/RelType enums. Use dataclasses and enum stdlib modules. GraphNode properties: id, label, name, file_path, start_line, end_line, content, signature, language, class_name, is_dead, is_entry_point, is_exported, properties dict. Deterministic ID format: '{label.value}:{file_path}:{symbol_name}'.

**Micro-steps:**
- Write tests for NodeLabel enum values and RelType enum values
- Write tests for GraphNode dataclass creation and deterministic ID generation
- Write tests for GraphRelationship dataclass creation
- Run tests to verify RED
- Implement NodeLabel enum (10 types: FILE, FOLDER, FUNCTION, CLASS, METHOD, INTERFACE, TYPE_ALIAS, ENUM, COMMUNITY, PROCESS)
- Implement RelType enum (11 types: CONTAINS, DEFINES, CALLS, IMPORTS, EXTENDS, IMPLEMENTS, USES_TYPE, EXPORTS, MEMBER_OF, STEP_IN_PROCESS, COUPLED_WITH)
- Implement GraphNode dataclass with deterministic generate_id() function (format: label:file_path:symbol_name)
- Implement GraphRelationship dataclass with source/target/type/properties
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_model.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_model.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_model.py -x
```

**Done when:** [Observable outcome]

### Task 2: Implement SQLite storage backend
**Files:** `scripts/context/storage.py`, `tests/test_context_storage.py`
**Action:**
SQLite-backed storage using stdlib sqlite3. Three tables: nodes (id PRIMARY KEY, label, name, file_path, start_line, end_line, content, signature, language, class_name, is_dead, is_entry_point, is_exported, properties_json), relationships (id PRIMARY KEY, type, source, target, properties_json), file_hashes (file_path PRIMARY KEY, content_hash). Add indexes on nodes.label, nodes.file_path, relationships.source, relationships.target, relationships.type. Use context manager pattern for connection lifecycle. Follow memory engine's storage.py patterns (with_retry, WAL mode).

**Micro-steps:**
- Write tests for initialize() creating tables and is_initialized() returning True
- Write tests for add_nodes() and get_node() round-trip
- Write tests for add_relationships() and get_callers/get_callees
- Write tests for get_indexed_files() and remove_nodes_by_file() for incremental support
- Run tests to verify RED
- Implement initialize() with nodes, relationships, and file_hashes tables
- Implement add_nodes() with upsert (INSERT OR REPLACE)
- Implement add_relationships() with upsert
- Implement get_node(), get_callers(), get_callees()
- Implement get_indexed_files(), update_file_hash(), remove_nodes_by_file()
- Implement close()
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_storage.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_storage.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_storage.py -x
```

**Done when:** [Observable outcome]

### Task 3: Create ContextGraph class skeleton and package __init__
**Files:** `scripts/context/__init__.py`, `tests/test_context_graph.py`
**Action:**
Create scripts/context/__init__.py with ContextGraph class. Constructor takes repo_path, initializes storage at .cnogo/graph.db. is_indexed() checks node count > 0. Stub index/query/impact/context methods with NotImplementedError. Export ContextGraph, GraphNode, GraphRelationship, NodeLabel, RelType from package.

**Micro-steps:**
- Write tests for ContextGraph construction with repo_path
- Write tests for is_indexed() returning False on fresh DB and True after indexing
- Write tests for db_path pointing to .cnogo/graph.db
- Run tests to verify RED
- Create scripts/context/__init__.py with ContextGraph class
- Implement __init__(repo_path='.') setting up db_path = repo_path/.cnogo/graph.db
- Implement is_indexed() checking if nodes table has rows
- Implement stub methods for index(), query(), impact(), context() that raise NotImplementedError
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_context_graph.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_context_graph.py -x
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_model.py tests/test_context_storage.py tests/test_context_graph.py -x
```

## Commit Message
```
feat(context-graph): add graph data model, SQLite storage, and ContextGraph skeleton
```
