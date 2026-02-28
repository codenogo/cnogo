"""Heritage phase: creates EXTENDS and IMPLEMENTS edges.

For each heritage tuple (child, relationship, parent) from ParseResult,
finds both class nodes in storage and creates the appropriate edge.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from scripts.context.model import (
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import ParseResult
from scripts.context.storage import GraphStorage


def _build_class_index(storage: GraphStorage) -> dict[str, list[str]]:
    """Build mapping from class name to list of node IDs.

    Indexes CLASS and INTERFACE nodes for heritage resolution.
    """
    assert storage._conn is not None
    index: dict[str, list[str]] = {}
    for label in (NodeLabel.CLASS, NodeLabel.INTERFACE):
        cur = storage._conn.execute(
            "SELECT id, name FROM nodes WHERE label = ?",
            (label.value,),
        )
        for node_id, name in cur.fetchall():
            index.setdefault(name, []).append(node_id)
    return index


def process_heritage(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create EXTENDS and IMPLEMENTS edges from heritage tuples.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write relationships to.
    """
    class_index = _build_class_index(storage)
    relationships: list[GraphRelationship] = []

    rel_type_map = {
        "extends": RelType.EXTENDS,
        "implements": RelType.IMPLEMENTS,
    }

    for file_path, result in parse_results.items():
        for child_name, rel_kind, parent_name in result.heritage:
            rel_type = rel_type_map.get(rel_kind)
            if rel_type is None:
                continue

            # Find child node — prefer same-file match
            child_id = _find_node(child_name, file_path, class_index)
            if child_id is None:
                continue

            # Find parent node — check same file first, then global
            parent_id = _find_node(parent_name, file_path, class_index)
            if parent_id is None:
                continue

            rel_id = f"{rel_type.value}:{child_id}->{parent_id}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=rel_type,
                source=child_id,
                target=parent_id,
            ))

    if relationships:
        storage.add_relationships(relationships)


def _find_node(
    name: str,
    preferred_file: str,
    class_index: dict[str, list[str]],
) -> str | None:
    """Find a class/interface node by name, preferring same-file matches."""
    candidates = class_index.get(name, [])
    if not candidates:
        return None

    # Prefer same-file match
    for node_id in candidates:
        if preferred_file in node_id:
            return node_id

    # Fall back to first match
    return candidates[0]
