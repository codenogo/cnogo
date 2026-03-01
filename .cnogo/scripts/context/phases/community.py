"""Community detection phase using Leiden algorithm.

Builds an igraph.Graph from CALLS/IMPORTS/EXTENDS edges stored in KuzuDB,
runs leidenalg.find_partition with ModularityVertexPartition, and persists
COMMUNITY nodes with MEMBER_OF relationships back to storage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import igraph
import leidenalg

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.storage import GraphStorage

_EDGE_TYPES = [RelType.CALLS.value, RelType.IMPORTS.value, RelType.EXTENDS.value]


@dataclass
class CommunityInfo:
    """Summary of a single detected community."""

    community_id: str
    members: list[str]
    member_names: list[str]
    size: int


@dataclass
class CommunityDetectionResult:
    """Result of running Leiden community detection."""

    communities: list[CommunityInfo]
    total_nodes: int
    num_communities: int


def _query_edges(storage: GraphStorage) -> list[tuple[str, str, str]]:
    """Return all (source_id, target_id, rel_type) for CALLS/IMPORTS/EXTENDS."""
    conn = storage._require_conn()
    types_list = ", ".join(f"'{t}'" for t in _EDGE_TYPES)
    result = conn.execute(
        f"MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) "
        f"WHERE r.rel_type IN [{types_list}] "
        f"RETURN a.id, b.id, r.rel_type"
    )
    edges: list[tuple[str, str, str]] = []
    while result.has_next():
        row = result.get_next()
        edges.append((row[0], row[1], row[2]))
    return edges


def _query_node_name(storage: GraphStorage, node_id: str) -> str:
    """Return the name for a node_id, or the node_id itself as fallback."""
    node = storage.get_node(node_id)
    if node is not None:
        return node.name
    return node_id


def detect_communities(
    storage: GraphStorage,
    min_size: int = 1,
) -> CommunityDetectionResult:
    """Run Leiden community detection on the code graph.

    1. Query storage for all CALLS/IMPORTS/EXTENDS relationships.
    2. Build igraph.Graph from those edges (nodes = unique node IDs).
    3. Run leidenalg.find_partition with ModularityVertexPartition.
    4. Filter communities by min_size.
    5. Create COMMUNITY nodes and MEMBER_OF relationships in storage.
    6. Return CommunityDetectionResult.
    """
    edges = _query_edges(storage)

    if not edges:
        return CommunityDetectionResult(communities=[], total_nodes=0, num_communities=0)

    # Collect unique node IDs preserving insertion order for determinism
    node_set: dict[str, int] = {}
    for src, tgt, _ in edges:
        if src not in node_set:
            node_set[src] = len(node_set)
        if tgt not in node_set:
            node_set[tgt] = len(node_set)

    n = len(node_set)
    igraph_edges = [(node_set[src], node_set[tgt]) for src, tgt, _ in edges]

    graph = igraph.Graph(n=n, edges=igraph_edges, directed=False)

    # Run Leiden with a fixed seed for determinism
    partition = leidenalg.find_partition(
        graph,
        leidenalg.ModularityVertexPartition,
        seed=42,
    )

    # Map vertex index back to node_id
    idx_to_node = {v: k for k, v in node_set.items()}

    community_infos: list[CommunityInfo] = []
    community_nodes: list[GraphNode] = []
    member_of_rels: list[GraphRelationship] = []

    for i, membership in enumerate(partition):
        member_node_ids = [idx_to_node[v] for v in membership]
        if len(member_node_ids) < min_size:
            continue

        community_id = generate_id(NodeLabel.COMMUNITY, "", f"community_{i}")
        member_names = [_query_node_name(storage, nid) for nid in member_node_ids]

        info = CommunityInfo(
            community_id=community_id,
            members=sorted(member_node_ids),
            member_names=member_names,
            size=len(member_node_ids),
        )
        community_infos.append(info)

        community_nodes.append(
            GraphNode(
                id=community_id,
                label=NodeLabel.COMMUNITY,
                name=f"community_{i}",
            )
        )

        for member_id in member_node_ids:
            rel_id = f"member_of:{member_id}->{community_id}"
            member_of_rels.append(
                GraphRelationship(
                    id=rel_id,
                    type=RelType.MEMBER_OF,
                    source=member_id,
                    target=community_id,
                )
            )

    if community_nodes:
        storage.add_nodes(community_nodes)
    if member_of_rels:
        storage.add_relationships(member_of_rels)

    return CommunityDetectionResult(
        communities=community_infos,
        total_nodes=n,
        num_communities=len(community_infos),
    )
