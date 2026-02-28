"""Graph proximity ranking phase.

BFS-based file proximity ranking from a set of focal node IDs.
Traverses CALLS, IMPORTS, EXTENDS, USES_TYPE edges in both directions
to compute minimum graph distance per file.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from collections import deque

from scripts.context.model import RelType
from scripts.context.storage import GraphStorage

# Edge types traversed for proximity ranking
_PROXIMITY_EDGE_TYPES = [
    RelType.CALLS,
    RelType.IMPORTS,
    RelType.EXTENDS,
    RelType.USES_TYPE,
]


def rank_by_proximity(
    storage: GraphStorage,
    focal_node_ids: list[str],
    max_depth: int = 5,
) -> list[dict]:
    """Rank files by minimum graph distance from focal nodes.

    BFS traverses CALLS, IMPORTS, EXTENDS, USES_TYPE edges in both
    directions. Groups results by file_path, taking the minimum distance
    per file. The focal nodes' own files are excluded (distance 0).

    Args:
        storage: Graph storage with indexed nodes/relationships.
        focal_node_ids: Seed node IDs to start BFS from.
        max_depth: Maximum BFS depth (default 5).

    Returns:
        List of dicts sorted by min_distance ascending:
            {
                "file_path": str,
                "min_distance": int,
                "connected_symbols": [list of symbol names at min_distance],
            }
    """
    if not focal_node_ids or max_depth <= 0:
        return []

    assert storage._conn is not None

    # Collect focal node file paths to exclude from results
    focal_files: set[str] = set()
    for node_id in focal_node_ids:
        node = storage.get_node(node_id)
        if node is not None and node.file_path:
            focal_files.add(node.file_path)

    # BFS: track min distance per node
    visited: dict[str, int] = {}  # node_id -> distance
    queue: deque[tuple[str, int]] = deque()

    for node_id in focal_node_ids:
        if node_id not in visited:
            visited[node_id] = 0
            queue.append((node_id, 0))

    # file_path -> (min_distance, set of symbol names at that distance)
    file_distances: dict[str, tuple[int, set[str]]] = {}

    while queue:
        node_id, depth = queue.popleft()

        # Record this node's file contribution (skip focal nodes at depth 0)
        if depth > 0:
            node = storage.get_node(node_id)
            if node is not None and node.file_path and node.file_path not in focal_files:
                fp = node.file_path
                if fp not in file_distances or depth < file_distances[fp][0]:
                    file_distances[fp] = (depth, {node.name})
                elif depth == file_distances[fp][0]:
                    file_distances[fp][1].add(node.name)

        if depth >= max_depth:
            continue

        # Traverse all proximity edge types in both directions
        for rel_type in _PROXIMITY_EDGE_TYPES:
            # Outgoing: node_id is source, get targets
            cur = storage._conn.execute(
                "SELECT target FROM relationships WHERE source = ? AND type = ?",
                (node_id, rel_type.value),
            )
            for (neighbor_id,) in cur.fetchall():
                if neighbor_id not in visited:
                    visited[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))

            # Incoming: node_id is target, get sources
            cur = storage._conn.execute(
                "SELECT source FROM relationships WHERE target = ? AND type = ?",
                (node_id, rel_type.value),
            )
            for (neighbor_id,) in cur.fetchall():
                if neighbor_id not in visited:
                    visited[neighbor_id] = depth + 1
                    queue.append((neighbor_id, depth + 1))

    # Build result list
    results = []
    for file_path, (min_dist, symbols) in file_distances.items():
        results.append({
            "file_path": file_path,
            "min_distance": min_dist,
            "connected_symbols": sorted(symbols),
        })

    # Sort by min_distance ascending
    results.sort(key=lambda r: r["min_distance"])
    return results
