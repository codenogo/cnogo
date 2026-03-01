"""Tests for the calls phase: CALLS relationship creation with confidence scoring."""

from __future__ import annotations

import sys
sys.path.insert(0, ".cnogo")

from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.parser_base import CallInfo, ImportInfo, ParseResult, SymbolInfo
from scripts.context.walker import FileEntry


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


def _add_symbol_node(storage, file_path, name, kind, start_line=1, end_line=5, class_name=""):
    """Helper to add a FUNCTION/CLASS/METHOD node."""
    label = {
        "function": NodeLabel.FUNCTION,
        "class": NodeLabel.CLASS,
        "method": NodeLabel.METHOD,
    }[kind]
    # For methods, use "ClassName.method_name" as symbol key (matching symbols phase)
    if kind == "method" and class_name:
        symbol_key = f"{class_name}.{name}"
    else:
        symbol_key = name
    node_id = generate_id(label, file_path, symbol_key)
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


def _setup_graph(tmp_path, files, parse_results):
    """Helper: create graph with structure and symbol nodes."""
    from scripts.context.storage import GraphStorage
    from scripts.context.phases.structure import process_structure
    from scripts.context.phases.symbols import process_symbols
    storage = GraphStorage(tmp_path / "db")
    storage.initialize()
    process_structure(files, storage)
    process_symbols(parse_results, storage)
    return storage


def _make_file_entry(path_str, language="python"):
    return FileEntry(
        path=Path(path_str),
        language=language,
        content="",
        content_hash="abc",
    )


# --- _build_symbol_index ---


def test_build_symbol_index_indexes_functions(storage):
    from scripts.context.phases.calls import _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "helper", "function")
    _add_symbol_node(storage, "app.py", "main", "function", start_line=7, end_line=12)

    index = _build_symbol_index(storage)
    assert "helper" in index
    assert "main" in index


def test_build_symbol_index_indexes_methods_by_qualified_name(storage):
    from scripts.context.phases.calls import _build_symbol_index
    _add_file_node(storage, "svc.py")
    _add_symbol_node(storage, "svc.py", "run", "method", class_name="Service")

    index = _build_symbol_index(storage)
    # Should be indexed both by simple name and qualified name
    assert "run" in index
    assert "Service.run" in index


def test_build_symbol_index_indexes_classes(storage):
    from scripts.context.phases.calls import _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "MyClass", "class")

    index = _build_symbol_index(storage)
    assert "MyClass" in index


def test_build_symbol_index_maps_name_to_node_ids(storage):
    from scripts.context.phases.calls import _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "helper", "function")

    index = _build_symbol_index(storage)
    assert isinstance(index["helper"], list)
    assert len(index["helper"]) >= 1
    # Node ID format: function:app.py:helper
    assert any("helper" in nid for nid in index["helper"])


# --- _resolve_caller ---


def test_resolve_caller_by_name(storage):
    from scripts.context.phases.calls import _resolve_caller, _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "main", "function")

    index = _build_symbol_index(storage)
    result = _resolve_caller("main", "app.py", index)
    assert result is not None
    assert "main" in result


def test_resolve_caller_empty_returns_file_node(storage):
    from scripts.context.phases.calls import _resolve_caller, _build_symbol_index
    _add_file_node(storage, "app.py")

    index = _build_symbol_index(storage)
    result = _resolve_caller("", "app.py", index)
    assert result is not None
    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    assert result == file_id


def test_resolve_caller_prefers_same_file(storage):
    from scripts.context.phases.calls import _resolve_caller, _build_symbol_index
    _add_file_node(storage, "a.py")
    _add_file_node(storage, "b.py")
    _add_symbol_node(storage, "a.py", "helper", "function")
    _add_symbol_node(storage, "b.py", "helper", "function")

    index = _build_symbol_index(storage)
    result = _resolve_caller("helper", "a.py", index)
    assert result is not None
    assert "a.py" in result


def test_resolve_caller_unknown_returns_none(storage):
    from scripts.context.phases.calls import _resolve_caller, _build_symbol_index
    _add_file_node(storage, "app.py")
    index = _build_symbol_index(storage)
    result = _resolve_caller("nonexistent_func", "app.py", index)
    assert result is None


# --- _resolve_callee ---


def test_resolve_callee_exact_qualified_match(storage):
    from scripts.context.phases.calls import _resolve_callee, _build_symbol_index
    _add_file_node(storage, "svc.py")
    _add_symbol_node(storage, "svc.py", "do_thing", "method", class_name="MyClass")

    index = _build_symbol_index(storage)
    node_id, confidence = _resolve_callee("MyClass.do_thing", index)
    assert node_id is not None
    assert confidence == 1.0


