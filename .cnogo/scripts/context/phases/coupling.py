"""Coupling detection phase.

Computes structural coupling between symbols via shared call/import neighbors
using Jaccard similarity. Creates COUPLED_WITH edges for pairs above threshold.

Algorithm:
1. Bulk query all CALLS + IMPORTS edges
2. Build neighbor sets per symbol node
3. Use inverted index (neighbor → symbols) to find pairs sharing neighbors
4. Compute Jaccard similarity = |A∩B| / |A∪B|
5. Create COUPLED_WITH edges for pairs above threshold

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from scripts.context.model import GraphRelationship, RelType
from scripts.context.storage import GraphStorage

_COUPLING_EDGE_TYPES = [
    RelType.CALLS.value,
    RelType.IMPORTS.value,
]


@dataclass
class CouplingResult:
    """A pair of symbols with structural coupling."""

    source_id: str
    source_name: str
    target_id: str
    target_name: str
    strength: float
    shared_count: int


def compute_coupling(
    storage: GraphStorage, threshold: float = 0.5
) -> list[CouplingResult]:
    """Compute structural coupling between symbols via Jaccard similarity.

    Args:
        storage: Initialized GraphStorage with indexed nodes/relationships.
        threshold: Minimum Jaccard similarity to create a COUPLED_WITH edge.

    Returns:
        List of CouplingResult sorted by strength descending.
    """
    # 1. Bulk query all CALLS + IMPORTS edges
    edges = storage.get_all_relationships_by_types(_COUPLING_EDGE_TYPES)
    if not edges:
        return []

    # 2. Build neighbor sets per node (both source and target sides)
    neighbors: dict[str, set[str]] = defaultdict(set)
    for source, target, _rtype in edges:
        neighbors[source].add(target)
        neighbors[target].add(source)

    # 3. Filter to symbol nodes only
    symbol_nodes = storage.get_all_symbol_nodes()
    symbol_ids = {n.id for n in symbol_nodes}
    symbol_name_map = {n.id: n.name for n in symbol_nodes}

    # Only keep neighbors for symbol nodes
    symbol_neighbors: dict[str, set[str]] = {
        nid: neighbors[nid] for nid in symbol_ids if nid in neighbors
    }

    if not symbol_neighbors:
        return []

    # 4. Build inverted index: neighbor → set of symbols that have it
    inverted: dict[str, set[str]] = defaultdict(set)
    for sym_id, nbrs in symbol_neighbors.items():
        for nbr in nbrs:
            inverted[nbr].add(sym_id)

    # 5. Find pairs sharing at least one neighbor and compute Jaccard
    seen_pairs: set[tuple[str, str]] = set()
    results: list[CouplingResult] = []
    new_edges: list[GraphRelationship] = []

    for _nbr, syms in inverted.items():
        sym_list = sorted(syms)  # deterministic ordering
        for i in range(len(sym_list)):
            for j in range(i + 1, len(sym_list)):
                a, b = sym_list[i], sym_list[j]
                pair_key = (a, b)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                set_a = symbol_neighbors[a]
                set_b = symbol_neighbors[b]
                intersection = set_a & set_b
                union = set_a | set_b
                jaccard = len(intersection) / len(union) if union else 0.0

                if jaccard >= threshold:
                    results.append(CouplingResult(
                        source_id=a,
                        source_name=symbol_name_map[a],
                        target_id=b,
                        target_name=symbol_name_map[b],
                        strength=round(jaccard, 4),
                        shared_count=len(intersection),
                    ))
                    new_edges.append(GraphRelationship(
                        id=f"coupled:{a}<->{b}",
                        type=RelType.COUPLED_WITH,
                        source=a,
                        target=b,
                        properties={"strength": round(jaccard, 4), "shared_count": len(intersection)},
                    ))

    # 6. Persist COUPLED_WITH edges
    if new_edges:
        storage.add_relationships(new_edges)

    # Sort by strength descending
    results.sort(key=lambda r: r.strength, reverse=True)
    return results
