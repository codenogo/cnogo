"""Community detection phase via label propagation.

Detects tightly-coupled module clusters by propagating labels through
the graph until convergence. Creates COMMUNITY nodes with MEMBER_OF edges.

Algorithm:
1. Bulk query relationship edges (CALLS, IMPORTS, COUPLED_WITH, etc.)
2. Build undirected adjacency dict
3. Initialize each node with its own label
4. Iterate: each node adopts most common neighbor label (ties → smallest)
5. Group nodes by final label, filter by min_size
6. Persist COMMUNITY nodes and MEMBER_OF edges

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage

_DEFAULT_EDGE_TYPES = [
    RelType.CALLS.value,
    RelType.IMPORTS.value,
    RelType.COUPLED_WITH.value,
    RelType.EXTENDS.value,
    RelType.IMPLEMENTS.value,
]

_MAX_ITERATIONS = 100


@dataclass
class CommunityInfo:
    """A detected community (cluster of related symbols)."""

    community_id: str
    members: list[str]
    member_names: list[str]
    size: int


@dataclass
class CommunityDetectionResult:
    """Result of community detection across the graph."""

    communities: list[CommunityInfo]
    total_nodes: int
    num_communities: int


def detect_communities(
    storage: GraphStorage,
    edge_types: list[str] | None = None,
    min_size: int = 2,
) -> CommunityDetectionResult:
    """Detect communities via label propagation.

    Args:
        storage: Initialized GraphStorage with indexed nodes/relationships.
        edge_types: Relationship types to use for adjacency. Defaults to
            CALLS, IMPORTS, COUPLED_WITH, EXTENDS, IMPLEMENTS.
        min_size: Minimum community size to include in results.

    Returns:
        CommunityDetectionResult with detected communities.
    """
    types = edge_types if edge_types is not None else _DEFAULT_EDGE_TYPES

    # 1. Bulk load edges
    edges = storage.get_all_relationships_by_types(types)
    if not edges:
        return CommunityDetectionResult(communities=[], total_nodes=0, num_communities=0)

    # 2. Build undirected adjacency
    adj: dict[str, set[str]] = defaultdict(set)
    for source, target, _rtype in edges:
        adj[source].add(target)
        adj[target].add(source)

    # 3. Filter to symbol nodes only
    symbol_nodes = storage.get_all_symbol_nodes()
    symbol_ids = {n.id for n in symbol_nodes}
    symbol_name_map = {n.id: n.name for n in symbol_nodes}

    # Only keep nodes that are symbols and have edges
    active_nodes = sorted(symbol_ids & set(adj.keys()))
    if not active_nodes:
        return CommunityDetectionResult(communities=[], total_nodes=0, num_communities=0)

    # 4. Initialize labels: each node gets its own label
    labels: dict[str, str] = {nid: nid for nid in active_nodes}

    # 5. Iterate until convergence
    for _ in range(_MAX_ITERATIONS):
        changed = False
        for nid in active_nodes:
            neighbor_labels = []
            for nbr in adj[nid]:
                if nbr in labels:
                    neighbor_labels.append(labels[nbr])
            if not neighbor_labels:
                continue

            # Most common label; break ties by smallest label value
            counts = Counter(neighbor_labels)
            max_count = max(counts.values())
            candidates = [lbl for lbl, cnt in counts.items() if cnt == max_count]
            best = min(candidates)

            if labels[nid] != best:
                labels[nid] = best
                changed = True

        if not changed:
            break

    # 6. Group by final label
    groups: dict[str, list[str]] = defaultdict(list)
    for nid, lbl in labels.items():
        groups[lbl].append(nid)

    # 7. Filter by min_size and build results
    communities: list[CommunityInfo] = []
    new_nodes: list[GraphNode] = []
    new_edges: list[GraphRelationship] = []

    for idx, (lbl, members) in enumerate(sorted(groups.items())):
        if len(members) < min_size:
            continue

        community_id = f"community:{idx}"
        member_names = [symbol_name_map.get(m, m) for m in sorted(members)]

        communities.append(CommunityInfo(
            community_id=community_id,
            members=sorted(members),
            member_names=member_names,
            size=len(members),
        ))

        # Persist COMMUNITY node
        new_nodes.append(GraphNode(
            id=community_id,
            label=NodeLabel.COMMUNITY,
            name=f"community-{idx}",
            properties={"size": len(members)},
        ))

        # Persist MEMBER_OF edges
        for member_id in sorted(members):
            new_edges.append(GraphRelationship(
                id=f"member_of:{member_id}->{community_id}",
                type=RelType.MEMBER_OF,
                source=member_id,
                target=community_id,
            ))

    # 8. Persist to storage
    if new_nodes:
        storage.add_nodes(new_nodes)
    if new_edges:
        storage.add_relationships(new_edges)

    return CommunityDetectionResult(
        communities=communities,
        total_nodes=len(active_nodes),
        num_communities=len(communities),
    )
