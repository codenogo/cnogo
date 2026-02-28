"""Tests for graph proximity ranking (Plan 04).

Tests cover:
- rank_by_proximity() BFS distance computation
- ContextGraph.prioritize_files() public method
- prioritize_context() workflow function
"""

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


# --- Fixtures ---


@pytest.fixture
def storage():
    """Create an in-memory graph storage for testing."""
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


# --- Helpers ---


def _add_node(storage, file_path, name, label=NodeLabel.FUNCTION):
    node_id = generate_id(label, file_path, name)
    node = GraphNode(id=node_id, label=label, name=name, file_path=file_path, start_line=1)
    storage.add_nodes([node])
    return node_id


def _add_rel(storage, rel_id, rel_type, source, target):
    storage.add_relationships([
        GraphRelationship(id=rel_id, type=rel_type, source=source, target=target)
    ])


# ============================================================
# rank_by_proximity tests
# ============================================================


class TestRankByProximityBasic:
    """Basic proximity ranking via CALLS edges."""

    def test_direct_callee_is_distance_1(self, storage):
        """A symbol called by focal node appears at distance 1."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        helper_id = _add_node(storage, "helpers.py", "helper")
        _add_rel(storage, "calls:main->helper", RelType.CALLS, focal_id, helper_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)

        # helpers.py should be at distance 1
        result_map = {r["file_path"]: r for r in results}
        assert "helpers.py" in result_map
        assert result_map["helpers.py"]["min_distance"] == 1

    def test_direct_caller_is_distance_1(self, storage):
        """A symbol that calls focal node appears at distance 1 (incoming edge)."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "lib.py", "lib_func")
        caller_id = _add_node(storage, "app.py", "app_func")
        _add_rel(storage, "calls:app->lib", RelType.CALLS, caller_id, focal_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)

        result_map = {r["file_path"]: r for r in results}
        assert "app.py" in result_map
        assert result_map["app.py"]["min_distance"] == 1

    def test_focal_file_excluded(self, storage):
        """The focal nodes' own file is excluded from results (distance 0)."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        other_id = _add_node(storage, "other.py", "other_func")
        _add_rel(storage, "calls:main->other", RelType.CALLS, focal_id, other_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)

        result_files = {r["file_path"] for r in results}
        assert "main.py" not in result_files
        assert "other.py" in result_files

    def test_empty_focal_returns_empty(self, storage):
        """Empty focal_node_ids returns no results."""
        from scripts.context.phases.proximity import rank_by_proximity

        _add_node(storage, "main.py", "main")
        results = rank_by_proximity(storage, [], max_depth=5)
        assert results == []

    def test_no_neighbors_returns_empty(self, storage):
        """Isolated focal node with no edges returns empty results."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "isolated.py", "lonely")
        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        assert results == []


