"""Dead code detection phase.

Identifies symbol nodes with no incoming CALLS/IMPORTS/EXTENDS/IMPLEMENTS edges,
excluding known entry points.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.context.model import NodeLabel, RelType
from scripts.context.storage import GraphStorage


@dataclass
class DeadCodeResult:
    node_id: str
    name: str
    label: NodeLabel
    file_path: str
    line: int


def _is_entry_point(node) -> bool:
    """Return True if node should be treated as an entry point (not dead)."""
    if node.is_entry_point:
        return True
    if node.is_exported:
        return True
    if node.name == "main":
        return True
    if node.name.startswith("test_") or node.name.startswith("Test"):
        return True
    if "__init__.py" in node.file_path:
        return True
    return False


def detect_dead_code(storage: GraphStorage) -> list[DeadCodeResult]:
    """Find symbols with zero incoming CALLS/IMPORTS/EXTENDS/IMPLEMENTS edges.

    After detection, calls storage.mark_dead_nodes() on found IDs.
    Returns list of DeadCodeResult.
    """
    symbol_nodes = storage.get_all_symbol_nodes()
    if not symbol_nodes:
        return []

    # Build set of node IDs that have at least one incoming relevant edge
    incoming_rel_types = [
        RelType.CALLS.value,
        RelType.IMPORTS.value,
        RelType.EXTENDS.value,
        RelType.IMPLEMENTS.value,
    ]
    all_rels = storage.get_all_relationships_by_types(incoming_rel_types)
    # target IDs that have at least one incoming edge
    referenced: set[str] = {target for _, target, _ in all_rels}

    dead_results: list[DeadCodeResult] = []
    dead_ids: list[str] = []

    for node in symbol_nodes:
        if _is_entry_point(node):
            continue
        if node.id not in referenced:
            dead_results.append(DeadCodeResult(
                node_id=node.id,
                name=node.name,
                label=node.label,
                file_path=node.file_path,
                line=node.start_line,
            ))
            dead_ids.append(node.id)

    if dead_ids:
        storage.mark_dead_nodes(dead_ids)

    return dead_results
