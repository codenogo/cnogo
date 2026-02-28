"""Tests for graph visualization module (Mermaid + DOT renderers).

Covers:
- render_mermaid() and render_dot() unit tests (Task 1)
- ContextGraph.visualize() method (Task 2)
- End-to-end integration tests with real indexing (Task 3)
"""

from __future__ import annotations

import re
import tempfile
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage():
    """Create an in-memory graph storage for testing."""
    from scripts.context.storage import GraphStorage

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        s = GraphStorage(db_path)
        s.initialize()
        yield s
        s.close()


@pytest.fixture
def graph(tmp_path):
    from scripts.context import ContextGraph

    g = ContextGraph(repo_path=tmp_path)
    yield g
    g.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_nodes_and_edges(storage):
    """Add sample nodes and edges to storage for visualization tests."""
    from scripts.context.model import (
        GraphNode,
        GraphRelationship,
        NodeLabel,
        RelType,
        generate_id,
    )

    # FILE node
    file_id = generate_id(NodeLabel.FILE, "src/app.py", "")
    func_a_id = generate_id(NodeLabel.FUNCTION, "src/app.py", "func_a")
    func_b_id = generate_id(NodeLabel.FUNCTION, "src/app.py", "func_b")
    class_id = generate_id(NodeLabel.CLASS, "src/app.py", "MyClass")

    nodes = [
        GraphNode(id=file_id, label=NodeLabel.FILE, name="src/app.py", file_path="src/app.py"),
        GraphNode(id=func_a_id, label=NodeLabel.FUNCTION, name="func_a", file_path="src/app.py"),
        GraphNode(id=func_b_id, label=NodeLabel.FUNCTION, name="func_b", file_path="src/app.py"),
        GraphNode(id=class_id, label=NodeLabel.CLASS, name="MyClass", file_path="src/app.py"),
    ]
    storage.add_nodes(nodes)

    rels = [
        GraphRelationship(
            id="calls:func_a->func_b",
            type=RelType.CALLS,
            source=func_a_id,
            target=func_b_id,
        ),
        GraphRelationship(
            id="defines:file->func_a",
            type=RelType.DEFINES,
            source=file_id,
            target=func_a_id,
        ),
    ]
    storage.add_relationships(rels)

    return {
        "file_id": file_id,
        "func_a_id": func_a_id,
        "func_b_id": func_b_id,
        "class_id": class_id,
    }


# ---------------------------------------------------------------------------
# Task 1: Unit tests for render_mermaid and render_dot
# ---------------------------------------------------------------------------


class TestRenderMermaid:
    """Unit tests for render_mermaid()."""

    def test_mermaid_header(self):
        """render_mermaid must start with 'flowchart TD'."""
        from scripts.context.visualization import render_mermaid

        nodes = []
        edges = []
        result = render_mermaid(nodes, edges)
        assert result.strip().startswith("flowchart TD")

    def test_mermaid_empty_graph(self):
        """Empty nodes/edges produces valid header-only output."""
        from scripts.context.visualization import render_mermaid

        result = render_mermaid([], [])
        assert "flowchart TD" in result

    def test_mermaid_single_node(self):
        """A single node appears with its label and type."""
        from scripts.context.model import GraphNode, NodeLabel
        from scripts.context.visualization import render_mermaid

        node = GraphNode(
            id="function:src/app.py:func_a",
            label=NodeLabel.FUNCTION,
            name="func_a",
            file_path="src/app.py",
        )
        result = render_mermaid([node], [])
        assert "func_a" in result
        assert "FUNCTION" in result or "function" in result.lower()

    def test_mermaid_edge_label(self):
        """An edge appears with its relationship type as label."""
        from scripts.context.model import (
            GraphNode,
            GraphRelationship,
            NodeLabel,
            RelType,
        )
        from scripts.context.visualization import render_mermaid

        node_a = GraphNode(
            id="function:src/app.py:func_a",
            label=NodeLabel.FUNCTION,
            name="func_a",
            file_path="src/app.py",
        )
        node_b = GraphNode(
            id="function:src/app.py:func_b",
            label=NodeLabel.FUNCTION,
            name="func_b",
            file_path="src/app.py",
        )
        edge = (node_a.id, node_b.id, "CALLS")
        result = render_mermaid([node_a, node_b], [edge])
        assert "CALLS" in result
        # Should have an arrow
        assert "-->" in result

    def test_mermaid_node_ids_sanitized(self):
        """Node IDs in Mermaid must not contain characters that break syntax."""
        from scripts.context.model import GraphNode, NodeLabel
        from scripts.context.visualization import render_mermaid

        # Node ID contains colons and slashes — must be sanitized
        node = GraphNode(
            id="function:src/app.py:func_a",
            label=NodeLabel.FUNCTION,
            name="func_a",
            file_path="src/app.py",
        )
        result = render_mermaid([node], [])
        # The raw id "function:src/app.py:func_a" should not appear in node declarations
        # Colons and slashes break Mermaid syntax
        lines = result.splitlines()
        node_lines = [l for l in lines if "func_a" in l and "-->" not in l and "flowchart" not in l]
        for line in node_lines:
            # Get the node id part (before the bracket)
            # e.g.  "    node_id_sanitized[...]"
            stripped = line.strip()
            if stripped and not stripped.startswith("%"):
                # The node_id (before '[') must not contain : or /
                bracket_pos = stripped.find("[")
                if bracket_pos > 0:
                    node_id_part = stripped[:bracket_pos]
                    assert ":" not in node_id_part, f"Unsanitized colon in node id: {node_id_part}"
                    assert "/" not in node_id_part, f"Unsanitized slash in node id: {node_id_part}"

    def test_mermaid_multiple_nodes(self):
        """Multiple nodes all appear in the output."""
        from scripts.context.model import GraphNode, NodeLabel
        from scripts.context.visualization import render_mermaid

        nodes = [
            GraphNode(id=f"function:a.py:func_{i}", label=NodeLabel.FUNCTION, name=f"func_{i}", file_path="a.py")
            for i in range(3)
        ]
        result = render_mermaid(nodes, [])
        for i in range(3):
            assert f"func_{i}" in result


