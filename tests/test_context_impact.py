"""Tests for impact analysis phase (BFS blast radius)."""

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
from scripts.context.phases.impact import ImpactResult, impact_analysis
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


def _add_file_with_symbols(storage, file_path, symbols):
    """Helper: add a FILE node and symbol nodes with DEFINES edges."""
    file_id = generate_id(NodeLabel.FILE, file_path, "")
    nodes = [
        GraphNode(id=file_id, label=NodeLabel.FILE, name=file_path, file_path=file_path)
    ]
    rels = []
    for name, label in symbols:
        sym_id = generate_id(label, file_path, name)
        nodes.append(GraphNode(
            id=sym_id, label=label, name=name, file_path=file_path,
        ))
        rels.append(GraphRelationship(
            id=f"defines:{file_id}->{sym_id}",
            type=RelType.DEFINES,
            source=file_id,
            target=sym_id,
        ))
    storage.add_nodes(nodes)
    if rels:
        storage.add_relationships(rels)
    return file_id


class TestImpactAnalysisDirectCallers:
    """Impact from direct CALLS edges."""

    def test_single_caller(self, storage):
        """A function called by one other function shows up at depth 1."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
        storage.add_relationships([GraphRelationship(
            id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
            properties={"confidence": 1.0},
        )])

        results = impact_analysis(storage, "a.py")
        assert len(results) >= 1
        names = {r.node.name for r in results}
        assert "bar" in names
        assert all(r.depth == 1 for r in results if r.node.name == "bar")

    def test_multiple_callers(self, storage):
        """Multiple direct callers of symbols in target file."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "c.py", [("baz", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
        baz_id = generate_id(NodeLabel.FUNCTION, "c.py", "baz")

        storage.add_relationships([
            GraphRelationship(
                id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
            ),
            GraphRelationship(
                id="calls:baz->foo", type=RelType.CALLS, source=baz_id, target=foo_id,
            ),
        ])

        results = impact_analysis(storage, "a.py")
        names = {r.node.name for r in results}
        assert "bar" in names
        assert "baz" in names

    def test_no_callers(self, storage):
        """File with no callers returns empty results."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        results = impact_analysis(storage, "a.py")
        assert results == []


class TestImpactAnalysisTransitive:
    """Impact via transitive (multi-hop) BFS."""

    def test_two_hop_transitive(self, storage):
        """A → B → C: changing A impacts B (depth 1) and C (depth 2)."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "c.py", [("baz", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
        baz_id = generate_id(NodeLabel.FUNCTION, "c.py", "baz")

        storage.add_relationships([
            GraphRelationship(
                id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
            ),
            GraphRelationship(
                id="calls:baz->bar", type=RelType.CALLS, source=baz_id, target=bar_id,
            ),
        ])

        results = impact_analysis(storage, "a.py")
        by_name = {r.node.name: r for r in results}
        assert "bar" in by_name
        assert by_name["bar"].depth == 1
        assert "baz" in by_name
        assert by_name["baz"].depth == 2

    def test_impact_via_imports(self, storage):
        """File importing target file shows up in blast radius."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        file_b = _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])
        file_a = generate_id(NodeLabel.FILE, "a.py", "")

        storage.add_relationships([GraphRelationship(
            id="imports:b->a", type=RelType.IMPORTS, source=file_b, target=file_a,
            properties={"symbols": ["foo"]},
        )])

        results = impact_analysis(storage, "a.py")
        node_ids = {r.node.id for r in results}
        assert file_b in node_ids

    def test_impact_via_extends(self, storage):
        """Class extending a class in target file shows up."""
        _add_file_with_symbols(storage, "a.py", [("Base", NodeLabel.CLASS)])
        _add_file_with_symbols(storage, "b.py", [("Child", NodeLabel.CLASS)])

        base_id = generate_id(NodeLabel.CLASS, "a.py", "Base")
        child_id = generate_id(NodeLabel.CLASS, "b.py", "Child")

        storage.add_relationships([GraphRelationship(
            id="extends:child->base", type=RelType.EXTENDS, source=child_id, target=base_id,
        )])

        results = impact_analysis(storage, "a.py")
        names = {r.node.name for r in results}
        assert "Child" in names


class TestImpactAnalysisDepthLimit:
    """max_depth parameter controls BFS traversal depth."""

    def test_depth_limit_excludes_far_nodes(self, storage):
        """With max_depth=1, only direct callers are returned."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "c.py", [("baz", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
        baz_id = generate_id(NodeLabel.FUNCTION, "c.py", "baz")

        storage.add_relationships([
            GraphRelationship(
                id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
            ),
            GraphRelationship(
                id="calls:baz->bar", type=RelType.CALLS, source=baz_id, target=bar_id,
            ),
        ])

        results = impact_analysis(storage, "a.py", max_depth=1)
        names = {r.node.name for r in results}
        assert "bar" in names
        assert "baz" not in names

    def test_depth_zero_returns_empty(self, storage):
        """max_depth=0 returns no impacted nodes."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")
        storage.add_relationships([GraphRelationship(
            id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
        )])

        results = impact_analysis(storage, "a.py", max_depth=0)
        assert results == []


class TestImpactAnalysisCycles:
    """Cycle handling in BFS."""

    def test_cycle_does_not_loop(self, storage):
        """A → B → A cycle terminates without infinite loop."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("bar", NodeLabel.FUNCTION)])

        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")
        bar_id = generate_id(NodeLabel.FUNCTION, "b.py", "bar")

        storage.add_relationships([
            GraphRelationship(
                id="calls:bar->foo", type=RelType.CALLS, source=bar_id, target=foo_id,
            ),
            GraphRelationship(
                id="calls:foo->bar", type=RelType.CALLS, source=foo_id, target=bar_id,
            ),
        ])

        results = impact_analysis(storage, "a.py")
        # Should terminate and include bar at depth 1
        names = {r.node.name for r in results}
        assert "bar" in names

    def test_self_referencing(self, storage):
        """A function calling itself doesn't cause issues."""
        _add_file_with_symbols(storage, "a.py", [("foo", NodeLabel.FUNCTION)])
        foo_id = generate_id(NodeLabel.FUNCTION, "a.py", "foo")

        storage.add_relationships([GraphRelationship(
            id="calls:foo->foo", type=RelType.CALLS, source=foo_id, target=foo_id,
        )])

        results = impact_analysis(storage, "a.py")
        # Should not include the file's own symbols
        assert results == []


