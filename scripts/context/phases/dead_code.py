"""Dead code detection phase.

A symbol is dead if it has no incoming CALLS, IMPORTS, EXTENDS, or IMPLEMENTS
edges and is not an entry point.

Entry point heuristics:
- Functions named ``main`` → entry point
- Functions/classes with ``test_`` or ``Test`` prefix → entry point
- Any symbol in an ``__init__.py`` file → entry point (exported)
- Any symbol already flagged is_entry_point in storage → entry point

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.context.model import NodeLabel, RelType
from scripts.context.storage import GraphStorage

# Relationship types whose incoming edges keep a node alive
_INCOMING_LIVE_EDGE_TYPES = (
    RelType.CALLS.value,
    RelType.IMPORTS.value,
    RelType.EXTENDS.value,
    RelType.IMPLEMENTS.value,
)


@dataclass
class DeadCodeResult:
    """A symbol identified as dead (unreferenced non-entry-point)."""

    node_id: str
    label: NodeLabel
    name: str
    file_path: str
    line: int


def _is_entry_point(node) -> bool:
    """Return True if the node is an entry point by heuristic or flag."""
    if node.is_entry_point:
        return True
    # Symbol lives in __init__.py → treated as exported
    if node.file_path.endswith("__init__.py"):
        return True
    # main() function
    if node.name == "main" and node.label in (NodeLabel.FUNCTION, NodeLabel.METHOD):
        return True
    # test_ prefix (functions or methods)
    if node.name.startswith("test_") and node.label in (
        NodeLabel.FUNCTION,
        NodeLabel.METHOD,
    ):
        return True
    # Test class (Test prefix, CLASS label)
    if node.name.startswith("Test") and node.label == NodeLabel.CLASS:
        return True
    return False


def _has_incoming_live_edge(storage: GraphStorage, node_id: str) -> bool:
    """Return True if any CALLS/IMPORTS/EXTENDS/IMPLEMENTS edge targets this node."""
    assert storage._conn is not None
    placeholders = ",".join("?" * len(_INCOMING_LIVE_EDGE_TYPES))
    cur = storage._conn.execute(
        f"SELECT 1 FROM relationships WHERE target = ? AND type IN ({placeholders}) LIMIT 1",
        (node_id, *_INCOMING_LIVE_EDGE_TYPES),
    )
    return cur.fetchone() is not None


def detect_dead_code(storage: GraphStorage) -> list[DeadCodeResult]:
    """Detect dead code symbols and mark them in storage.

    Args:
        storage: Initialized GraphStorage with indexed nodes/relationships.

    Returns:
        List of DeadCodeResult for all dead symbols found. Marks dead nodes
        in storage via mark_dead_nodes().
    """
    symbol_nodes = storage.get_all_symbol_nodes()
    dead_ids: list[str] = []
    results: list[DeadCodeResult] = []

    for node in symbol_nodes:
        if _is_entry_point(node):
            continue
        if _has_incoming_live_edge(storage, node.id):
            continue
        dead_ids.append(node.id)
        results.append(DeadCodeResult(
            node_id=node.id,
            label=node.label,
            name=node.name,
            file_path=node.file_path,
            line=node.start_line,
        ))

    if dead_ids:
        storage.mark_dead_nodes(dead_ids)

    return results