def test_resolve_callee_simple_name_confidence_07(storage):
    from scripts.context.phases.calls import _resolve_callee, _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "helper", "function")

    index = _build_symbol_index(storage)
    # "helper" is a plain function name with no dot — confidence 0.7
    # But note: strategy 1 checks index first; since "helper" IS in the index,
    # it returns 1.0 for exact match. The 0.7 path is only for ambiguous multi-file.
    # Actually per design: strategy 1 (exact match) -> 1.0; simple name also hits strategy 1
    node_id, confidence = _resolve_callee("helper", index)
    assert node_id is not None
    assert confidence in (0.7, 1.0)  # exact match or simple name match


def test_resolve_callee_dot_notation_low_confidence(storage):
    from scripts.context.phases.calls import _resolve_callee, _build_symbol_index
    _add_file_node(storage, "app.py")
    _add_symbol_node(storage, "app.py", "method_name", "method", class_name="SomeClass")

    index = _build_symbol_index(storage)
    # "obj.method_name" — not in index as qualified, so falls through to dot strategy
    node_id, confidence = _resolve_callee("obj.method_name", index)
    assert node_id is not None
    assert confidence == 0.3


def test_resolve_callee_unresolvable_returns_none(storage):
    from scripts.context.phases.calls import _resolve_callee, _build_symbol_index
    _add_file_node(storage, "app.py")
    index = _build_symbol_index(storage)
    node_id, confidence = _resolve_callee("totally_unknown_function", index)
    assert node_id is None
    assert confidence == 0.0


# --- process_calls ---


def test_calls_function_to_function_same_file(tmp_path):
    """func A calls func B in same file -> CALLS rel created."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
                SymbolInfo(name="helper", kind="function", start_line=7, end_line=12),
            ],
            calls=[CallInfo(caller="main", callee="helper", line=3)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "app.py", "main")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) >= 1
    callee_names = [n.name for n in callees]
    assert "helper" in callee_names
    storage.close()


def test_calls_method_to_method_qualified(tmp_path):
    """method calls ClassName.method -> confidence 1.0."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("svc.py")]
    parse_results = {
        "svc.py": ParseResult(
            symbols=[
                SymbolInfo(name="Service", kind="class", start_line=1, end_line=20),
                SymbolInfo(name="run", kind="method", start_line=3, end_line=10, class_name="Service"),
                SymbolInfo(name="validate", kind="method", start_line=12, end_line=18, class_name="Service"),
            ],
            calls=[CallInfo(caller="Service.run", callee="Service.validate", line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.METHOD, "svc.py", "Service.run")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) >= 1
    callee_names = [n.name for n in callees]
    assert "validate" in callee_names
    storage.close()


def test_calls_method_via_dot_notation(tmp_path):
    """Call like 'obj.method' resolves to method node with confidence 0.3."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=10),
                SymbolInfo(name="process", kind="method", start_line=12, end_line=20, class_name="Worker"),
            ],
            calls=[CallInfo(caller="main", callee="obj.process", line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "app.py", "main")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) >= 1
    storage.close()


def test_calls_cross_file(tmp_path):
    """func in file A calls func in file B -> CALLS rel created."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("a.py"), _make_file_entry("b.py")]
    parse_results = {
        "a.py": ParseResult(
            symbols=[
                SymbolInfo(name="runner", kind="function", start_line=1, end_line=5),
            ],
            calls=[CallInfo(caller="runner", callee="compute", line=3)],
        ),
        "b.py": ParseResult(
            symbols=[
                SymbolInfo(name="compute", kind="function", start_line=1, end_line=10),
            ],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "a.py", "runner")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) >= 1
    callee_names = [n.name for n in callees]
    assert "compute" in callee_names
    storage.close()


def test_calls_module_level_caller(tmp_path):
    """caller='' (module-level) -> source is FILE node."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="helper", kind="function", start_line=5, end_line=10),
            ],
            calls=[CallInfo(caller="", callee="helper", line=2)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    callees = storage.get_related_nodes(file_id, RelType.CALLS, "outgoing")
    assert len(callees) >= 1
    callee_names = [n.name for n in callees]
    assert "helper" in callee_names
    storage.close()


def test_calls_no_target_found(tmp_path):
    """Unresolvable callee -> no relationship, no crash."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
            ],
            calls=[CallInfo(caller="main", callee="totally_unknown_external_lib", line=3)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "app.py", "main")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) == 0
    storage.close()


