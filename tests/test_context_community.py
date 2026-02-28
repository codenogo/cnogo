"""Tests for community detection phase (label propagation)."""

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


# --- CommunityInfo / CommunityDetectionResult dataclass ---


def test_community_info_fields():
    from scripts.context.phases.community import CommunityInfo
    c = CommunityInfo(
        community_id="community:0",
        members=["fn:a", "fn:b"],
        member_names=["a", "b"],
        size=2,
    )
    assert c.community_id == "community:0"
    assert c.members == ["fn:a", "fn:b"]
    assert c.member_names == ["a", "b"]
    assert c.size == 2


def test_community_detection_result_fields():
    from scripts.context.phases.community import CommunityDetectionResult, CommunityInfo
    r = CommunityDetectionResult(
        communities=[CommunityInfo("c:0", ["a"], ["a"], 1)],
        total_nodes=1,
        num_communities=1,
    )
    assert r.total_nodes == 1
    assert r.num_communities == 1
    assert len(r.communities) == 1


# --- detect_communities ---


def test_empty_graph_returns_empty(storage):
    """Empty graph (no edges) should produce empty result."""
    from scripts.context.phases.community import detect_communities
    result = detect_communities(storage)
    assert result.communities == []
    assert result.total_nodes == 0
    assert result.num_communities == 0


def test_single_component_produces_one_community(storage):
    """Three connected functions should form a single community."""
    from scripts.context.phases.community import detect_communities

    a = _add_function(storage, "func_a", "a.py")
    b = _add_function(storage, "func_b", "b.py")
    c = _add_function(storage, "func_c", "c.py")

    # a -> b -> c, forming a chain
    _add_call_edge(storage, a, b)
    _add_call_edge(storage, b, c)

    result = detect_communities(storage, min_size=2)
    assert result.num_communities == 1
    assert result.total_nodes == 3

    community = result.communities[0]
    assert community.size == 3
    assert set(community.members) == {a, b, c}


def test_two_disconnected_components_produce_two_communities(storage):
    """Two separate clusters should produce two communities."""
    from scripts.context.phases.community import detect_communities

    # Cluster 1: a <-> b
    a = _add_function(storage, "func_a", "a.py")
    b = _add_function(storage, "func_b", "b.py")
    _add_call_edge(storage, a, b)
    _add_call_edge(storage, b, a)

    # Cluster 2: c <-> d
    c = _add_function(storage, "func_c", "c.py")
    d = _add_function(storage, "func_d", "d.py")
    _add_call_edge(storage, c, d)
    _add_call_edge(storage, d, c)

    result = detect_communities(storage, min_size=2)
    assert result.num_communities == 2
    assert result.total_nodes == 4

    sizes = sorted(cm.size for cm in result.communities)
    assert sizes == [2, 2]


def test_deterministic_across_runs(storage):
    """Same graph should produce same communities every run."""
    from scripts.context.phases.community import detect_communities

    a = _add_function(storage, "func_a", "a.py")
    b = _add_function(storage, "func_b", "b.py")
    c = _add_function(storage, "func_c", "c.py")
    _add_call_edge(storage, a, b)
    _add_call_edge(storage, b, c)

    result1 = detect_communities(storage, min_size=2)
    result2 = detect_communities(storage, min_size=2)

    assert result1.num_communities == result2.num_communities
    for c1, c2 in zip(result1.communities, result2.communities):
        assert c1.members == c2.members


def test_min_size_filters_small_groups(storage):
    """Nodes in groups smaller than min_size should be excluded."""
    from scripts.context.phases.community import detect_communities

    # Cluster of 3
    a = _add_function(storage, "func_a", "a.py")
    b = _add_function(storage, "func_b", "b.py")
    c = _add_function(storage, "func_c", "c.py")
    _add_call_edge(storage, a, b)
    _add_call_edge(storage, b, c)
    _add_call_edge(storage, a, c)

    # Isolated pair
    d = _add_function(storage, "func_d", "d.py")
    e = _add_function(storage, "func_e", "e.py")
    _add_call_edge(storage, d, e)

    # min_size=3 should only include the cluster of 3
    result = detect_communities(storage, min_size=3)
    assert result.num_communities == 1
    assert result.communities[0].size == 3


def test_persists_community_nodes_and_member_of_edges(storage):
    """detect_communities should create COMMUNITY nodes and MEMBER_OF edges."""
    from scripts.context.phases.community import detect_communities

    a = _add_function(storage, "func_a", "a.py")
    b = _add_function(storage, "func_b", "b.py")
    _add_call_edge(storage, a, b)
    _add_call_edge(storage, b, a)

    detect_communities(storage, min_size=2)

    # Check MEMBER_OF edges exist
    member_edges = storage.get_all_relationships_by_types([RelType.MEMBER_OF.value])
    assert len(member_edges) == 2  # a and b are members
