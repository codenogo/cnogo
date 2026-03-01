"""Tests for imports phase.

Tests the build_file_index, resolve_import, and process_imports functions.
"""

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
from scripts.context.parser_base import ImportInfo, ParseResult, SymbolInfo


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


def _add_function_node(storage, file_path, func_name):
    """Helper to add a FUNCTION node to storage."""
    node_id = generate_id(NodeLabel.FUNCTION, file_path, func_name)
    storage.add_nodes([GraphNode(
        id=node_id,
        label=NodeLabel.FUNCTION,
        name=func_name,
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


def test_build_file_index_slash_notation(storage):
    from scripts.context.phases.imports import build_file_index
    _add_file_node(storage, "src/utils.py")

    index = build_file_index(storage)
    # Both slash and dot notation should be present
    assert "src/utils" in index or "src.utils" in index


# --- resolve_import ---


def test_resolve_absolute_import(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mymodule.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mymodule", names=[])
    result = resolve_import(imp, "main.py", index)
    assert result is not None
    assert "mymodule.py" in result


def test_resolve_absolute_import_skip_unresolvable():
    from scripts.context.phases.imports import resolve_import
    imp = ImportInfo(module="requests", names=["get"])
    result = resolve_import(imp, "main.py", {})
    assert result is None


def test_resolve_absolute_import_empty_index():
    from scripts.context.phases.imports import resolve_import
    imp = ImportInfo(module="os", names=[])
    result = resolve_import(imp, "main.py", {})
    assert result is None


def test_resolve_from_import(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mypackage/__init__.py")
    _add_file_node(storage, "mypackage/foo.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mypackage.foo", names=["bar"])
    result = resolve_import(imp, "main.py", index)
    assert result is not None
    assert "mypackage/foo.py" in result


def test_resolve_from_import_to_package(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "mypackage/__init__.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="mypackage", names=["something"])
    result = resolve_import(imp, "main.py", index)
    assert result is not None


def test_resolve_relative_dot_import(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "pkg/__init__.py")
    _add_file_node(storage, "pkg/sibling.py")
    index = build_file_index(storage)

    # from . import sibling (relative import, module="", names=["sibling"])
    # level=1 means single dot — relative to current package
    imp = ImportInfo(module="sibling", names=[], alias="")
    # Simulate as if the module is in the same package directory
    # For simple resolution: "sibling" resolves relative to "pkg/"
    result = resolve_import(imp, "pkg/child.py", index)
    # Should find pkg/sibling.py through index
    assert result is not None


def test_resolve_python_dotted_module(storage):
    from scripts.context.phases.imports import build_file_index, resolve_import
    _add_file_node(storage, "src/utils.py")
    index = build_file_index(storage)

    imp = ImportInfo(module="src.utils", names=["helper"])
    result = resolve_import(imp, "main.py", index)
    assert result is not None
    assert "src/utils.py" in result


# --- process_imports ---


def test_imports_creates_file_to_file_relationship(storage):
    """File A imports module B -> IMPORTS rel from file A to file B."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "utils.py")

    parse_results = {
        "main.py": ParseResult(
            imports=[ImportInfo(module="utils", names=[])],
        ),
    }
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    assert len(imported) >= 1
    imported_paths = [n.file_path for n in imported]
    assert "utils.py" in imported_paths


def test_imports_python_dotted_module(storage):
    """from src.utils import helper resolves to src/utils.py."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "src/utils.py")

    parse_results = {
        "main.py": ParseResult(
            imports=[ImportInfo(module="src.utils", names=["helper"])],
        ),
    }
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    assert len(imported) >= 1
    imported_paths = [n.file_path for n in imported]
    assert "src/utils.py" in imported_paths


def test_imports_no_target_found_creates_no_relationship(storage):
    """Unresolvable import creates no relationship (no crash)."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")

    parse_results = {
        "main.py": ParseResult(
            imports=[ImportInfo(module="nonexistent_package", names=[])],
        ),
    }
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    assert len(imported) == 0


def test_imports_empty_parse_results(storage):
    """No imports -> no relationships."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")

    parse_results: dict = {}
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    assert len(imported) == 0


def test_imports_init_package(storage):
    """import src.pkg resolves to src/pkg/__init__.py."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")
    _add_file_node(storage, "src/pkg/__init__.py")

    parse_results = {
        "main.py": ParseResult(
            imports=[ImportInfo(module="src.pkg", names=[])],
        ),
    }
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    assert len(imported) >= 1


def test_imports_multiple_files(storage):
    """Multiple files with imports all get IMPORTS relationships."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "a.py")
    _add_file_node(storage, "b.py")
    _add_file_node(storage, "c.py")

    parse_results = {
        "a.py": ParseResult(imports=[ImportInfo(module="b", names=[])]),
        "b.py": ParseResult(imports=[ImportInfo(module="c", names=[])]),
    }
    process_imports(parse_results, storage)

    a_id = generate_id(NodeLabel.FILE, "a.py", "")
    b_id = generate_id(NodeLabel.FILE, "b.py", "")
    assert len(storage.get_related_nodes(a_id, RelType.IMPORTS, "outgoing")) >= 1
    assert len(storage.get_related_nodes(b_id, RelType.IMPORTS, "outgoing")) >= 1


def test_imports_no_self_import(storage):
    """A file should not create an IMPORTS relationship to itself."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "utils.py")

    parse_results = {
        "utils.py": ParseResult(
            imports=[ImportInfo(module="utils", names=[])],
        ),
    }
    process_imports(parse_results, storage)

    utils_id = generate_id(NodeLabel.FILE, "utils.py", "")
    imported = storage.get_related_nodes(utils_id, RelType.IMPORTS, "outgoing")
    # Should not import itself
    self_imports = [n for n in imported if n.file_path == "utils.py"]
    assert len(self_imports) == 0


def test_imports_no_crash_on_empty_module_name(storage):
    """Empty module name should not crash."""
    from scripts.context.phases.imports import process_imports

    _add_file_node(storage, "main.py")

    parse_results = {
        "main.py": ParseResult(
            imports=[ImportInfo(module="", names=["something"])],
        ),
    }
    # Should not raise
    process_imports(parse_results, storage)

    main_id = generate_id(NodeLabel.FILE, "main.py", "")
    imported = storage.get_related_nodes(main_id, RelType.IMPORTS, "outgoing")
    # No relationship created for empty module
    assert len(imported) == 0
