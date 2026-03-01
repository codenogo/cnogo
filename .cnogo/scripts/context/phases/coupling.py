"""Coupling analysis phase using Jaccard similarity of shared neighbors.

Identifies structurally coupled symbol pairs by computing the Jaccard
similarity of their neighbor sets (callers + callees + importers + imports)
from the code graph. Pairs above a threshold get COUPLED_WITH relationships.
"""
from __future__ import annotations

from dataclasses import dataclass

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage

# Edge types used to build neighbor sets
_NEIGHBOR_EDGE_TYPES = [RelType.CALLS.value, RelType.IMPORTS.value]

# Symbol node labels considered for coupling analysis
_SYMBOL_LABELS = {NodeLabel.FUNCTION.value, NodeLabel.CLASS.value, NodeLabel.METHOD.value}


@dataclass
class CouplingResult:
    """A single coupling pair result."""

    source_id: str
    source_name: str
    target_id: str
    target_name: str
    strength: float    # Jaccard similarity of shared neighbors
    shared_count: int  # number of shared neighbors


def _query_symbol_nodes(storage: GraphStorage) -> list[tuple[str, str]]:
    """Return (node_id, name) for all function/class/method nodes."""
    conn = storage._require_conn()
    labels_list = ", ".join(f"'{lbl}'" for lbl in _SYMBOL_LABELS)
    result = conn.execute(
        f"MATCH (n:GraphNode) WHERE n.label IN [{labels_list}] RETURN n.id, n.name"
    )
    nodes: list[tuple[str, str]] = []
    while result.has_next():
        row = result.get_next()
        nodes.append((row[0], row[1]))
    return nodes


def _build_neighbor_sets(
    storage: GraphStorage, node_ids: list[str]
) -> dict[str, set[str]]:
    """Build neighbor sets for each node_id using CALLS and IMPORTS edges."""
    # Fetch all relevant edges at once
    edges = storage.get_all_relationships_by_types(_NEIGHBOR_EDGE_TYPES)

    node_id_set = set(node_ids)

    # For each symbol node, collect both incoming and outgoing neighbors
    neighbors: dict[str, set[str]] = {nid: set() for nid in node_ids}

    for src, tgt, _rtype in edges:
        if src in node_id_set:
            neighbors[src].add(tgt)
        if tgt in node_id_set:
            neighbors[tgt].add(src)

    return neighbors


def compute_coupling(
    storage: GraphStorage,
    threshold: float = 0.1,
) -> list[CouplingResult]:
    """Compute structural coupling between symbol pairs using Jaccard similarity.

    1. Query all symbol nodes (function, class, method).
    2. For each pair, compute Jaccard similarity of their neighbor sets.
    3. Create COUPLED_WITH relationships for pairs above threshold.
    4. Return list of CouplingResult sorted by strength descending.
    """
    symbol_nodes = _query_symbol_nodes(storage)

    if len(symbol_nodes) < 2:
        return []

    node_ids = [nid for nid, _name in symbol_nodes]
    name_map = {nid: name for nid, name in symbol_nodes}

    neighbor_sets = _build_neighbor_sets(storage, node_ids)

    results: list[CouplingResult] = []
    coupled_rels: list[GraphRelationship] = []

    # Use canonical ordering to avoid duplicate pairs
    for i in range(len(node_ids)):
        for j in range(i + 1, len(node_ids)):
            a_id = node_ids[i]
            b_id = node_ids[j]

            # Skip self-coupling (should never happen with i < j but be safe)
            if a_id == b_id:
                continue

            nb_a = neighbor_sets[a_id]
            nb_b = neighbor_sets[b_id]

            intersection = nb_a & nb_b
            union = nb_a | nb_b

            if not union or not intersection:
                continue

            jaccard = len(intersection) / len(union)
            shared = len(intersection)

            if jaccard < threshold:
                continue

            # Canonical ordering by sorted IDs
            if a_id > b_id:
                a_id, b_id = b_id, a_id

            a_name = name_map[a_id]
            b_name = name_map[b_id]

            results.append(CouplingResult(
                source_id=a_id,
                source_name=a_name,
                target_id=b_id,
                target_name=b_name,
                strength=jaccard,
                shared_count=shared,
            ))

            coupled_rels.append(GraphRelationship(
                id=f"coupled:{a_id}->{b_id}",
                type=RelType.COUPLED_WITH,
                source=a_id,
                target=b_id,
                properties={
                    "structural_score": jaccard,
                    "temporal_score": 0.0,
                    "combined_score": jaccard,
                    "shared_count": shared,
                },
            ))

    if coupled_rels:
        storage.add_relationships(coupled_rels)

    results.sort(key=lambda r: -r.strength)
    return results