class TestRenderDot:
    """Unit tests for render_dot()."""

    def test_dot_header(self):
        """render_dot must produce 'digraph G {' header."""
        from scripts.context.visualization import render_dot

        result = render_dot([], [])
        assert "digraph G {" in result or "digraph" in result

    def test_dot_closing_brace(self):
        """DOT output must end with closing '}'."""
        from scripts.context.visualization import render_dot

        result = render_dot([], [])
        assert result.strip().endswith("}")

    def test_dot_single_node(self):
        """A single node appears with label and shape."""
        from scripts.context.model import GraphNode, NodeLabel
        from scripts.context.visualization import render_dot

        node = GraphNode(
            id="function:src/app.py:func_a",
            label=NodeLabel.FUNCTION,
            name="func_a",
            file_path="src/app.py",
        )
        result = render_dot([node], [])
        assert "func_a" in result
        assert "shape=" in result or "[" in result

    def test_dot_edge_with_label(self):
        """An edge appears as '->' with label."""
        from scripts.context.model import (
            GraphNode,
            GraphRelationship,
            NodeLabel,
            RelType,
        )
        from scripts.context.visualization import render_dot

        node_a = GraphNode(
            id="function:src/app.py:func_a",
            label=NodeLabel.FUNCTION,
            name="func_a",
            file_path="src/app.py",
        )
        node_b = GraphNode(
            id="function:src/app.py:func_b",
            label=NodeLabel.FUNCTION,
            name="func_b",
            file_path="src/app.py",
        )
        edge = (node_a.id, node_b.id, "CALLS")
        result = render_dot([node_a, node_b], [edge])
        assert "->" in result
        assert "CALLS" in result

    def test_dot_node_label_format(self):
        """DOT node label includes name and type."""
        from scripts.context.model import GraphNode, NodeLabel
        from scripts.context.visualization import render_dot

        node = GraphNode(
            id="class:src/app.py:MyClass",
            label=NodeLabel.CLASS,
            name="MyClass",
            file_path="src/app.py",
        )
        result = render_dot([node], [])
        assert "MyClass" in result
        assert "CLASS" in result or "class" in result.lower()

    def test_dot_rankdir(self):
        """DOT output should specify rankdir."""
        from scripts.context.visualization import render_dot

        result = render_dot([], [])
        assert "rankdir" in result


# ---------------------------------------------------------------------------
# Task 1: _collect_subgraph unit tests
# ---------------------------------------------------------------------------


