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


# --- dead_code ---


def _add_function_node(storage, file_path, name, label=None):
    from scripts.context.model import GraphNode, NodeLabel, generate_id
    if label is None:
        label = NodeLabel.FUNCTION
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
    from scripts.context.model import GraphRelationship, RelType
    storage.add_relationships([
        GraphRelationship(
            id=f"calls:{caller_id}->{callee_id}",
            type=RelType.CALLS,
            source=caller_id,
            target=callee_id,
        )
    ])


def test_dead_code_returns_results(graph):
    """An unreferenced function should appear in dead_code() results."""
    from scripts.context.phases.dead_code import DeadCodeResult
    _add_function_node(graph._storage, "src/module.py", "orphan_func")
    results = graph.dead_code()
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], DeadCodeResult)
    assert results[0].name == "orphan_func"


def test_dead_code_empty_when_all_referenced(graph):
    """A function with an incoming CALLS edge should not be dead."""
    caller_id = _add_function_node(graph._storage, "src/caller.py", "caller_func")
    callee_id = _add_function_node(graph._storage, "src/callee.py", "callee_func")
    _add_call_edge(graph._storage, caller_id, callee_id)
    # caller_func has no incoming edges but has name "caller_func" — not an entry point
    # callee_func has an incoming CALLS edge — should not be dead
    results = graph.dead_code()
    dead_names = [r.name for r in results]
    assert "callee_func" not in dead_names


def test_dead_code_marks_is_dead_in_storage(graph):
    """After calling dead_code(), the node should have is_dead=True in storage."""
    node_id = _add_function_node(graph._storage, "src/module.py", "unused_func")
    graph.dead_code()
    dead_nodes = graph._storage.get_dead_nodes()
    dead_ids = [n.id for n in dead_nodes]
    assert node_id in dead_ids