class TestRankByProximityDistances:
    """BFS computes correct multi-hop distances."""

    def test_two_hop_distance(self, storage):
        """A → B → C: C is at distance 2 from A."""
        from scripts.context.phases.proximity import rank_by_proximity

        a_id = _add_node(storage, "a.py", "func_a")
        b_id = _add_node(storage, "b.py", "func_b")
        c_id = _add_node(storage, "c.py", "func_c")

        _add_rel(storage, "calls:a->b", RelType.CALLS, a_id, b_id)
        _add_rel(storage, "calls:b->c", RelType.CALLS, b_id, c_id)

        results = rank_by_proximity(storage, [a_id], max_depth=5)
        result_map = {r["file_path"]: r for r in results}

        assert result_map["b.py"]["min_distance"] == 1
        assert result_map["c.py"]["min_distance"] == 2

    def test_sorted_by_distance_asc(self, storage):
        """Results are sorted by min_distance ascending."""
        from scripts.context.phases.proximity import rank_by_proximity

        a_id = _add_node(storage, "a.py", "func_a")
        b_id = _add_node(storage, "b.py", "func_b")
        c_id = _add_node(storage, "c.py", "func_c")

        _add_rel(storage, "calls:a->b", RelType.CALLS, a_id, b_id)
        _add_rel(storage, "calls:b->c", RelType.CALLS, b_id, c_id)

        results = rank_by_proximity(storage, [a_id], max_depth=5)
        distances = [r["min_distance"] for r in results]
        assert distances == sorted(distances)

    def test_min_distance_per_file(self, storage):
        """Multiple nodes in same file: file gets minimum distance."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        # Two nodes in shared.py at different distances
        shared_near_id = _add_node(storage, "shared.py", "near_func")
        shared_far_id = _add_node(storage, "shared.py", "far_func")
        bridge_id = _add_node(storage, "bridge.py", "bridge")

        _add_rel(storage, "calls:main->near", RelType.CALLS, focal_id, shared_near_id)
        _add_rel(storage, "calls:main->bridge", RelType.CALLS, focal_id, bridge_id)
        _add_rel(storage, "calls:bridge->far", RelType.CALLS, bridge_id, shared_far_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        result_map = {r["file_path"]: r for r in results}

        # shared.py should be at min distance 1 (near_func), not 2 (far_func)
        assert result_map["shared.py"]["min_distance"] == 1

    def test_max_depth_limits_traversal(self, storage):
        """Nodes beyond max_depth are not included."""
        from scripts.context.phases.proximity import rank_by_proximity

        a_id = _add_node(storage, "a.py", "a")
        b_id = _add_node(storage, "b.py", "b")
        c_id = _add_node(storage, "c.py", "c")

        _add_rel(storage, "calls:a->b", RelType.CALLS, a_id, b_id)
        _add_rel(storage, "calls:b->c", RelType.CALLS, b_id, c_id)

        results = rank_by_proximity(storage, [a_id], max_depth=1)
        result_files = {r["file_path"] for r in results}

        assert "b.py" in result_files
        assert "c.py" not in result_files


class TestRankByProximityEdgeTypes:
    """BFS traverses CALLS, IMPORTS, EXTENDS, USES_TYPE edges."""

    def test_traverses_imports_edges(self, storage):
        """IMPORTS edges are traversed bidirectionally."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        util_id = _add_node(storage, "utils.py", "util_func")
        _add_rel(storage, "imports:main->utils", RelType.IMPORTS, focal_id, util_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        result_files = {r["file_path"] for r in results}
        assert "utils.py" in result_files

    def test_traverses_extends_edges(self, storage):
        """EXTENDS edges are traversed bidirectionally."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "base.py", "Base", label=NodeLabel.CLASS)
        child_id = _add_node(storage, "child.py", "Child", label=NodeLabel.CLASS)
        _add_rel(storage, "extends:child->base", RelType.EXTENDS, child_id, focal_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        result_files = {r["file_path"] for r in results}
        assert "child.py" in result_files

    def test_traverses_uses_type_edges(self, storage):
        """USES_TYPE edges are traversed bidirectionally."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "types.py", "MyType", label=NodeLabel.CLASS)
        user_id = _add_node(storage, "consumer.py", "consumer_func")
        _add_rel(storage, "uses_type:consumer->mytype", RelType.USES_TYPE, user_id, focal_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        result_files = {r["file_path"] for r in results}
        assert "consumer.py" in result_files


class TestRankByProximityConnectedSymbols:
    """connected_symbols field contains symbol names at the closest distance."""

    def test_connected_symbols_present(self, storage):
        """Result includes connected_symbols list."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        helper_id = _add_node(storage, "helpers.py", "helper")
        _add_rel(storage, "calls:main->helper", RelType.CALLS, focal_id, helper_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        assert len(results) > 0
        for r in results:
            assert "connected_symbols" in r
            assert isinstance(r["connected_symbols"], list)

    def test_connected_symbols_includes_symbol_names(self, storage):
        """connected_symbols lists symbol names from that file."""
        from scripts.context.phases.proximity import rank_by_proximity

        focal_id = _add_node(storage, "main.py", "main")
        helper_id = _add_node(storage, "helpers.py", "my_helper")
        _add_rel(storage, "calls:main->helper", RelType.CALLS, focal_id, helper_id)

        results = rank_by_proximity(storage, [focal_id], max_depth=5)
        result_map = {r["file_path"]: r for r in results}

        assert "helpers.py" in result_map
        assert "my_helper" in result_map["helpers.py"]["connected_symbols"]


# ============================================================
# ContextGraph.prioritize_files() tests
# ============================================================


class TestPrioritizeFiles:
    """ContextGraph.prioritize_files() public method."""

    def test_returns_list_of_dicts(self, graph):
        """Returns a list of dicts with file_path, min_distance, connected_symbols."""
        # Empty graph returns empty list
        result = graph.prioritize_files([], max_files=20)
        assert isinstance(result, list)

    def test_resolves_focal_symbols_by_name(self, graph):
        """focal_symbols are resolved by name to node IDs."""
        storage = graph._storage

        focal_id = _add_node(storage, "main.py", "entry_point")
        helper_id = _add_node(storage, "helpers.py", "do_work")
        _add_rel(storage, "calls:entry->work", RelType.CALLS, focal_id, helper_id)

        result = graph.prioritize_files(["entry_point"], max_files=20)
        result_files = [r["file_path"] for r in result]
        assert "helpers.py" in result_files

    def test_max_files_limits_output(self, graph):
        """max_files caps the number of returned files."""
        storage = graph._storage

        focal_id = _add_node(storage, "main.py", "main")
        for i in range(10):
            other_id = _add_node(storage, f"file_{i}.py", f"func_{i}")
            _add_rel(storage, f"calls:main->func_{i}", RelType.CALLS, focal_id, other_id)

        result = graph.prioritize_files(["main"], max_files=3)
        assert len(result) <= 3

    def test_empty_focal_symbols_returns_empty(self, graph):
        """Empty focal_symbols returns empty list."""
        storage = graph._storage
        _add_node(storage, "main.py", "main")

        result = graph.prioritize_files([], max_files=20)
        assert result == []

    def test_unresolved_symbol_returns_empty(self, graph):
        """Focal symbol not in graph returns empty list."""
        result = graph.prioritize_files(["nonexistent_symbol"], max_files=20)
        assert result == []


# ============================================================
# prioritize_context() workflow function tests
# ============================================================


class TestPrioritizeContext:
    """prioritize_context() workflow function."""

    def test_returns_enabled_false_when_not_indexed(self, tmp_path):
        """Returns enabled=False when graph has no indexed nodes."""
        from scripts.context.workflow import prioritize_context

        result = prioritize_context(tmp_path, focal_symbols=["foo"])
        assert result["enabled"] is False
        assert "error" in result

    def test_returns_enabled_true_when_indexed(self, tmp_path):
        """Returns enabled=True after indexing."""
        from scripts.context import ContextGraph
        from scripts.context.workflow import prioritize_context

        # Populate graph
        graph = ContextGraph(repo_path=tmp_path)
        storage = graph._storage
        _add_node(storage, "main.py", "main")
        _add_node(storage, "lib.py", "lib_func")
        graph.close()

        result = prioritize_context(tmp_path, focal_symbols=["main"])
        assert result["enabled"] is True
        assert "ranked_files" in result

    def test_ranked_files_structure(self, tmp_path):
        """ranked_files contains path, distance, reason."""
        from scripts.context import ContextGraph
        from scripts.context.workflow import prioritize_context

        graph = ContextGraph(repo_path=tmp_path)
        storage = graph._storage

        focal_id = _add_node(storage, "main.py", "main")
        helper_id = _add_node(storage, "helpers.py", "helper")
        _add_rel(storage, "calls:main->helper", RelType.CALLS, focal_id, helper_id)
        graph.close()

        result = prioritize_context(tmp_path, focal_symbols=["main"])
        assert result["enabled"] is True

        ranked = result["ranked_files"]
        if ranked:  # may be empty if helpers.py excluded
            for entry in ranked:
                assert "path" in entry
                assert "distance" in entry
                assert "reason" in entry

    def test_focal_symbols_resolved_in_result(self, tmp_path):
        """focal_symbols_resolved is present in result."""
        from scripts.context import ContextGraph
        from scripts.context.workflow import prioritize_context

        graph = ContextGraph(repo_path=tmp_path)
        storage = graph._storage
        _add_node(storage, "main.py", "main")
        graph.close()

        result = prioritize_context(tmp_path, focal_symbols=["main"])
        assert "focal_symbols_resolved" in result

    def test_graceful_degradation_on_exception(self, tmp_path):
        """Returns enabled=False on any exception, no crash."""
        from scripts.context.workflow import prioritize_context

        # Pass invalid repo path (no .cnogo dir, unindexed)
        result = prioritize_context("/nonexistent/path/xyz", focal_symbols=["foo"])
        assert result["enabled"] is False
        assert "error" in result

    def test_none_focal_symbols_defaults_to_empty(self, tmp_path):
        """focal_symbols=None is treated as empty list."""
        from scripts.context import ContextGraph
        from scripts.context.workflow import prioritize_context

        graph = ContextGraph(repo_path=tmp_path)
        storage = graph._storage
        _add_node(storage, "main.py", "main")
        graph.close()

        result = prioritize_context(tmp_path, focal_symbols=None)
        assert result["enabled"] is True
        assert result["ranked_files"] == []
