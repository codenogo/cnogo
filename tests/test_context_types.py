"""Tests for the types phase: USES_TYPE relationships."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import sys
sys.path.insert(0, ".cnogo")

from scripts.context.model import NodeLabel, RelType, GraphNode, GraphRelationship, generate_id
from scripts.context.storage import GraphStorage
from scripts.context.parser_base import ParseResult, SymbolInfo, TypeRef, ImportInfo, CallInfo
from scripts.context.phases.structure import process_structure
from scripts.context.phases.symbols import process_symbols
from scripts.context.walker import FileEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_entry(path_str: str, content: str = "") -> FileEntry:
    return FileEntry(
        path=Path(path_str),
        language="python",
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def _setup_graph(tmp_path, files: list[FileEntry], parse_results: dict[str, ParseResult]) -> GraphStorage:
    """Create graph with structure + symbol nodes."""
    storage = GraphStorage(tmp_path / "db")
    storage.initialize()
    process_structure(files, storage)
    process_symbols(parse_results, storage)
    return storage


# ---------------------------------------------------------------------------
# Types tests
# ---------------------------------------------------------------------------

def test_types_annotation_resolves(tmp_path):
    """TypeRef(kind='annotation') -> USES_TYPE from FILE to type node."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("service.py")]
    parse_results = {
        "service.py": ParseResult(
            symbols=[SymbolInfo(name="MyClass", kind="class", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="MyClass", kind="annotation", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "service.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "MyClass"
    storage.close()


def test_types_return_type_resolves(tmp_path):
    """TypeRef(kind='return_type') -> USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("api.py")]
    parse_results = {
        "api.py": ParseResult(
            symbols=[SymbolInfo(name="Response", kind="class", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="Response", kind="return_type", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "api.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "Response"
    storage.close()


def test_types_skip_primitives(tmp_path):
    """TypeRef with primitive type name -> no USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("utils.py")]
    parse_results = {
        "utils.py": ParseResult(
            type_refs=[
                TypeRef(name="str", kind="annotation", line=5),
                TypeRef(name="int", kind="return_type", line=6),
                TypeRef(name="bool", kind="annotation", line=7),
                TypeRef(name="None", kind="return_type", line=8),
            ],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "utils.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 0
    storage.close()


def test_types_skip_base_class(tmp_path):
    """TypeRef(kind='base_class') -> no USES_TYPE (handled by heritage phase)."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[SymbolInfo(name="Animal", kind="class", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="Animal", kind="base_class", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "models.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 0
    storage.close()


def test_types_unresolvable(tmp_path):
    """TypeRef with unknown type name -> no crash, no relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("code.py")]
    parse_results = {
        "code.py": ParseResult(
            type_refs=[TypeRef(name="NonExistentClass", kind="annotation", line=5)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    # Should not crash
    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "code.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 0
    storage.close()


def test_types_empty_results(tmp_path):
    """Empty parse_results -> no crash."""
    from scripts.context.phases.types import process_types

    storage = GraphStorage(tmp_path / "db")
    storage.initialize()

    # Should not crash
    process_types({}, storage)

    storage.close()


def test_types_dedup(tmp_path):
    """Same type ref appearing twice -> only one USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("svc.py")]
    parse_results = {
        "svc.py": ParseResult(
            symbols=[SymbolInfo(name="Config", kind="class", start_line=1, end_line=5)],
            type_refs=[
                TypeRef(name="Config", kind="annotation", line=10),
                TypeRef(name="Config", kind="annotation", line=15),  # duplicate
            ],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "svc.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    storage.close()


def test_types_resolves_interface(tmp_path):
    """TypeRef referencing INTERFACE node -> USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("types.py")]
    parse_results = {
        "types.py": ParseResult(
            symbols=[SymbolInfo(name="IFoo", kind="interface", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="IFoo", kind="annotation", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "types.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "IFoo"
    storage.close()


def test_types_resolves_type_alias(tmp_path):
    """TypeRef referencing TYPE_ALIAS node -> USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("aliases.py")]
    parse_results = {
        "aliases.py": ParseResult(
            symbols=[SymbolInfo(name="UserID", kind="type_alias", start_line=1, end_line=1)],
            type_refs=[TypeRef(name="UserID", kind="annotation", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "aliases.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "UserID"
    storage.close()


def test_types_resolves_enum(tmp_path):
    """TypeRef referencing ENUM node -> USES_TYPE relationship."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("enums.py")]
    parse_results = {
        "enums.py": ParseResult(
            symbols=[SymbolInfo(name="Color", kind="enum", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="Color", kind="annotation", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_id = generate_id(NodeLabel.FILE, "enums.py", "")
    related = storage.get_related_nodes(file_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "Color"
    storage.close()


def test_types_cross_file(tmp_path):
    """Type defined in file A, used in file B -> USES_TYPE from file B."""
    from scripts.context.phases.types import process_types

    files = [
        _make_file_entry("models.py"),
        _make_file_entry("service.py"),
    ]
    parse_results = {
        "models.py": ParseResult(
            symbols=[SymbolInfo(name="User", kind="class", start_line=1, end_line=10)],
        ),
        "service.py": ParseResult(
            type_refs=[TypeRef(name="User", kind="annotation", line=5)],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    file_b_id = generate_id(NodeLabel.FILE, "service.py", "")
    related = storage.get_related_nodes(file_b_id, RelType.USES_TYPE, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "User"
    storage.close()


def test_types_kind_property(tmp_path):
    """Relationship has kind stored in properties."""
    from scripts.context.phases.types import process_types

    files = [_make_file_entry("app.py")]
    parse_results = {
        "app.py": ParseResult(
            symbols=[SymbolInfo(name="Config", kind="class", start_line=1, end_line=5)],
            type_refs=[TypeRef(name="Config", kind="return_type", line=10)],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_types(parse_results, storage)

    # Verify via Cypher query that properties contain kind
    conn = storage._require_conn()
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) "
        "WHERE r.rel_type = 'uses_type' RETURN r.properties"
    )
    rows = []
    while result.has_next():
        rows.append(result.get_next())
    assert len(rows) == 1
    import json
    props = json.loads(rows[0][0])
    assert props.get("kind") == "return_type"
    storage.close()
