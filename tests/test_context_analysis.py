"""Analysis tests: dead-code, coupling, impact, community, and flows."""

from __future__ import annotations

import pytest

from tests.conftest_context import (
    add_call_edge,
    add_function_node,
    add_import_edge,
    graph,
    write_python_files,
)


# --- dead_code ---


def test_dead_code_returns_results(graph):
    """An unreferenced function should appear in dead_code() results."""
    from scripts.context.phases.dead_code import DeadCodeResult
    add_function_node(graph._storage, "src/module.py", "orphan_func")
    results = graph.dead_code()
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], DeadCodeResult)
    assert results[0].name == "orphan_func"


def test_dead_code_empty_when_all_referenced(graph):
    """A function with an incoming CALLS edge should not be dead."""
    caller_id = add_function_node(graph._storage, "src/caller.py", "caller_func")
    callee_id = add_function_node(graph._storage, "src/callee.py", "callee_func")
    add_call_edge(graph._storage, caller_id, callee_id)
    results = graph.dead_code()
    dead_names = [r.name for r in results]
    assert "callee_func" not in dead_names


def test_dead_code_marks_is_dead_in_storage(graph):
    """After calling dead_code(), the node should have is_dead=True in storage."""
    node_id = add_function_node(graph._storage, "src/module.py", "unused_func")
    graph.dead_code()
    dead_nodes = graph._storage.get_dead_nodes()
    dead_ids = [n.id for n in dead_nodes]
    assert node_id in dead_ids


# --- coupling ---


def test_coupling_returns_results(graph):
    """Two functions sharing call targets should appear as coupled."""
    from scripts.context.phases.coupling import CouplingResult
    a = add_function_node(graph._storage, "src/a.py", "func_a")
    b = add_function_node(graph._storage, "src/b.py", "func_b")
    shared = add_function_node(graph._storage, "src/shared.py", "shared_func")
    add_call_edge(graph._storage, a, shared)
    add_call_edge(graph._storage, b, shared)

    results = graph.coupling(threshold=0.5)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], CouplingResult)
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"func_a", "func_b"}]
    assert len(ab_pairs) == 1


def test_coupling_empty_when_no_shared_neighbors(graph):
    """Functions with disjoint neighbors should not be coupled."""
    a = add_function_node(graph._storage, "src/a.py", "func_a")
    b = add_function_node(graph._storage, "src/b.py", "func_b")
    t1 = add_function_node(graph._storage, "src/t1.py", "target1")
    t2 = add_function_node(graph._storage, "src/t2.py", "target2")
    add_call_edge(graph._storage, a, t1)
    add_call_edge(graph._storage, b, t2)

    results = graph.coupling(threshold=0.5)
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"func_a", "func_b"}]
    assert len(ab_pairs) == 0


def test_coupling_threshold_filters(graph):
    """Higher threshold should filter out weaker coupling."""
    a = add_function_node(graph._storage, "src/a.py", "func_a")
    b = add_function_node(graph._storage, "src/b.py", "func_b")
    shared = add_function_node(graph._storage, "src/shared.py", "shared_func")
    add_call_edge(graph._storage, a, shared)
    add_call_edge(graph._storage, b, shared)

    results_low = graph.coupling(threshold=0.5)
    ab_low = [r for r in results_low if {r.source_name, r.target_name} == {"func_a", "func_b"}]

    results_high = graph.coupling(threshold=1.0)
    assert len(results_high) <= len(results_low)


# --- review_impact ---


def test_review_impact_returns_structured_dict(tmp_path):
    """review_impact should return dict with expected keys."""
    from scripts.context import ContextGraph
    write_python_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        result = g.review_impact(["lib.py"])
        assert isinstance(result, dict)
        assert result["graph_status"] == "indexed"
        assert "affected_files" in result
        assert "affected_symbols" in result
        assert "per_file" in result
        assert "total_affected" in result
        assert isinstance(result["affected_files"], list)
        assert isinstance(result["affected_symbols"], list)
        assert isinstance(result["total_affected"], int)
    finally:
        g.close()


def test_review_impact_empty_changed_files(tmp_path):
    """Empty changed_files list should return empty structure."""
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    try:
        result = g.review_impact([])
        assert result["graph_status"] == "indexed"
        assert result["affected_files"] == []
        assert result["affected_symbols"] == []
        assert result["total_affected"] == 0
        assert result["per_file"] == {}
    finally:
        g.close()


def test_review_impact_unknown_file(tmp_path):
    """Unknown file should produce empty impact gracefully."""
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    try:
        result = g.review_impact(["nonexistent.py"])
        assert result["graph_status"] == "indexed"
        assert result["total_affected"] == 0
        assert "nonexistent.py" in result["per_file"]
        assert result["per_file"]["nonexistent.py"] == []
    finally:
        g.close()


def test_review_impact_aggregates_multiple_files(tmp_path):
    """review_impact should aggregate impact across multiple changed files."""
    from scripts.context import ContextGraph
    write_python_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        result = g.review_impact(["lib.py", "util.py"])
        assert result["graph_status"] == "indexed"
        assert "lib.py" in result["per_file"]
        assert "util.py" in result["per_file"]
        assert result["total_affected"] >= 0
    finally:
        g.close()


# --- communities ---


def test_communities_returns_result_type(graph):
    """communities() should return a CommunityDetectionResult."""
    from scripts.context.phases.community import CommunityDetectionResult
    a = add_function_node(graph._storage, "src/a.py", "func_a")
    b = add_function_node(graph._storage, "src/b.py", "func_b")
    add_call_edge(graph._storage, a, b)

    result = graph.communities(min_size=2)
    assert isinstance(result, CommunityDetectionResult)
    assert result.num_communities >= 1


def test_communities_empty_graph(graph):
    """Empty graph should produce empty communities."""
    result = graph.communities()
    assert result.num_communities == 0
    assert result.total_nodes == 0
    assert result.communities == []


def test_communities_respects_min_size(graph):
    """min_size should filter out smaller groups."""
    a = add_function_node(graph._storage, "src/a.py", "func_a")
    b = add_function_node(graph._storage, "src/b.py", "func_b")
    add_call_edge(graph._storage, a, b)

    result2 = graph.communities(min_size=2)
    assert result2.num_communities >= 1

    result10 = graph.communities(min_size=10)
    assert result10.num_communities == 0


# --- flows ---


def test_flows_returns_list(graph):
    """flows() should return a list of FlowResult."""
    from scripts.context.phases.flows import FlowResult
    main_id = add_function_node(graph._storage, "src/app.py", "main")
    helper_id = add_function_node(graph._storage, "src/app.py", "helper")
    add_call_edge(graph._storage, main_id, helper_id)

    results = graph.flows()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], FlowResult)
    assert results[0].entry_point.name == "main"


def test_flows_max_depth(graph):
    """flows() should respect max_depth parameter."""
    from scripts.context.phases.flows import FlowResult
    main_id = add_function_node(graph._storage, "src/app.py", "main")
    a_id = add_function_node(graph._storage, "src/app.py", "func_a")
    b_id = add_function_node(graph._storage, "src/app.py", "func_b")
    add_call_edge(graph._storage, main_id, a_id)
    add_call_edge(graph._storage, a_id, b_id)

    results = graph.flows(max_depth=1)
    assert len(results) == 1
    step_names = [s.node.name for s in results[0].steps]
    assert "func_a" in step_names
    assert "func_b" not in step_names


def test_flows_exported_in_package():
    """FlowResult should be importable from the package."""
    from scripts.context import FlowResult
    assert FlowResult is not None
