"""Core ContextGraph tests: construction, indexing, queries, calls, search, package exports."""

from __future__ import annotations

import pytest

from tests.conftest_context import (
    add_call_edge,
    add_function_node,
    graph,
    write_docstring_files,
    write_python_files,
)


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


# --- Stub methods ---


def test_index_runs_on_empty_repo(graph):
    graph.index()
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


# --- nodes_in_file ---


def test_nodes_in_file_returns_empty_for_unknown_file(graph):
    assert graph.nodes_in_file("unknown.py") == []


def test_nodes_in_file_returns_nodes(graph):
    from scripts.context.model import GraphNode, NodeLabel, generate_id

    nid = generate_id(NodeLabel.FUNCTION, "src/a.py", "foo")
    graph._storage.add_nodes(
        [GraphNode(id=nid, label=NodeLabel.FUNCTION, name="foo", file_path="src/a.py")]
    )
    result = graph.nodes_in_file("src/a.py")
    assert len(result) == 1
    assert result[0].id == nid


# --- callers_with_confidence ---


def test_callers_with_confidence_returns_empty(graph):
    assert graph.callers_with_confidence("nonexistent") == []


def test_callers_with_confidence_returns_caller_and_score(graph):
    from scripts.context.model import (
        GraphNode, GraphRelationship, NodeLabel, RelType, generate_id,
    )

    callee_id = generate_id(NodeLabel.FUNCTION, "a.py", "callee")
    caller_id = generate_id(NodeLabel.FUNCTION, "b.py", "caller")
    graph._storage.add_nodes([
        GraphNode(id=callee_id, label=NodeLabel.FUNCTION, name="callee", file_path="a.py"),
        GraphNode(id=caller_id, label=NodeLabel.FUNCTION, name="caller", file_path="b.py"),
    ])
    graph._storage.add_relationships([
        GraphRelationship(
            id=f"calls:{caller_id}->{callee_id}",
            type=RelType.CALLS,
            source=caller_id,
            target=callee_id,
            properties={"confidence": 0.5},
        )
    ])
    results = graph.callers_with_confidence(callee_id)
    assert len(results) == 1
    node, conf = results[0]
    assert node.id == caller_id
    assert conf == 0.5


# --- callees ---


def test_callees_returns_empty(graph):
    assert graph.callees("nonexistent") == []


def test_callees_returns_called_nodes(graph):
    from scripts.context.model import (
        GraphNode, GraphRelationship, NodeLabel, RelType, generate_id,
    )

    caller_id = generate_id(NodeLabel.FUNCTION, "a.py", "caller")
    callee_id = generate_id(NodeLabel.FUNCTION, "b.py", "callee")
    graph._storage.add_nodes([
        GraphNode(id=caller_id, label=NodeLabel.FUNCTION, name="caller", file_path="a.py"),
        GraphNode(id=callee_id, label=NodeLabel.FUNCTION, name="callee", file_path="b.py"),
    ])
    graph._storage.add_relationships([
        GraphRelationship(
            id=f"calls:{caller_id}->{callee_id}",
            type=RelType.CALLS,
            source=caller_id,
            target=callee_id,
        )
    ])
    results = graph.callees(caller_id)
    assert len(results) == 1
    assert results[0].id == callee_id


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


# --- review_impact ---


def test_review_impact_returns_structured_dict(tmp_path):
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


# --- Docstring extraction + FTS search ---


def test_docstrings_populated_in_content_field(tmp_path):
    from scripts.context import ContextGraph
    write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        nodes = g.query("add_numbers")
        assert len(nodes) == 1
        assert "Add two numbers" in nodes[0].content
    finally:
        g.close()


def test_fts_search_finds_by_docstring_keywords(tmp_path):
    from scripts.context import ContextGraph
    write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g._storage.search("mathematical computation")
        names = [n.name for n, _ in results]
        assert "MathEngine" in names
    finally:
        g.close()


def test_fts_search_finds_by_partial_name(tmp_path):
    from scripts.context import ContextGraph
    write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g._storage.search("multiply")
        names = [n.name for n, _ in results]
        assert "multiply" in names
    finally:
        g.close()


# --- ContextGraph.search() API ---


def test_search_returns_ranked_results(tmp_path):
    from scripts.context import ContextGraph
    write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g.search("multiply")
        assert len(results) >= 1
        node, score = results[0]
        assert node.name == "multiply"
        assert isinstance(score, float)
    finally:
        g.close()


def test_search_with_limit(tmp_path):
    from scripts.context import ContextGraph
    write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g.search("compute", limit=1)
        assert len(results) <= 1
    finally:
        g.close()


def test_search_exported_in_package():
    from scripts.context import ContextGraph
    assert hasattr(ContextGraph, "search")


# --- test_coverage ---


def test_coverage_returns_mapping_structure(tmp_path):
    """test_coverage() should return a dict with coverage mapping keys."""
    import textwrap
    from scripts.context import ContextGraph

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "math_utils.py").write_text(textwrap.dedent("""\
        def add(a, b):
            return a + b

        def subtract(a, b):
            return a - b
    """))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_math.py").write_text(textwrap.dedent("""\
        from src.math_utils import add

        def test_add():
            assert add(1, 2) == 3
    """))

    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        result = g.test_coverage()
        assert isinstance(result, dict)
        assert "covered_symbols" in result
        assert "uncovered_symbols" in result
        assert "coverage_by_file" in result
        assert "summary" in result
        assert isinstance(result["covered_symbols"], list)
        assert isinstance(result["uncovered_symbols"], list)
        assert isinstance(result["coverage_by_file"], dict)
        assert isinstance(result["summary"], dict)
    finally:
        g.close()


def test_coverage_empty_graph(tmp_path):
    """Empty graph should return all-empty coverage."""
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    try:
        result = g.test_coverage()
        assert result["covered_symbols"] == []
        assert result["uncovered_symbols"] == []
        assert result["coverage_by_file"] == {}
        summary = result["summary"]
        assert summary["total_symbols"] == 0
        assert summary["covered"] == 0
        assert summary["uncovered"] == 0
    finally:
        g.close()


def test_coverage_report_workflow_enabled(tmp_path):
    """test_coverage_report() should return enabled=True and coverage keys."""
    from scripts.context.workflow import test_coverage_report
    result = test_coverage_report(tmp_path)
    assert result["enabled"] is True
    assert "covered_symbols" in result
    assert "uncovered_symbols" in result
    assert "coverage_by_file" in result
    assert "summary" in result


def test_coverage_report_workflow_disabled_on_error():
    """test_coverage_report() with bad path should return enabled=False gracefully."""
    from scripts.context.workflow import test_coverage_report
    result = test_coverage_report("/nonexistent/path/that/cant/exist/xyz")
    assert result["enabled"] is False
    assert "error" in result


def test_coverage_summary_has_counts(tmp_path):
    """summary dict should include total_symbols, covered, uncovered, coverage_pct."""
    import textwrap
    from scripts.context import ContextGraph

    (tmp_path / "mylib.py").write_text(textwrap.dedent("""\
        def covered_func():
            pass

        def uncovered_func():
            pass
    """))
    (tmp_path / "test_mylib.py").write_text(textwrap.dedent("""\
        from mylib import covered_func

        def test_covered():
            covered_func()
    """))

    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        result = g.test_coverage()
        summary = result["summary"]
        assert "total_symbols" in summary
        assert "covered" in summary
        assert "uncovered" in summary
        assert "coverage_pct" in summary
        assert isinstance(summary["coverage_pct"], float)
        assert 0.0 <= summary["coverage_pct"] <= 100.0
    finally:
        g.close()
