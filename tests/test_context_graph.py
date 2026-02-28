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


# --- coupling ---


def _add_import_edge(storage, source_id, target_id):
    from scripts.context.model import GraphRelationship, RelType
    storage.add_relationships([
        GraphRelationship(
            id=f"imports:{source_id}->{target_id}",
            type=RelType.IMPORTS,
            source=source_id,
            target=target_id,
        )
    ])


def test_coupling_returns_results(graph):
    """Two functions sharing call targets should appear as coupled."""
    from scripts.context.phases.coupling import CouplingResult
    a = _add_function_node(graph._storage, "src/a.py", "func_a")
    b = _add_function_node(graph._storage, "src/b.py", "func_b")
    shared = _add_function_node(graph._storage, "src/shared.py", "shared_func")
    _add_call_edge(graph._storage, a, shared)
    _add_call_edge(graph._storage, b, shared)

    results = graph.coupling(threshold=0.5)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], CouplingResult)
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"func_a", "func_b"}]
    assert len(ab_pairs) == 1


def test_coupling_empty_when_no_shared_neighbors(graph):
    """Functions with disjoint neighbors should not be coupled."""
    a = _add_function_node(graph._storage, "src/a.py", "func_a")
    b = _add_function_node(graph._storage, "src/b.py", "func_b")
    t1 = _add_function_node(graph._storage, "src/t1.py", "target1")
    t2 = _add_function_node(graph._storage, "src/t2.py", "target2")
    _add_call_edge(graph._storage, a, t1)
    _add_call_edge(graph._storage, b, t2)

    results = graph.coupling(threshold=0.5)
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"func_a", "func_b"}]
    assert len(ab_pairs) == 0


def test_coupling_threshold_filters(graph):
    """Higher threshold should filter out weaker coupling."""
    a = _add_function_node(graph._storage, "src/a.py", "func_a")
    b = _add_function_node(graph._storage, "src/b.py", "func_b")
    shared = _add_function_node(graph._storage, "src/shared.py", "shared_func")
    _add_call_edge(graph._storage, a, shared)
    _add_call_edge(graph._storage, b, shared)

    # At threshold=0.5, should find coupling
    results_low = graph.coupling(threshold=0.5)
    ab_low = [r for r in results_low if {r.source_name, r.target_name} == {"func_a", "func_b"}]

    # At threshold=1.0, only perfect matches pass — (a,b) may not be 1.0
    # depending on other neighbors
    results_high = graph.coupling(threshold=1.0)
    # At minimum, high threshold should be <= low threshold results
    assert len(results_high) <= len(results_low)


# --- review_impact ---


