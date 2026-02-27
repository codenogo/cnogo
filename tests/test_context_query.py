"""Tests for ContextGraph.context() — node neighborhood queries."""

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


def _add_node(storage, label, file_path, name, **kwargs):
    """Helper: add a single node."""
    node_id = generate_id(label, file_path, name)
    node = GraphNode(id=node_id, label=label, name=name, file_path=file_path, **kwargs)
    storage.add_nodes([node])
    return node_id


class TestGetRelatedNodes:
    """Tests for GraphStorage.get_related_nodes()."""

    def test_outgoing(self, storage):
        """Get nodes connected via outgoing edges."""
        a_id = _add_node(storage, NodeLabel.FUNCTION, "a.py", "foo")
        b_id = _add_node(storage, NodeLabel.FUNCTION, "b.py", "bar")
        storage.add_relationships([GraphRelationship(
            id="calls:a->b", type=RelType.CALLS, source=a_id, target=b_id,
        )])

        results = storage.get_related_nodes(a_id, RelType.CALLS, direction="outgoing")
        assert len(results) == 1
        assert results[0].id == b_id

    def test_incoming(self, storage):
        """Get nodes connected via incoming edges."""
        a_id = _add_node(storage, NodeLabel.FUNCTION, "a.py", "foo")
        b_id = _add_node(storage, NodeLabel.FUNCTION, "b.py", "bar")
        storage.add_relationships([GraphRelationship(
            id="calls:b->a", type=RelType.CALLS, source=b_id, target=a_id,
        )])

        results = storage.get_related_nodes(a_id, RelType.CALLS, direction="incoming")
        assert len(results) == 1
        assert results[0].id == b_id

    def test_no_results(self, storage):
        """Returns empty list when no edges match."""
        a_id = _add_node(storage, NodeLabel.FUNCTION, "a.py", "foo")
        results = storage.get_related_nodes(a_id, RelType.CALLS, direction="outgoing")
        assert results == []

    def test_multiple_results(self, storage):
        """Returns all matching nodes."""
        a_id = _add_node(storage, NodeLabel.FUNCTION, "a.py", "foo")
        b_id = _add_node(storage, NodeLabel.FUNCTION, "b.py", "bar")
        c_id = _add_node(storage, NodeLabel.FUNCTION, "c.py", "baz")
        storage.add_relationships([
            GraphRelationship(id="calls:a->b", type=RelType.CALLS, source=a_id, target=b_id),
            GraphRelationship(id="calls:a->c", type=RelType.CALLS, source=a_id, target=c_id),
        ])

        results = storage.get_related_nodes(a_id, RelType.CALLS, direction="outgoing")
        assert len(results) == 2
        ids = {r.id for r in results}
        assert b_id in ids
        assert c_id in ids