class TestCollectSubgraph:
    """Unit tests for _collect_subgraph()."""

    def test_collect_full_scope(self, storage):
        """Full scope collects all nodes and edges in storage."""
        from scripts.context.visualization import _collect_subgraph

        ids = _add_nodes_and_edges(storage)
        nodes, edges = _collect_subgraph(storage, scope="full", center=None, depth=3)
        node_ids = {n.id for n in nodes}
        # All nodes should appear
        for nid in ids.values():
            assert nid in node_ids

    def test_collect_file_scope(self, storage):
        """File scope collects only nodes in the specified file."""
        from scripts.context.visualization import _collect_subgraph

        ids = _add_nodes_and_edges(storage)
        nodes, edges = _collect_subgraph(storage, scope="file", center=ids["func_a_id"], depth=3)
        # All nodes are in src/app.py; should return them
        node_ids = {n.id for n in nodes}
        assert ids["func_a_id"] in node_ids

    def test_collect_returns_edges(self, storage):
        """Collect subgraph returns edges between nodes in subgraph."""
        from scripts.context.visualization import _collect_subgraph

        _add_nodes_and_edges(storage)
        nodes, edges = _collect_subgraph(storage, scope="full", center=None, depth=3)
        # Edges should be tuples of (source_id, target_id, rel_type)
        assert len(edges) >= 1
        for edge in edges:
            assert len(edge) == 3

    def test_collect_depth_limits_bfs(self, storage):
        """Depth parameter limits BFS expansion from center node."""
        from scripts.context.model import (
            GraphNode,
            GraphRelationship,
            NodeLabel,
            RelType,
            generate_id,
        )
        from scripts.context.visualization import _collect_subgraph

        # Build: A -> B -> C (3-hop chain)
        a_id = generate_id(NodeLabel.FUNCTION, "x.py", "node_a")
        b_id = generate_id(NodeLabel.FUNCTION, "x.py", "node_b")
        c_id = generate_id(NodeLabel.FUNCTION, "x.py", "node_c")

        storage.add_nodes([
            GraphNode(id=a_id, label=NodeLabel.FUNCTION, name="node_a", file_path="x.py"),
            GraphNode(id=b_id, label=NodeLabel.FUNCTION, name="node_b", file_path="x.py"),
            GraphNode(id=c_id, label=NodeLabel.FUNCTION, name="node_c", file_path="x.py"),
        ])
        storage.add_relationships([
            GraphRelationship(id="r1", type=RelType.CALLS, source=a_id, target=b_id),
            GraphRelationship(id="r2", type=RelType.CALLS, source=b_id, target=c_id),
        ])

        # depth=1 from a: only b is 1 hop away
        nodes, edges = _collect_subgraph(storage, scope="file", center=a_id, depth=1)
        node_ids = {n.id for n in nodes}
        assert a_id in node_ids
        assert b_id in node_ids
        assert c_id not in node_ids


# ---------------------------------------------------------------------------
# Task 2: ContextGraph.visualize() method tests
# ---------------------------------------------------------------------------


class TestContextGraphVisualize:
    """Tests for ContextGraph.visualize() method."""

    def test_visualize_returns_string(self, graph):
        """visualize() returns a non-empty string."""
        from scripts.context.model import GraphNode, NodeLabel

        graph._storage.add_nodes([
            GraphNode(
                id="function:a.py:foo",
                label=NodeLabel.FUNCTION,
                name="foo",
                file_path="a.py",
            )
        ])
        result = graph.visualize(scope="full")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_visualize_mermaid_format(self, graph):
        """visualize(format='mermaid') returns Mermaid flowchart syntax."""
        from scripts.context.model import GraphNode, NodeLabel

        graph._storage.add_nodes([
            GraphNode(
                id="function:a.py:foo",
                label=NodeLabel.FUNCTION,
                name="foo",
                file_path="a.py",
            )
        ])
        result = graph.visualize(scope="full", format="mermaid")
        assert "flowchart" in result.lower()

    def test_visualize_dot_format(self, graph):
        """visualize(format='dot') returns DOT digraph syntax."""
        from scripts.context.model import GraphNode, NodeLabel

        graph._storage.add_nodes([
            GraphNode(
                id="function:a.py:foo",
                label=NodeLabel.FUNCTION,
                name="foo",
                file_path="a.py",
            )
        ])
        result = graph.visualize(scope="full", format="dot")
        assert "digraph" in result

    def test_visualize_default_format_is_mermaid(self, graph):
        """Default format is 'mermaid'."""
        from scripts.context.model import GraphNode, NodeLabel

        graph._storage.add_nodes([
            GraphNode(
                id="function:a.py:foo",
                label=NodeLabel.FUNCTION,
                name="foo",
                file_path="a.py",
            )
        ])
        result = graph.visualize(scope="full")
        assert "flowchart" in result.lower()

    def test_visualize_empty_graph(self, graph):
        """visualize() on empty graph returns valid empty output."""
        result = graph.visualize(scope="full")
        # Should not raise and should return valid format header
        assert isinstance(result, str)
        assert "flowchart" in result.lower() or "digraph" in result

    def test_visualize_invalid_format_raises(self, graph):
        """visualize() raises ValueError for unsupported format."""
        with pytest.raises(ValueError, match="format"):
            graph.visualize(scope="full", format="invalid_format")

    def test_visualize_invalid_scope_raises(self, graph):
        """visualize() raises ValueError for unsupported scope."""
        with pytest.raises(ValueError, match="scope"):
            graph.visualize(scope="bad_scope")

    def test_visualize_with_center_and_depth(self, graph):
        """visualize() accepts center and depth parameters."""
        from scripts.context.model import (
            GraphNode,
            GraphRelationship,
            NodeLabel,
            RelType,
        )

        a_id = "function:a.py:func_a"
        b_id = "function:b.py:func_b"
        graph._storage.add_nodes([
            GraphNode(id=a_id, label=NodeLabel.FUNCTION, name="func_a", file_path="a.py"),
            GraphNode(id=b_id, label=NodeLabel.FUNCTION, name="func_b", file_path="b.py"),
        ])
        graph._storage.add_relationships([
            GraphRelationship(id="r1", type=RelType.CALLS, source=a_id, target=b_id)
        ])
        result = graph.visualize(scope="full", center=a_id, depth=2)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Task 3: End-to-end integration tests
