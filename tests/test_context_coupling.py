"""Tests for coupling detection phase."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmp:
        s = GraphStorage(Path(tmp) / "test.db")
        s.initialize()
        yield s
        s.close()


def _add_function(storage, name, file_path="a.py"):
    nid = f"function:{file_path}:{name}"
    storage.add_nodes([GraphNode(
        id=nid, label=NodeLabel.FUNCTION, name=name, file_path=file_path,
    )])
    return nid


def _add_call_edge(storage, source_id, target_id):
    rid = f"calls:{source_id}->{target_id}"
    storage.add_relationships([GraphRelationship(
        id=rid, type=RelType.CALLS, source=source_id, target=target_id,
    )])


def _add_import_edge(storage, source_id, target_id):
    rid = f"imports:{source_id}->{target_id}"
    storage.add_relationships([GraphRelationship(
        id=rid, type=RelType.IMPORTS, source=source_id, target=target_id,
    )])


# --- CouplingResult dataclass ---


def test_coupling_result_fields():
    from scripts.context.phases.coupling import CouplingResult
    r = CouplingResult(
        source_id="fn:a", source_name="a",
        target_id="fn:b", target_name="b",
        strength=0.75, shared_count=3,
    )
    assert r.source_id == "fn:a"
    assert r.source_name == "a"
    assert r.target_id == "fn:b"
    assert r.target_name == "b"
    assert r.strength == 0.75
    assert r.shared_count == 3


# --- compute_coupling: basic cases ---


def test_coupled_pair_above_threshold(storage):
    """Two functions calling the same two targets should be coupled."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    shared1 = _add_function(storage, "shared1")
    shared2 = _add_function(storage, "shared2")

    _add_call_edge(storage, a, shared1)
    _add_call_edge(storage, a, shared2)
    _add_call_edge(storage, b, shared1)
    _add_call_edge(storage, b, shared2)

    results = compute_coupling(storage, threshold=0.5)
    assert len(results) >= 1
    # Find the (a, b) pair in results
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"a", "b"}]
    assert len(ab_pairs) == 1
    pair = ab_pairs[0]
    assert pair.strength == 1.0  # Identical neighbor sets
    assert pair.shared_count == 2


def test_unreferenced_pair_not_coupled(storage):
    """Two functions with no shared neighbors should not be coupled."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    t1 = _add_function(storage, "target1")
    t2 = _add_function(storage, "target2")

    _add_call_edge(storage, a, t1)
    _add_call_edge(storage, b, t2)

    results = compute_coupling(storage, threshold=0.5)
    assert len(results) == 0


def test_pair_below_threshold_excluded(storage):
    """Pair with low Jaccard similarity should be excluded by threshold."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    shared = _add_function(storage, "shared")
    only_a1 = _add_function(storage, "only_a1")
    only_a2 = _add_function(storage, "only_a2")
    only_a3 = _add_function(storage, "only_a3")

    # a calls shared + 3 unique → neighbors(a) = {shared, only_a1, only_a2, only_a3}
    _add_call_edge(storage, a, shared)
    _add_call_edge(storage, a, only_a1)
    _add_call_edge(storage, a, only_a2)
    _add_call_edge(storage, a, only_a3)
    # b calls shared only → neighbors(b) = {shared, a} (bidirectional)
    # But a has neighbors {shared, only_a1, only_a2, only_a3, b}
    # Jaccard(a,b) is low, so (a,b) pair should not appear
    _add_call_edge(storage, b, shared)

    results = compute_coupling(storage, threshold=0.5)
    ab_pairs = [r for r in results if {r.source_name, r.target_name} == {"a", "b"}]
    assert len(ab_pairs) == 0


def test_self_coupling_excluded(storage):
    """A symbol should never be coupled with itself."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    shared = _add_function(storage, "shared")
    _add_call_edge(storage, a, shared)

    results = compute_coupling(storage, threshold=0.0)
    # No result should have source == target
    for r in results:
        assert r.source_id != r.target_id


# --- compute_coupling: edge cases ---


def test_empty_graph(storage):
    """Empty graph should return no coupling results."""
    from scripts.context.phases.coupling import compute_coupling
    results = compute_coupling(storage, threshold=0.5)
    assert results == []


def test_single_node(storage):
    """Graph with single node should return no coupling."""
    from scripts.context.phases.coupling import compute_coupling
    _add_function(storage, "solo")
    results = compute_coupling(storage, threshold=0.5)
    assert results == []


def test_disjoint_components(storage):
    """Symbols in disjoint components should not be coupled."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    t1 = _add_function(storage, "t1")
    t2 = _add_function(storage, "t2")

    _add_call_edge(storage, a, t1)
    _add_call_edge(storage, b, t2)

    results = compute_coupling(storage, threshold=0.0)
    # a and b share no neighbors
    for r in results:
        names = {r.source_name, r.target_name}
        assert names != {"a", "b"}


def test_bidirectional_symmetry(storage):
    """Coupling should be symmetric: (A,B) strength == (B,A) strength."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    shared = _add_function(storage, "shared")

    _add_call_edge(storage, a, shared)
    _add_call_edge(storage, b, shared)

    results = compute_coupling(storage, threshold=0.0)
    # Should produce exactly one result (not two symmetric entries)
    coupled = [r for r in results if {r.source_name, r.target_name} == {"a", "b"}]
    assert len(coupled) == 1


def test_coupling_creates_coupled_with_edges(storage):
    """compute_coupling should create COUPLED_WITH edges in storage."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    shared = _add_function(storage, "shared")

    _add_call_edge(storage, a, shared)
    _add_call_edge(storage, b, shared)

    compute_coupling(storage, threshold=0.5)

    # Verify COUPLED_WITH edge was created
    edges = storage.get_all_relationships_by_types([RelType.COUPLED_WITH.value])
    assert len(edges) == 1
    edge_nodes = {edges[0][0], edges[0][1]}
    assert edge_nodes == {a, b}


def test_coupling_sorted_by_strength(storage):
    """Results should be sorted by strength descending."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    c = _add_function(storage, "c")
    s1 = _add_function(storage, "s1")
    s2 = _add_function(storage, "s2")

    # a and b share both s1 and s2 → Jaccard = 1.0
    _add_call_edge(storage, a, s1)
    _add_call_edge(storage, a, s2)
    _add_call_edge(storage, b, s1)
    _add_call_edge(storage, b, s2)
    # c shares only s1 with a → Jaccard = 1/2 = 0.5
    _add_call_edge(storage, c, s1)

    results = compute_coupling(storage, threshold=0.5)
    assert len(results) >= 2
    assert results[0].strength >= results[1].strength


def test_coupling_via_imports(storage):
    """Coupling should also consider IMPORTS edges."""
    from scripts.context.phases.coupling import compute_coupling

    a = _add_function(storage, "a")
    b = _add_function(storage, "b")
    shared = _add_function(storage, "shared")

    _add_import_edge(storage, a, shared)
    _add_import_edge(storage, b, shared)

    results = compute_coupling(storage, threshold=0.5)
    assert len(results) >= 1
    pair = results[0]
    names = {pair.source_name, pair.target_name}
    assert names == {"a", "b"}
