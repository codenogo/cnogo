"""Impact analysis phase (BFS blast radius).

Given a file path, finds all symbols defined in that file, then BFS outward
through reverse CALLS, IMPORTS, and EXTENDS edges to determine the blast
radius of a change.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from scripts.context.model import GraphNode, NodeLabel, RelType
from scripts.context.storage import GraphStorage


@dataclass
class ImpactResult:
    """A node impacted by a change, with distance and edge type."""

    node: GraphNode
    depth: int
    edge_type: str


def impact_analysis(
    storage: GraphStorage,
    file_path: str,
    max_depth: int = 3,
) -> list[ImpactResult]:
    """BFS blast radius from all symbols in a file.

    Traverses reverse CALLS, reverse IMPORTS, and reverse EXTENDS edges
    to find nodes impacted by changes to the given file.

    Args:
        storage: Graph storage with indexed nodes/relationships.
        file_path: Path of the file being changed.
        max_depth: Maximum BFS depth (default 3). 0 returns empty.

    Returns:
        List of ImpactResult sorted by depth ascending, then name ascending.
    """
    if max_depth <= 0:
        return []

    assert storage._conn is not None

    # Collect seed node IDs: all symbols defined in the target file,
    # plus the FILE node itself
    seed_ids: set[str] = set()
    cur = storage._conn.execute(
        "SELECT id FROM nodes WHERE file_path = ?", (file_path,)
    )
    for (node_id,) in cur.fetchall():
        seed_ids.add(node_id)

    if not seed_ids:
        return []

    # BFS outward via reverse edges
    visited: set[str] = set(seed_ids)
    queue: deque[tuple[str, int, str]] = deque()
    results: list[ImpactResult] = []

    # Reverse edge types to traverse: who calls/imports/extends our symbols
    reverse_edge_types = [
        RelType.CALLS.value,
        RelType.IMPORTS.value,
        RelType.EXTENDS.value,
        RelType.IMPLEMENTS.value,
    ]

    # Seed the queue with direct reverse neighbors at depth 1
    for seed_id in seed_ids:
        for edge_type in reverse_edge_types:
            cur = storage._conn.execute(
                "SELECT source FROM relationships WHERE target = ? AND type = ?",
                (seed_id, edge_type),
            )
            for (source_id,) in cur.fetchall():
                if source_id not in visited:
                    visited.add(source_id)
                    queue.append((source_id, 1, edge_type))

    # BFS
    while queue:
        node_id, depth, edge_type = queue.popleft()

        node = storage.get_node(node_id)
        if node is not None:
            results.append(ImpactResult(node=node, depth=depth, edge_type=edge_type))

        if depth < max_depth:
            for et in reverse_edge_types:
                cur = storage._conn.execute(
                    "SELECT source FROM relationships WHERE target = ? AND type = ?",
                    (node_id, et),
                )
                for (source_id,) in cur.fetchall():
                    if source_id not in visited:
                        visited.add(source_id)
                        queue.append((source_id, depth + 1, et))

    # Sort by depth ascending, then name ascending
    results.sort(key=lambda r: (r.depth, r.node.name))
    return results
