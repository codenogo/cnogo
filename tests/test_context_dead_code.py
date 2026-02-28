"""Tests for dead code detection phase."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.phases.dead_code import DeadCodeResult, detect_dead_code
from scripts.context.storage import GraphStorage


@pytest.fixture
def storage():
    """Create an in-memory graph storage for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        s = GraphStorage(db_path)
        s.initialize()
        yield s
        s.close()


def _add_function(storage, file_path, name, label=NodeLabel.FUNCTION):
    """Helper: add a symbol node."""
    node_id = generate_id(label, file_path, name)
    node = GraphNode(
        id=node_id,
        label=label,
        name=name,
        file_path=file_path,
        start_line=1,
    )
    storage.add_nodes([node])
    return node_id


def _add_call_edge(storage, caller_id, callee_id):
    """Helper: add a CALLS edge from caller to callee."""
    storage.add_relationships([
        GraphRelationship(
            id=f"calls:{caller_id}->{callee_id}",
            type=RelType.CALLS,
            source=caller_id,
            target=callee_id,
        )
    ])


class TestGetAllSymbolNodes:
    """get_all_symbol_nodes returns only FUNCTION/CLASS/METHOD/ENUM nodes."""

    def test_returns_function_nodes(self, storage):
        _add_function(storage, "a.py", "foo", NodeLabel.FUNCTION)
        nodes = storage.get_all_symbol_nodes()
        assert any(n.name == "foo" for n in nodes)

    def test_returns_class_nodes(self, storage):
        _add_function(storage, "a.py", "MyClass", NodeLabel.CLASS)
        nodes = storage.get_all_symbol_nodes()
        assert any(n.name == "MyClass" for n in nodes)

    def test_returns_method_nodes(self, storage):
        _add_function(storage, "a.py", "my_method", NodeLabel.METHOD)
        nodes = storage.get_all_symbol_nodes()
        assert any(n.name == "my_method" for n in nodes)

    def test_returns_enum_nodes(self, storage):
        _add_function(storage, "a.py", "Color", NodeLabel.ENUM)
        nodes = storage.get_all_symbol_nodes()
        assert any(n.name == "Color" for n in nodes)

    def test_excludes_file_nodes(self, storage):
        file_id = generate_id(NodeLabel.FILE, "a.py", "")
        storage.add_nodes([GraphNode(
            id=file_id, label=NodeLabel.FILE, name="a.py", file_path="a.py"
        )])
        nodes = storage.get_all_symbol_nodes()
        assert all(n.label != NodeLabel.FILE for n in nodes)

    def test_excludes_folder_nodes(self, storage):
        folder_id = generate_id(NodeLabel.FOLDER, "src/", "")
        storage.add_nodes([GraphNode(
            id=folder_id, label=NodeLabel.FOLDER, name="src/", file_path="src/"
        )])
        nodes = storage.get_all_symbol_nodes()
        assert all(n.label != NodeLabel.FOLDER for n in nodes)


class TestMarkDeadNodes:
    """mark_dead_nodes bulk-updates is_dead=1 for the given IDs."""

    def test_marks_single_node_dead(self, storage):
        node_id = _add_function(storage, "a.py", "foo")
        storage.mark_dead_nodes([node_id])
        node = storage.get_node(node_id)
        assert node is not None
        assert node.is_dead is True

    def test_marks_multiple_nodes_dead(self, storage):
        id1 = _add_function(storage, "a.py", "foo")
        id2 = _add_function(storage, "a.py", "bar")
        storage.mark_dead_nodes([id1, id2])
        assert storage.get_node(id1).is_dead is True
        assert storage.get_node(id2).is_dead is True

    def test_does_not_mark_other_nodes_dead(self, storage):
        id1 = _add_function(storage, "a.py", "dead_fn")
        id2 = _add_function(storage, "a.py", "live_fn")
        storage.mark_dead_nodes([id1])
        assert storage.get_node(id2).is_dead is False

    def test_empty_list_is_safe(self, storage):
        _add_function(storage, "a.py", "foo")
        # Should not raise
        storage.mark_dead_nodes([])

    def test_get_dead_nodes_returns_marked(self, storage):
        id1 = _add_function(storage, "a.py", "dead_fn")
        _add_function(storage, "a.py", "live_fn")
        storage.mark_dead_nodes([id1])
        dead = storage.get_dead_nodes()
        assert len(dead) == 1
        assert dead[0].name == "dead_fn"


