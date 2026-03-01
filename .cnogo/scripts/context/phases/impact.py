"""Impact analysis phase.

BFS blast radius from all symbols in a changed file via incoming edges.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from scripts.context.model import NodeLabel, RelType
from scripts.context.storage import GraphStorage


@dataclass
class ImpactResult:
    node: object  # GraphNode
    depth: int


def impact_analysis(
    storage: GraphStorage,
    file_path: str,
    max_depth: int = 5,
) -> list[ImpactResult]:
    """BFS blast radius from all symbols in a changed file.

    1. Get all symbol nodes in the target file (by file_path)
    2. BFS backwards through INCOMING CALLS/IMPORTS/EXTENDS edges
    3. Exclude nodes that belong to the target file itself
    4. Track depth for each discovered node
    5. Sort results by (depth ASC, name ASC)

    Returns list of ImpactResult.
    """
    if max_depth == 0:
        return []

    # Get all nodes in the target file (symbols + file nodes)
    file_nodes = storage.get_nodes_by_file(file_path)
    if not file_nodes:
        return []

    # Seed BFS with all node IDs in the target file
    seed_ids: set[str] = {n.id for n in file_nodes}
    if not seed_ids:
        return []

    # Build reverse edge map: target_id -> list[source_id]
    # for CALLS, IMPORTS, EXTENDS edges
    incoming_rel_types = [
        RelType.CALLS.value,
        RelType.IMPORTS.value,
        RelType.EXTENDS.value,
    ]
    all_rels = storage.get_all_relationships_by_types(incoming_rel_types)

    # reverse_map: target_id -> list[source_id]
    reverse_map: dict[str, list[str]] = {}
    for src, tgt, _ in all_rels:
        reverse_map.setdefault(tgt, []).append(src)

    # BFS backward from seed nodes
    visited: set[str] = set(seed_ids)
    queue: deque[tuple[str, int]] = deque()

    for seed_id in seed_ids:
        for src_id in reverse_map.get(seed_id, []):
            if src_id not in visited:
                visited.add(src_id)
                queue.append((src_id, 1))

    results_map: dict[str, int] = {}  # node_id -> depth

    while queue:
        node_id, depth = queue.popleft()
        if depth > max_depth:
            continue

        # Fetch node to check file_path
        node = storage.get_node(node_id)
        if node is None:
            continue

        # Exclude nodes in the target file
        if node.file_path == file_path:
            continue

        # Record (keep minimum depth if already seen)
        if node_id not in results_map:
            results_map[node_id] = depth

            if depth < max_depth:
                for src_id in reverse_map.get(node_id, []):
                    if src_id not in visited:
                        visited.add(src_id)
                        queue.append((src_id, depth + 1))

    if not results_map:
        return []

    # Fetch all impacted nodes
    results: list[ImpactResult] = []
    for node_id, depth in results_map.items():
        node = storage.get_node(node_id)
        if node is not None:
            results.append(ImpactResult(node=node, depth=depth))

    # Sort by depth ASC, then name ASC
    results.sort(key=lambda r: (r.depth, r.node.name))
    return results