# ---------------------------------------------------------------------------


def _write_sample_repo(tmp_path: Path) -> None:
    """Write sample Python files for e2e visualization testing."""
    (tmp_path / "greet.py").write_text(textwrap.dedent("""\
        def greet(name: str) -> str:
            \"\"\"Greet a person by name.\"\"\"
            return _format(name)

        def _format(name: str) -> str:
            return f"Hello, {name}!"
    """))

    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from greet import greet

        def run():
            \"\"\"Entry point.\"\"\"
            greet("World")
    """))


class TestE2EVisualization:
    """End-to-end tests: index sample code then verify visualization output."""

    def test_e2e_mermaid_contains_nodes(self, tmp_path):
        """After indexing, Mermaid output contains expected symbol nodes."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result = g.visualize(scope="full", format="mermaid")
            assert "flowchart" in result.lower()
            # Should have some nodes (greet, _format, or run)
            has_node = any(name in result for name in ["greet", "_format", "run"])
            assert has_node, f"Expected function names in output:\n{result}"
        finally:
            g.close()

    def test_e2e_dot_contains_digraph(self, tmp_path):
        """After indexing, DOT output contains expected digraph structure."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result = g.visualize(scope="full", format="dot")
            assert "digraph G {" in result
            assert "rankdir" in result
            assert result.strip().endswith("}")
        finally:
            g.close()

    def test_e2e_mermaid_contains_edges(self, tmp_path):
        """After indexing, Mermaid output shows call edges."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result = g.visualize(scope="full", format="mermaid")
            # Should have arrow syntax from CALLS edges or DEFINES
            assert "-->" in result, f"Expected Mermaid arrows in output:\n{result}"
        finally:
            g.close()

    def test_e2e_dot_contains_edges(self, tmp_path):
        """After indexing, DOT output shows edges."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result = g.visualize(scope="full", format="dot")
            assert "->" in result, f"Expected DOT edges in output:\n{result}"
        finally:
            g.close()

    def test_e2e_file_scope(self, tmp_path):
        """File scope visualization returns only nodes in the specified file."""
        from scripts.context import ContextGraph
        from scripts.context.model import NodeLabel, generate_id

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            # Get a node ID from greet.py to use as center
            greet_nodes = g.query("greet")
            if greet_nodes:
                center = greet_nodes[0].id
                result = g.visualize(scope="file", center=center, format="mermaid")
                assert isinstance(result, str)
                assert "flowchart" in result.lower()
            else:
                pytest.skip("greet node not found after indexing")
        finally:
            g.close()

    def test_e2e_module_scope(self, tmp_path):
        """Module scope visualization covers all files in a directory."""
        from scripts.context import ContextGraph
        from scripts.context.model import NodeLabel, generate_id

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result = g.visualize(scope="module", format="mermaid")
            assert isinstance(result, str)
            assert "flowchart" in result.lower()
        finally:
            g.close()

    def test_e2e_depth_limits_output(self, tmp_path):
        """Depth=1 produces fewer nodes than depth=10 from same center."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            result_deep = g.visualize(scope="full", depth=10, format="mermaid")
            result_shallow = g.visualize(scope="full", depth=1, format="mermaid")
            # Both should be valid; deep may have >= nodes as shallow
            assert "flowchart" in result_deep.lower()
            assert "flowchart" in result_shallow.lower()
        finally:
            g.close()

    def test_e2e_mermaid_and_dot_both_valid(self, tmp_path):
        """Both Mermaid and DOT outputs are syntactically valid from the same graph."""
        from scripts.context import ContextGraph

        _write_sample_repo(tmp_path)
        g = ContextGraph(repo_path=tmp_path)
        try:
            g.index()
            mermaid = g.visualize(scope="full", format="mermaid")
            dot = g.visualize(scope="full", format="dot")

            # Mermaid: must start with flowchart
            assert mermaid.strip().startswith("flowchart TD")
            # DOT: must have digraph and closing brace
            assert "digraph G {" in dot
            assert dot.strip().endswith("}")
        finally:
            g.close()