class TestDetectDeadCode:
    """detect_dead_code identifies unreferenced non-entry-point symbols."""

    def test_unreferenced_function_is_dead(self, storage):
        _add_function(storage, "a.py", "orphan")
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "orphan" in names

    def test_called_function_is_not_dead(self, storage):
        callee_id = _add_function(storage, "a.py", "helper")
        caller_id = _add_function(storage, "b.py", "main_caller")
        _add_call_edge(storage, caller_id, callee_id)
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "helper" not in names

    def test_result_is_dead_code_result_instances(self, storage):
        _add_function(storage, "a.py", "orphan")
        results = detect_dead_code(storage)
        assert all(isinstance(r, DeadCodeResult) for r in results)

    def test_dead_code_result_has_expected_fields(self, storage):
        node_id = _add_function(storage, "a.py", "orphan")
        results = detect_dead_code(storage)
        r = next(r for r in results if r.name == "orphan")
        assert r.node_id == node_id
        assert r.label == NodeLabel.FUNCTION
        assert r.file_path == "a.py"
        assert r.line == 1


class TestEntryPoints:
    """Entry point heuristics prevent false positives."""

    def test_main_function_is_not_dead(self, storage):
        _add_function(storage, "app.py", "main")
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "main" not in names

    def test_test_prefix_function_is_not_dead(self, storage):
        _add_function(storage, "test_app.py", "test_my_feature")
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "test_my_feature" not in names

    def test_init_file_symbol_is_not_dead(self, storage):
        _add_function(storage, "mypackage/__init__.py", "public_api")
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "public_api" not in names

    def test_non_test_function_without_callers_is_dead(self, storage):
        _add_function(storage, "utils.py", "helper_fn")
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "helper_fn" in names

    def test_test_prefix_class_is_not_dead(self, storage):
        _add_function(storage, "test_things.py", "TestMyClass", NodeLabel.CLASS)
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "TestMyClass" not in names


class TestEdgeTypesCoverage:
    """Incoming IMPORTS, EXTENDS, IMPLEMENTS edges prevent dead classification."""

    def test_class_with_extends_is_not_dead(self, storage):
        base_id = _add_function(storage, "base.py", "Base", NodeLabel.CLASS)
        child_id = _add_function(storage, "child.py", "Child", NodeLabel.CLASS)
        storage.add_relationships([GraphRelationship(
            id=f"extends:{child_id}->{base_id}",
            type=RelType.EXTENDS,
            source=child_id,
            target=base_id,
        )])
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "Base" not in names

    def test_class_with_implements_is_not_dead(self, storage):
        iface_id = _add_function(storage, "proto.py", "Protocol", NodeLabel.CLASS)
        impl_id = _add_function(storage, "impl.py", "ConcreteImpl", NodeLabel.CLASS)
        storage.add_relationships([GraphRelationship(
            id=f"implements:{impl_id}->{iface_id}",
            type=RelType.IMPLEMENTS,
            source=impl_id,
            target=iface_id,
        )])
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "Protocol" not in names

    def test_symbol_with_imports_edge_is_not_dead(self, storage):
        exported_id = _add_function(storage, "lib.py", "helper")
        importer_id = _add_function(storage, "app.py", "app_func")
        storage.add_relationships([GraphRelationship(
            id=f"imports:{importer_id}->{exported_id}",
            type=RelType.IMPORTS,
            source=importer_id,
            target=exported_id,
        )])
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "helper" not in names

    def test_method_called_via_calls_is_not_dead(self, storage):
        method_id = _add_function(storage, "obj.py", "do_work", NodeLabel.METHOD)
        caller_id = _add_function(storage, "runner.py", "run")
        _add_call_edge(storage, caller_id, method_id)
        results = detect_dead_code(storage)
        names = {r.name for r in results}
        assert "do_work" not in names


class TestMarkDeadNodesIntegration:
    """detect_dead_code marks nodes in storage after detection."""

    def test_dead_nodes_are_marked_in_storage(self, storage):
        node_id = _add_function(storage, "a.py", "orphan")
        detect_dead_code(storage)
        node = storage.get_node(node_id)
        assert node is not None
        assert node.is_dead is True

    def test_live_nodes_are_not_marked_dead(self, storage):
        callee_id = _add_function(storage, "a.py", "helper")
        caller_id = _add_function(storage, "b.py", "main_fn")
        _add_call_edge(storage, caller_id, callee_id)
        detect_dead_code(storage)
        node = storage.get_node(callee_id)
        assert node is not None
        assert node.is_dead is False

    def test_empty_graph_returns_empty(self, storage):
        results = detect_dead_code(storage)
        assert results == []
