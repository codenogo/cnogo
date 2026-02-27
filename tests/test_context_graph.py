"""Tests for ContextGraph class skeleton."""

from __future__ import annotations

import pytest


@pytest.fixture
def graph(tmp_path):
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    yield g
    g.close()


# --- Construction ---


def test_context_graph_construction(tmp_path):
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    assert g.repo_path == tmp_path
    g.close()


def test_db_path_under_cnogo(tmp_path):
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    assert g.db_path == tmp_path / ".cnogo" / "graph.db"
    g.close()


# --- is_indexed ---


def test_is_indexed_false_on_fresh_db(graph):
    assert graph.is_indexed() is False


def test_is_indexed_true_after_adding_nodes(graph):
    from scripts.context.model import GraphNode, NodeLabel
    node = GraphNode(
        id="function:foo.py:bar",
        label=NodeLabel.FUNCTION,
        name="bar",
        file_path="foo.py",
    )
    graph._storage.add_nodes([node])
    assert graph.is_indexed() is True


# --- Stub methods raise NotImplementedError ---


def test_index_runs_on_empty_repo(graph):
    graph.index()
    # No files to index — should not crash
    assert graph.is_indexed() is False


def test_query_returns_empty_on_fresh_db(graph):
    results = graph.query("nonexistent")
    assert results == []


def test_impact_returns_empty_for_unknown_file(graph):
    results = graph.impact("nonexistent.py")
    assert results == []


def test_context_raises_for_unknown_node(graph):
    with pytest.raises(ValueError, match="not found"):
        graph.context("function:foo.py:bar")


# --- Package exports ---


def test_package_exports_core_types():
    from scripts.context import (
        ContextGraph,
        GraphNode,
        GraphRelationship,
        NodeLabel,
        RelType,
    )
    assert ContextGraph is not None
    assert GraphNode is not None
    assert GraphRelationship is not None
    assert NodeLabel is not None
    assert RelType is not None