class TestImpactResultSorting:
    """Results are sorted by depth then name."""

    def test_sorted_by_depth_then_name(self, storage):
        """Results come back sorted: depth ascending, then name ascending."""
        _add_file_with_symbols(storage, "a.py", [("target", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "b.py", [("zebra", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "c.py", [("alpha", NodeLabel.FUNCTION)])
        _add_file_with_symbols(storage, "d.py", [("deep", NodeLabel.FUNCTION)])

        target_id = generate_id(NodeLabel.FUNCTION, "a.py", "target")
        zebra_id = generate_id(NodeLabel.FUNCTION, "b.py", "zebra")
        alpha_id = generate_id(NodeLabel.FUNCTION, "c.py", "alpha")
        deep_id = generate_id(NodeLabel.FUNCTION, "d.py", "deep")

        storage.add_relationships([
            GraphRelationship(
                id="calls:zebra->target", type=RelType.CALLS, source=zebra_id, target=target_id,
            ),
            GraphRelationship(
                id="calls:alpha->target", type=RelType.CALLS, source=alpha_id, target=target_id,
            ),
            GraphRelationship(
                id="calls:deep->alpha", type=RelType.CALLS, source=deep_id, target=alpha_id,
            ),
        ])

        results = impact_analysis(storage, "a.py")
        names = [r.node.name for r in results]
        # Depth 1: alpha, zebra (sorted by name). Depth 2: deep
        assert names == ["alpha", "zebra", "deep"]


class TestImpactAnalysisEdgeCases:
    """Edge cases."""

    def test_nonexistent_file(self, storage):
        """File not in the graph returns empty results."""
        results = impact_analysis(storage, "nonexistent.py")
        assert results == []

    def test_file_no_symbols(self, storage):
        """File with no symbols (just a FILE node) returns empty."""
        _add_file_with_symbols(storage, "empty.py", [])
        results = impact_analysis(storage, "empty.py")
        assert results == []