class TestContextMethod:
    """Tests for ContextGraph.context() via storage-level setup."""

    def test_callers_and_callees(self, storage):
        """context() returns callers and callees."""
        from scripts.context import ContextGraph

        with tempfile.TemporaryDirectory() as tmp:
            graph = ContextGraph(repo_path=tmp)
            s = graph._storage

            a_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
            b_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
            c_id = generate_id(NodeLabel.FUNCTION, "c.py", "baz")

            s.add_nodes([
                GraphNode(id=a_id, label=NodeLabel.FUNCTION, name="foo", file_path="a.py"),
                GraphNode(id=b_id, label=NodeLabel.FUNCTION, name="bar", file_path="b.py"),
                GraphNode(id=c_id, label=NodeLabel.FUNCTION, name="baz", file_path="c.py"),
            ])
            s.add_relationships([
                GraphRelationship(id="calls:b->a", type=RelType.CALLS, source=b_id, target=a_id),
                GraphRelationship(id="calls:a->c", type=RelType.CALLS, source=a_id, target=c_id),
            ])

            ctx = graph.context(a_id)
            assert ctx["node"].id == a_id
            assert len(ctx["callers"]) == 1
            assert ctx["callers"][0].id == b_id
            assert len(ctx["callees"]) == 1
            assert ctx["callees"][0].id == c_id
            graph.close()

    def test_parent_and_child_classes(self, storage):
        """context() returns parent and child classes."""
        from scripts.context import ContextGraph

        with tempfile.TemporaryDirectory() as tmp:
            graph = ContextGraph(repo_path=tmp)
            s = graph._storage

            base_id = generate_id(NodeLabel.CLASS, "a.py", "Base")
            mid_id = generate_id(NodeLabel.CLASS, "b.py", "Mid")
            child_id = generate_id(NodeLabel.CLASS, "c.py", "Child")

            s.add_nodes([
                GraphNode(id=base_id, label=NodeLabel.CLASS, name="Base", file_path="a.py"),
                GraphNode(id=mid_id, label=NodeLabel.CLASS, name="Mid", file_path="b.py"),
                GraphNode(id=child_id, label=NodeLabel.CLASS, name="Child", file_path="c.py"),
            ])
            s.add_relationships([
                GraphRelationship(id="extends:mid->base", type=RelType.EXTENDS, source=mid_id, target=base_id),
                GraphRelationship(id="extends:child->mid", type=RelType.EXTENDS, source=child_id, target=mid_id),
            ])

            ctx = graph.context(mid_id)
            assert len(ctx["parent_classes"]) == 1
            assert ctx["parent_classes"][0].id == base_id
            assert len(ctx["child_classes"]) == 1
            assert ctx["child_classes"][0].id == child_id
            graph.close()

    def test_importers_and_imports(self, storage):
        """context() returns importers and imported files."""
        from scripts.context import ContextGraph

        with tempfile.TemporaryDirectory() as tmp:
            graph = ContextGraph(repo_path=tmp)
            s = graph._storage

            a_id = generate_id(NodeLabel.FILE, "a.py", "")
            b_id = generate_id(NodeLabel.FILE, "b.py", "")

            s.add_nodes([
                GraphNode(id=a_id, label=NodeLabel.FILE, name="a.py", file_path="a.py"),
                GraphNode(id=b_id, label=NodeLabel.FILE, name="b.py", file_path="b.py"),
            ])
            s.add_relationships([
                GraphRelationship(
                    id="imports:a->b", type=RelType.IMPORTS, source=a_id, target=b_id,
                    properties={"symbols": ["foo"]},
                ),
            ])

            ctx = graph.context(a_id)
            assert len(ctx["imports"]) == 1
            assert ctx["imports"][0].id == b_id

            ctx_b = graph.context(b_id)
            assert len(ctx_b["importers"]) == 1
            assert ctx_b["importers"][0].id == a_id
            graph.close()

    def test_nonexistent_node_raises(self, storage):
        """context() raises ValueError for unknown node ID."""
        from scripts.context import ContextGraph

        with tempfile.TemporaryDirectory() as tmp:
            graph = ContextGraph(repo_path=tmp)
            with pytest.raises(ValueError, match="not found"):
                graph.context("nonexistent:id")
            graph.close()

    def test_empty_neighborhood(self, storage):
        """context() returns empty lists for isolated node."""
        from scripts.context import ContextGraph

        with tempfile.TemporaryDirectory() as tmp:
            graph = ContextGraph(repo_path=tmp)
            s = graph._storage

            a_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
            s.add_nodes([GraphNode(
                id=a_id, label=NodeLabel.FUNCTION, name="foo", file_path="a.py",
            )])

            ctx = graph.context(a_id)
            assert ctx["node"].id == a_id
            assert ctx["callers"] == []
            assert ctx["callees"] == []
            assert ctx["importers"] == []
            assert ctx["imports"] == []
            assert ctx["parent_classes"] == []
            assert ctx["child_classes"] == []
            graph.close()
