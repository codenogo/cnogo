"""Tests for import resolution phase."""

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
from scripts.context.python_parser import ImportInfo


@pytest.fixture
def storage(tmp_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


def _add_file_node(storage, file_path):
    """Helper to add a FILE node to storage."""
    node_id = generate_id(NodeLabel.FILE, file_path, "")
    storage.add_nodes([GraphNode(
        id=node_id,
        label=NodeLabel.FILE,
        name=Path(file_path).name,
        file_path=file_path,
    )])
    return node_id


# --- build_file_index ---


def test_build_file_index_maps_module_paths(storage):
    from scripts.context.phases.imports import build_file_index
    _add_file_node(storage, "scripts/memory/__init__.py")
    _add_file_node(storage, "scripts/memory/bridge.py")

    index = build_file_index(storage)
    assert "scripts.memory" in index
    assert "scripts.memory.bridge" in index


def test_build_file_index_simple_module(storage):
    from scripts.context.phases.imports import build_file_index
    _add_file_node(storage, "utils.py")

    index = build_file_index(storage)
    assert "utils" in index


def test_build_file_index_init_package(storage):
    from scripts.context.phases.imports import build_file_index
    _add_file_node(storage, "pkg/__init__.py")

    index = build_file_index(storage)
    # __init__.py maps to the package name
    assert "pkg" in index


# --- resolve_import: absolute imports ---


def test_resolve_absolute_import(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mymodule.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mymodule", names=[], is_relative=False, level=0)
    result = resolve_import(imp, "main.py", index)
    assert result is not None
    assert "mymodule.py" in result


def test_resolve_absolute_import_skip_stdlib():
    from scripts.context.phases.imports import resolve_import
    imp = ImportInfo(module="os", names=[], is_relative=False, level=0)
    result = resolve_import(imp, "main.py", {})
    assert result is None


def test_resolve_absolute_import_skip_unresolvable():
    from scripts.context.phases.imports import resolve_import
    imp = ImportInfo(module="requests", names=["get"], is_relative=False, level=0)
    result = resolve_import(imp, "main.py", {})
    assert result is None


# --- resolve_import: from-imports ---


def test_resolve_from_import(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mypackage/__init__.py")
    _add_file_node(storage, "mypackage/foo.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mypackage.foo", names=["bar"], is_relative=False, level=0)
    result = resolve_import(imp, "main.py", index)
    assert result is not None
    assert "mypackage/foo.py" in result


def test_resolve_from_import_to_package(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mypackage/__init__.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mypackage", names=["something"], is_relative=False, level=0)
    result = resolve_import(imp, "main.py", index)
    assert result is not None


# --- resolve_import: relative imports ---


def test_resolve_relative_import_dot(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "pkg/__init__.py")
    _add_file_node(storage, "pkg/sibling.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="", names=["sibling"], is_relative=True, level=1)
    result = resolve_import(imp, "pkg/child.py", index)
    assert result is not None
    assert "pkg/sibling.py" in result or "pkg" in result


def test_resolve_relative_import_double_dot(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    # from ..utils import helper in pkg/sub/mod.py → parent package is pkg → pkg.utils
    _add_file_node(storage, "pkg/__init__.py")
    _add_file_node(storage, "pkg/utils.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="utils", names=["helper"], is_relative=True, level=2)
    result = resolve_import(imp, "pkg/sub/mod.py", index)
    assert result is not None
    assert "pkg/utils.py" in result


# --- process_imports ---


def test_process_imports_creates_edges(storage):
    from scripts.context.phases.imports import process_imports
    from scripts.context.python_parser import ParseResult

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "utils.py")

    parse_results = {
        "main.py": ParseResult(
            file_path="main.py",
            imports=[ImportInfo(module="utils", names=["helper"], is_relative=False, level=0)],
        ),
    }
    process_imports(parse_results, storage)

    # Verify IMPORTS relationship exists by checking storage directly
    assert storage._conn is not None
    cur = storage._conn.execute(
        "SELECT * FROM relationships WHERE type = ?", (RelType.IMPORTS.value,)
    )
    rows = cur.fetchall()
    assert len(rows) >= 1


def test_process_imports_skips_stdlib(storage):
    from scripts.context.phases.imports import process_imports
    from scripts.context.python_parser import ParseResult

    _add_file_node(storage, "main.py")

    parse_results = {
        "main.py": ParseResult(
            file_path="main.py",
            imports=[ImportInfo(module="os", names=["path"], is_relative=False, level=0)],
        ),
    }
    process_imports(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT * FROM relationships WHERE type = ?", (RelType.IMPORTS.value,)
    )
    rows = cur.fetchall()
    assert len(rows) == 0


def test_process_imports_stores_symbols_property(storage):
    from scripts.context.phases.imports import process_imports
    from scripts.context.python_parser import ParseResult
    import json

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "utils.py")

    parse_results = {
        "main.py": ParseResult(
            file_path="main.py",
            imports=[ImportInfo(module="utils", names=["helper", "parse"], is_relative=False, level=0)],
        ),
    }
    process_imports(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT properties_json FROM relationships WHERE type = ?",
        (RelType.IMPORTS.value,)
    )
    row = cur.fetchone()
    assert row is not None
    props = json.loads(row[0])
    assert set(props["symbols"]) == {"helper", "parse"}