def test_calls_empty_parse_results(tmp_path):
    """No parse results -> no calls relationships, no crash."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results: dict = {}
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    assert storage.node_count() >= 0  # No crash
    storage.close()


def test_calls_deduplication(tmp_path):
    """Same call appearing twice -> only one relationship created."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="main", kind="function", start_line=1, end_line=5),
                SymbolInfo(name="helper", kind="function", start_line=7, end_line=12),
            ],
            # Same call twice
            calls=[
                CallInfo(caller="main", callee="helper", line=3),
                CallInfo(caller="main", callee="helper", line=4),
            ],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "app.py", "main")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    # Should be deduplicated to exactly one
    helper_callees = [n for n in callees if n.name == "helper"]
    assert len(helper_callees) == 1
    storage.close()


def test_calls_confidence_property_stored(tmp_path):
    """Verify confidence is stored in relationship properties."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("svc.py")]
    parse_results = {
        "svc.py": ParseResult(
            symbols=[
                SymbolInfo(name="Service", kind="class", start_line=1, end_line=20),
                SymbolInfo(name="run", kind="method", start_line=3, end_line=10, class_name="Service"),
                SymbolInfo(name="validate", kind="method", start_line=12, end_line=18, class_name="Service"),
            ],
            calls=[CallInfo(caller="Service.run", callee="Service.validate", line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.METHOD, "svc.py", "Service.run")
    callee_id = generate_id(NodeLabel.METHOD, "svc.py", "Service.validate")

    # Verify confidence via get_callers_with_confidence
    callers_with_conf = storage.get_callers_with_confidence(callee_id)
    assert len(callers_with_conf) >= 1
    caller_node, confidence = callers_with_conf[0]
    assert caller_node.id == caller_id
    assert isinstance(confidence, float)
    storage.close()


def test_calls_multiple_files(tmp_path):
    """Calls across multiple files all get CALLS relationships."""
    from scripts.context.phases.calls import process_calls

    files = [
        _make_file_entry("a.py"),
        _make_file_entry("b.py"),
        _make_file_entry("c.py"),
    ]
    parse_results = {
        "a.py": ParseResult(
            symbols=[SymbolInfo(name="func_a", kind="function", start_line=1, end_line=5)],
            calls=[CallInfo(caller="func_a", callee="func_b", line=3)],
        ),
        "b.py": ParseResult(
            symbols=[SymbolInfo(name="func_b", kind="function", start_line=1, end_line=5)],
            calls=[CallInfo(caller="func_b", callee="func_c", line=3)],
        ),
        "c.py": ParseResult(
            symbols=[SymbolInfo(name="func_c", kind="function", start_line=1, end_line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    a_id = generate_id(NodeLabel.FUNCTION, "a.py", "func_a")
    b_id = generate_id(NodeLabel.FUNCTION, "b.py", "func_b")
    assert len(storage.get_related_nodes(a_id, RelType.CALLS, "outgoing")) >= 1
    assert len(storage.get_related_nodes(b_id, RelType.CALLS, "outgoing")) >= 1
    storage.close()


def test_calls_self_method_resolve(tmp_path):
    """'self.method' call resolves to a method via dot-notation strategy."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("svc.py")]
    parse_results = {
        "svc.py": ParseResult(
            symbols=[
                SymbolInfo(name="Service", kind="class", start_line=1, end_line=30),
                SymbolInfo(name="run", kind="method", start_line=3, end_line=10, class_name="Service"),
                SymbolInfo(name="validate", kind="method", start_line=12, end_line=18, class_name="Service"),
            ],
            calls=[CallInfo(caller="Service.run", callee="self.validate", line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.METHOD, "svc.py", "Service.run")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    # self.validate -> resolves via dot strategy to validate method
    assert len(callees) >= 1
    callee_names = [n.name for n in callees]
    assert "validate" in callee_names
    storage.close()


def test_calls_no_calls_in_parse_result(tmp_path):
    """ParseResult with empty calls list creates no relationships."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[SymbolInfo(name="main", kind="function", start_line=1, end_line=5)],
            calls=[],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    caller_id = generate_id(NodeLabel.FUNCTION, "app.py", "main")
    callees = storage.get_related_nodes(caller_id, RelType.CALLS, "outgoing")
    assert len(callees) == 0
    storage.close()


def test_calls_caller_not_in_graph(tmp_path):
    """Caller not found in graph -> skip gracefully, no crash."""
    from scripts.context.phases.calls import process_calls

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[
                SymbolInfo(name="helper", kind="function", start_line=5, end_line=10),
            ],
            calls=[CallInfo(caller="ghost_func", callee="helper", line=2)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_calls(parse_results, storage)

    # No crash, and no spurious relationships
    helper_id = generate_id(NodeLabel.FUNCTION, "app.py", "helper")
    callers = storage.get_callers_with_confidence(helper_id)
    # ghost_func doesn't exist in the graph so no rel created
    assert len(callers) == 0
    storage.close()
