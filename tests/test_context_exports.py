"""Tests for the exports phase: EXPORTS relationship creation."""

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
from scripts.context.parser_base import ParseResult, SymbolInfo
from scripts.context.walker import FileEntry


def _make_file_entry(path_str, language="python"):
    return FileEntry(
        path=Path(path_str),
        language=language,
        content="",
        content_hash="abc",
    )


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


# --- process_exports ---


def test_exports_function(tmp_path):
    """exports=['helper'] -> EXPORTS rel from FILE to function node."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("utils.py")]
    parse_results = {
        "utils.py": ParseResult(
            symbols=[SymbolInfo(name="helper", kind="function", start_line=1, end_line=5)],
            exports=["helper"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "utils.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    assert len(exported) >= 1
    names = [n.name for n in exported]
    assert "helper" in names
    storage.close()


def test_exports_class(tmp_path):
    """exports=['MyClass'] -> EXPORTS rel from FILE to class node."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[SymbolInfo(name="MyClass", kind="class", start_line=1, end_line=10)],
            exports=["MyClass"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "models.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    assert len(exported) >= 1
    names = [n.name for n in exported]
    assert "MyClass" in names
    storage.close()


def test_exports_multiple(tmp_path):
    """exports=['func_a', 'func_b'] -> 2 EXPORTS rels."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("lib.py")]
    parse_results = {
        "lib.py": ParseResult(
            symbols=[
                SymbolInfo(name="func_a", kind="function", start_line=1, end_line=5),
                SymbolInfo(name="func_b", kind="function", start_line=7, end_line=12),
            ],
            exports=["func_a", "func_b"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "lib.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    names = [n.name for n in exported]
    assert "func_a" in names
    assert "func_b" in names
    assert len(names) >= 2
    storage.close()


def test_exports_unknown_name(tmp_path):
    """exports=['nonexistent'] -> no crash, no rel created."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[SymbolInfo(name="real_func", kind="function", start_line=1, end_line=5)],
            exports=["nonexistent"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    assert len(exported) == 0
    storage.close()


def test_exports_empty(tmp_path):
    """No exports -> no EXPORTS rels created."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[SymbolInfo(name="main", kind="function", start_line=1, end_line=5)],
            exports=[],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    assert len(exported) == 0
    storage.close()


def test_exports_empty_results(tmp_path):
    """Empty parse_results -> no crash."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("app.py")]
    storage = _setup_graph(tmp_path, files, {})
    process_exports({}, storage)

    assert storage.node_count() >= 0  # No crash
    storage.close()


def test_exports_dedup(tmp_path):
    """Same name twice in exports -> only one EXPORTS rel."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("utils.py")]
    parse_results = {
        "utils.py": ParseResult(
            symbols=[SymbolInfo(name="helper", kind="function", start_line=1, end_line=5)],
            exports=["helper", "helper"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "utils.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    helper_nodes = [n for n in exported if n.name == "helper"]
    assert len(helper_nodes) == 1
    storage.close()


def test_exports_cross_file_unaffected(tmp_path):
    """Exports only finds symbols in the same file, not in other files."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("a.py"), _make_file_entry("b.py")]
    parse_results = {
        "a.py": ParseResult(
            symbols=[SymbolInfo(name="func_a", kind="function", start_line=1, end_line=5)],
            exports=["func_b"],  # func_b is in b.py, not a.py
        ),
        "b.py": ParseResult(
            symbols=[SymbolInfo(name="func_b", kind="function", start_line=1, end_line=5)],
            exports=[],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    # a.py exports "func_b" but that symbol is in b.py, not a.py -> no rel
    file_a_id = generate_id(NodeLabel.FILE, "a.py", "")
    exported_a = storage.get_related_nodes(file_a_id, RelType.EXPORTS, "outgoing")
    assert len(exported_a) == 0

    # b.py has no exports
    file_b_id = generate_id(NodeLabel.FILE, "b.py", "")
    exported_b = storage.get_related_nodes(file_b_id, RelType.EXPORTS, "outgoing")
    assert len(exported_b) == 0
    storage.close()


def test_exports_method(tmp_path):
    """exports=['do_work'] where do_work is a method -> EXPORTS rel created."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("service.py")]
    parse_results = {
        "service.py": ParseResult(
            symbols=[
                SymbolInfo(name="MyService", kind="class", start_line=1, end_line=20),
                SymbolInfo(name="do_work", kind="method", start_line=3, end_line=10, class_name="MyService"),
            ],
            exports=["do_work"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "service.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    names = [n.name for n in exported]
    assert "do_work" in names
    storage.close()


def test_exports_mixed_known_and_unknown(tmp_path):
    """exports=['real', 'ghost'] -> only real gets a rel."""
    from scripts.context.phases.exports import process_exports

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[SymbolInfo(name="real", kind="function", start_line=1, end_line=5)],
            exports=["real", "ghost"],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)
    process_exports(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "app.py", "")
    exported = storage.get_related_nodes(file_id, RelType.EXPORTS, "outgoing")
    names = [n.name for n in exported]
    assert "real" in names
    assert "ghost" not in names
    assert len(names) == 1
    storage.close()
