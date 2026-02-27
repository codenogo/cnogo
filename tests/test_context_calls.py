"""Tests for call tracing phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import CallInfo, ImportInfo, ParseResult, SymbolInfo


@pytest.fixture
def storage(tmp_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


def _add_file_node(storage, file_path):
    """Helper to add a FILE node."""
    node_id = generate_id(NodeLabel.FILE, file_path, "")
    storage.add_nodes([GraphNode(
        id=node_id,
        label=NodeLabel.FILE,
        name=Path(file_path).name,
        file_path=file_path,
    )])
    return node_id


def _add_symbol_node(storage, file_path, name, kind, start_line, end_line, class_name=""):
    """Helper to add a FUNCTION/CLASS/METHOD node."""
    label = {
        "function": NodeLabel.FUNCTION,
        "class": NodeLabel.CLASS,
        "method": NodeLabel.METHOD,
    }[kind]
    node_id = generate_id(label, file_path, name)
    storage.add_nodes([GraphNode(
        id=node_id,
        label=label,
        name=name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        class_name=class_name,
    )])
    return node_id


def _add_defines_edge(storage, file_path, symbol_node_id):
    """Helper to add a DEFINES edge from file to symbol."""
    file_id = generate_id(NodeLabel.FILE, file_path, "")
    rel_id = f"defines:{file_id}->{symbol_node_id}"
    storage.add_relationships([GraphRelationship(
        id=rel_id,
        type=RelType.DEFINES,
        source=file_id,
        target=symbol_node_id,
    )])


def _add_imports_edge(storage, source_file, target_file, symbols=None):
    """Helper to add an IMPORTS edge."""
    source_id = generate_id(NodeLabel.FILE, source_file, "")
    target_id = generate_id(NodeLabel.FILE, target_file, "")
    rel_id = f"imports:{source_id}->{target_id}"
    props = {"symbols": symbols} if symbols else {}
    storage.add_relationships([GraphRelationship(
        id=rel_id,
        type=RelType.IMPORTS,
        source=source_id,
        target=target_id,
        properties=props,
    )])


# --- find_containing_symbol ---


def test_find_containing_symbol_exact():
    from scripts.context.phases.calls import find_containing_symbol
    symbols = [
        SymbolInfo(name="foo", kind="function", start_line=1, end_line=5),
        SymbolInfo(name="bar", kind="function", start_line=7, end_line=12),
    ]
    result = find_containing_symbol(3, symbols)
    assert result is not None
    assert result.name == "foo"


def test_find_containing_symbol_none_outside():
    from scripts.context.phases.calls import find_containing_symbol
    symbols = [
        SymbolInfo(name="foo", kind="function", start_line=5, end_line=10),
    ]
    result = find_containing_symbol(15, symbols)
    assert result is None


def test_find_containing_symbol_method():
    from scripts.context.phases.calls import find_containing_symbol
    symbols = [
        SymbolInfo(name="MyClass", kind="class", start_line=1, end_line=20),
        SymbolInfo(name="do_thing", kind="method", start_line=5, end_line=10, class_name="MyClass"),
        SymbolInfo(name="other", kind="method", start_line=12, end_line=18, class_name="MyClass"),
    ]
    # Line 7 is inside do_thing — prefer method over class
    result = find_containing_symbol(7, symbols)
    assert result is not None
    assert result.name == "do_thing"


# --- blocklist ---


def test_blocklist_skips_builtins():
    from scripts.context.phases.calls import CALL_BLOCKLIST
    for name in ["print", "len", "range", "isinstance", "hasattr", "getattr",
                  "setattr", "super", "type", "enumerate"]:
        assert name in CALL_BLOCKLIST


# --- same-file call resolution (confidence 1.0) ---


def test_resolve_same_file_call(storage):
    from scripts.context.phases.calls import process_calls
    import json

    _add_file_node(storage, "app.py")
    sid_caller = _add_symbol_node(storage, "app.py", "main", "function", 1, 5)
    sid_callee = _add_symbol_node(storage, "app.py", "helper", "function", 7, 12)
    _add_defines_edge(storage, "app.py", sid_caller)
    _add_defines_edge(storage, "app.py", sid_callee)

    parse_results = {
        "app.py": ParseResult(
            file_path="app.py",
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
                SymbolInfo(name="helper", kind="function", start_line=7, end_line=12),
            ],
            calls=[CallInfo(name="helper", line=3)],
        ),
    }
    process_calls(parse_results, storage)

    assert storage._conn is not None
    cur = storage._conn.execute(
        "SELECT properties_json FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert props["confidence"] == 1.0


# --- import-resolved call resolution (confidence 1.0) ---


def test_resolve_import_resolved_call(storage):
    from scripts.context.phases.calls import process_calls
    import json

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "utils.py")
    sid_caller = _add_symbol_node(storage, "main.py", "run", "function", 1, 5)
    sid_callee = _add_symbol_node(storage, "utils.py", "parse", "function", 1, 10)
    _add_defines_edge(storage, "main.py", sid_caller)
    _add_defines_edge(storage, "utils.py", sid_callee)
    _add_imports_edge(storage, "main.py", "utils.py", symbols=["parse"])

    parse_results = {
        "main.py": ParseResult(
            file_path="main.py",
            symbols=[
                SymbolInfo(name="run", kind="function", start_line=1, end_line=5),
            ],
            imports=[ImportInfo(module="utils", names=["parse"], is_relative=False, level=0)],
            calls=[CallInfo(name="parse", line=3)],
        ),
    }
    process_calls(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT properties_json FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert props["confidence"] == 1.0


# --- receiver method call (self/cls → confidence 0.8) ---


def test_resolve_self_method_call(storage):
    from scripts.context.phases.calls import process_calls
    import json

    _add_file_node(storage, "svc.py")
    sid_class = _add_symbol_node(storage, "svc.py", "Service", "class", 1, 20)
    sid_caller = _add_symbol_node(storage, "svc.py", "run", "method", 3, 10, class_name="Service")
    sid_callee = _add_symbol_node(storage, "svc.py", "validate", "method", 12, 18, class_name="Service")
    _add_defines_edge(storage, "svc.py", sid_class)
    _add_defines_edge(storage, "svc.py", sid_caller)
    _add_defines_edge(storage, "svc.py", sid_callee)

    parse_results = {
        "svc.py": ParseResult(
            file_path="svc.py",
            symbols=[
                SymbolInfo(name="Service", kind="class", start_line=1, end_line=20),
                SymbolInfo(name="run", kind="method", start_line=3, end_line=10, class_name="Service"),
                SymbolInfo(name="validate", kind="method", start_line=12, end_line=18, class_name="Service"),
            ],
            calls=[CallInfo(name="validate", line=5, receiver="self")],
        ),
    }
    process_calls(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT properties_json FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert props["confidence"] == 0.8


# --- global fuzzy match (confidence 0.5) ---


def test_resolve_global_fuzzy_call(storage):
    from scripts.context.phases.calls import process_calls
    import json

    _add_file_node(storage, "a.py")
    _add_file_node(storage, "b.py")
    sid_caller = _add_symbol_node(storage, "a.py", "main", "function", 1, 5)
    sid_callee = _add_symbol_node(storage, "b.py", "compute", "function", 1, 10)
    _add_defines_edge(storage, "a.py", sid_caller)
    _add_defines_edge(storage, "b.py", sid_callee)

    # No import edge — so it's a global fuzzy match
    parse_results = {
        "a.py": ParseResult(
            file_path="a.py",
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
            ],
            calls=[CallInfo(name="compute", line=3)],
        ),
    }
    process_calls(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT properties_json FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert props["confidence"] == 0.5


# --- blocklist filtering ---


def test_process_calls_skips_blocklisted(storage):
    from scripts.context.phases.calls import process_calls

    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "main", "function", 1, 5)
    _add_defines_edge(storage, "app.py", generate_id(NodeLabel.FUNCTION, "app.py", "main"))

    parse_results = {
        "app.py": ParseResult(
            file_path="app.py",
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
            ],
            calls=[CallInfo(name="print", line=3), CallInfo(name="len", line=4)],
        ),
    }
    process_calls(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT * FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 0


# --- no caller attribution for module-level calls ---


def test_process_calls_no_caller_outside_symbol(storage):
    from scripts.context.phases.calls import process_calls

    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "helper", "function", 5, 10)
    _add_defines_edge(storage, "app.py", generate_id(NodeLabel.FUNCTION, "app.py", "helper"))

    parse_results = {
        "app.py": ParseResult(
            file_path="app.py",
            symbols=[
                SymbolInfo(name="helper", kind="function", start_line=5, end_line=10),
            ],
            # Call at line 2 is at module level, outside any symbol
            calls=[CallInfo(name="helper", line=2)],
        ),
    }
    process_calls(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT source FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    # Source should be the FILE node when no containing symbol
    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    assert row[0] == file_id