def _write_python_files(tmp_path):
    """Create a small repo with cross-file dependencies for impact testing."""
    import textwrap
    (tmp_path / "lib.py").write_text(textwrap.dedent("""\
        def helper():
            pass
    """))
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from lib import helper

        def run():
            helper()
    """))
    (tmp_path / "util.py").write_text(textwrap.dedent("""\
        def standalone():
            pass
    """))


def test_review_impact_returns_structured_dict(tmp_path):
    """review_impact should return dict with expected keys."""
    from scripts.context import ContextGraph
    _write_python_files(tmp_path)
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
    _write_python_files(tmp_path)
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
    a = _add_function_node(graph._storage, "src/a.py", "func_a")
    b = _add_function_node(graph._storage, "src/b.py", "func_b")
    _add_call_edge(graph._storage, a, b)

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
    a = _add_function_node(graph._storage, "src/a.py", "func_a")
    b = _add_function_node(graph._storage, "src/b.py", "func_b")
    _add_call_edge(graph._storage, a, b)

    # min_size=2 should include the pair
    result2 = graph.communities(min_size=2)
    assert result2.num_communities >= 1

    # min_size=10 should exclude everything
    result10 = graph.communities(min_size=10)
    assert result10.num_communities == 0


# --- flows ---


def test_flows_returns_list(graph):
    """flows() should return a list of FlowResult."""
    from scripts.context.phases.flows import FlowResult
    main_id = _add_function_node(graph._storage, "src/app.py", "main")
    helper_id = _add_function_node(graph._storage, "src/app.py", "helper")
    _add_call_edge(graph._storage, main_id, helper_id)

    results = graph.flows()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert isinstance(results[0], FlowResult)
    assert results[0].entry_point.name == "main"


def test_flows_max_depth(graph):
    """flows() should respect max_depth parameter."""
    from scripts.context.phases.flows import FlowResult
    main_id = _add_function_node(graph._storage, "src/app.py", "main")
    a_id = _add_function_node(graph._storage, "src/app.py", "func_a")
    b_id = _add_function_node(graph._storage, "src/app.py", "func_b")
    _add_call_edge(graph._storage, main_id, a_id)
    _add_call_edge(graph._storage, a_id, b_id)

    results = graph.flows(max_depth=1)
    assert len(results) == 1
    step_names = [s.node.name for s in results[0].steps]
    assert "func_a" in step_names
    assert "func_b" not in step_names


def test_flows_exported_in_package():
    """FlowResult should be importable from the package."""
    from scripts.context import FlowResult
    assert FlowResult is not None


# --- Docstring extraction + FTS search ---


def _write_docstring_files(tmp_path):
    """Create Python files with docstrings for FTS testing."""
    import textwrap
    (tmp_path / "calculator.py").write_text(textwrap.dedent('''\
        def add_numbers(a, b):
            """Add two numbers together and return the sum."""
            return a + b

        def multiply(a, b):
            """Multiply two values and return the product."""
            return a * b

        class MathEngine:
            """A mathematical computation engine for complex calculations."""

            def compute(self, expr):
                """Evaluate a mathematical expression string."""
                pass
    '''))


def test_docstrings_populated_in_content_field(tmp_path):
    """After indexing, symbol nodes should have docstrings in the content field."""
    from scripts.context import ContextGraph
    _write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        nodes = g.query("add_numbers")
        assert len(nodes) == 1
        assert "Add two numbers" in nodes[0].content
    finally:
        g.close()


def test_fts_search_finds_by_docstring_keywords(tmp_path):
    """FTS search should find symbols by docstring keywords."""
    from scripts.context import ContextGraph
    _write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g._storage.search("mathematical computation")
        names = [n.name for n, _ in results]
        assert "MathEngine" in names
    finally:
        g.close()


def test_fts_search_finds_by_partial_name(tmp_path):
    """FTS search should find symbols by partial name match."""
    from scripts.context import ContextGraph
    _write_docstring_files(tmp_path)
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
    """ContextGraph.search() returns ranked (node, score) tuples."""
    from scripts.context import ContextGraph
    _write_docstring_files(tmp_path)
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
    """ContextGraph.search() respects limit parameter."""
    from scripts.context import ContextGraph
    _write_docstring_files(tmp_path)
    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        results = g.search("compute", limit=1)
        assert len(results) <= 1
    finally:
        g.close()


def test_search_exported_in_package():
    """ImpactResult should be importable from the package."""
    from scripts.context import ContextGraph
    assert hasattr(ContextGraph, "search")


# --- types phase (USES_TYPE edges) ---


def _write_typed_python_file(tmp_path, filename, source):
    """Write a Python source file with type annotations."""
    (tmp_path / filename).write_text(source)


def _make_storage_with_nodes(tmp_path):
    """Create a GraphStorage with a function and class node for type tests."""
    import textwrap
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test.db")
    db.initialize()

    # Add a class node (type target)
    class_node = GraphNode(
        id="class:mymodule.py:MyClass",
        label=NodeLabel.CLASS,
        name="MyClass",
        file_path="mymodule.py",
        start_line=1,
        end_line=10,
    )
    # Add a function node that uses MyClass as param annotation (lines 12-15)
    func_node = GraphNode(
        id="function:mymodule.py:my_func",
        label=NodeLabel.FUNCTION,
        name="my_func",
        file_path="mymodule.py",
        start_line=12,
        end_line=15,
    )
    db.add_nodes([class_node, func_node])
    return db


def test_uses_type_edges_from_param_annotations(tmp_path):
    """USES_TYPE edges should be created from function parameter annotations."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType

    db = _make_storage_with_nodes(tmp_path)

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            type_refs=[
                TypeRef(name="MyClass", kind="param", line=12),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target, type FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    source, target, rel_type = rows[0]
    assert source == "function:mymodule.py:my_func"
    assert target == "class:mymodule.py:MyClass"
    assert rel_type == RelType.USES_TYPE.value
    db.close()


def test_uses_type_edges_from_return_annotations(tmp_path):
    """USES_TYPE edges should be created from return type annotations."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test2.db")
    db.initialize()

    class_node = GraphNode(
        id="class:service.py:Response",
        label=NodeLabel.CLASS,
        name="Response",
        file_path="service.py",
        start_line=1,
        end_line=5,
    )
    func_node = GraphNode(
        id="function:service.py:get_response",
        label=NodeLabel.FUNCTION,
        name="get_response",
        file_path="service.py",
        start_line=7,
        end_line=12,
    )
    db.add_nodes([class_node, func_node])

    parse_results = {
        "service.py": ParseResult(
            file_path="service.py",
            type_refs=[
                TypeRef(name="Response", kind="return", line=7),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target, type FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    source, target, rel_type = rows[0]
    assert source == "function:service.py:get_response"
    assert target == "class:service.py:Response"
    db.close()


def test_uses_type_resolves_same_file_class(tmp_path):
    """USES_TYPE edges should resolve to same-file class nodes."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test3.db")
    db.initialize()

    # Two classes with same name in different files
    class_a = GraphNode(
        id="class:file_a.py:Widget",
        label=NodeLabel.CLASS,
        name="Widget",
        file_path="file_a.py",
        start_line=1,
        end_line=5,
    )
    class_b = GraphNode(
        id="class:file_b.py:Widget",
        label=NodeLabel.CLASS,
        name="Widget",
        file_path="file_b.py",
        start_line=1,
        end_line=5,
    )
    func_node = GraphNode(
        id="function:file_a.py:render",
        label=NodeLabel.FUNCTION,
        name="render",
        file_path="file_a.py",
        start_line=7,
        end_line=10,
    )
    db.add_nodes([class_a, class_b, func_node])

    parse_results = {
        "file_a.py": ParseResult(
            file_path="file_a.py",
            type_refs=[
                TypeRef(name="Widget", kind="param", line=7),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    # Should resolve to same-file class
    assert len(rows) == 1
    source, target = rows[0]
    assert target == "class:file_a.py:Widget"
    db.close()


def test_uses_type_no_edge_for_unresolvable_type(tmp_path):
    """No USES_TYPE edges should be created for unresolvable type names."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage

    db = GraphStorage(tmp_path / "test4.db")
    db.initialize()

    # No class nodes in storage — type "str" won't resolve
    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            type_refs=[
                TypeRef(name="str", kind="param", line=5),
                TypeRef(name="int", kind="return", line=5),
                TypeRef(name="NonExistentClass", kind="param", line=5),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    count = cur.fetchone()[0]
    assert count == 0
    db.close()


def test_uses_type_pipeline_integration(tmp_path):
    """index() pipeline should produce USES_TYPE edges for typed functions."""
    import textwrap
    from scripts.context import ContextGraph
    from scripts.context.model import RelType

    source = textwrap.dedent("""\
        class MyModel:
            pass

        def process(obj: MyModel) -> MyModel:
            return obj
    """)
    (tmp_path / "typed_module.py").write_text(source)

    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        assert g._storage._conn is not None
        cur = g._storage._conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE type = ?",
            (RelType.USES_TYPE.value,),
        )
        count = cur.fetchone()[0]
        assert count >= 1
    finally:
        g.close()
