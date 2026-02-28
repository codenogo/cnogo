"""Exports phase: creates EXPORTS edges from __all__ declarations.

For each file in parse_results, iterates ParseResult.exports (names from
__all__). For each exported name, finds the symbol node in the same file
(FUNCTION, CLASS, METHOD). Creates an EXPORTS edge from FILE → symbol.
Also sets is_exported=True on the symbol node via a bulk UPDATE.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from scripts.context.model import (
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.python_parser import ParseResult
from scripts.context.storage import GraphStorage


def _build_symbol_index(storage: GraphStorage) -> dict[str, dict[str, str]]:
    """Build mapping from file_path → {symbol_name: node_id}.

    Indexes FUNCTION, CLASS, and METHOD nodes for export resolution.
    Returns: {file_path: {name: node_id}}
    """
    assert storage._conn is not None
    index: dict[str, dict[str, str]] = {}
    for label in (NodeLabel.FUNCTION, NodeLabel.CLASS, NodeLabel.METHOD):
        cur = storage._conn.execute(
            "SELECT id, name, file_path FROM nodes WHERE label = ?",
            (label.value,),
        )
        for node_id, name, file_path in cur.fetchall():
            index.setdefault(file_path, {})[name] = node_id
    return index


def _build_file_node_index(storage: GraphStorage) -> dict[str, str]:
    """Build mapping from file_path → FILE node ID."""
    assert storage._conn is not None
    index: dict[str, str] = {}
    cur = storage._conn.execute(
        "SELECT id, file_path FROM nodes WHERE label = ?",
        (NodeLabel.FILE.value,),
    )
    for node_id, file_path in cur.fetchall():
        index[file_path] = node_id
    return index


def _mark_exported_nodes(storage: GraphStorage, node_ids: list[str]) -> None:
    """Bulk set is_exported=1 for the given node IDs."""
    assert storage._conn is not None
    if not node_ids:
        return
    placeholders = ",".join("?" * len(node_ids))
    storage._conn.execute(
        f"UPDATE nodes SET is_exported = 1 WHERE id IN ({placeholders})", node_ids
    )
    storage._conn.commit()


def process_exports(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create EXPORTS edges from __all__ symbol lists.

    For each exported name in each file, finds the corresponding symbol
    node (FUNCTION, CLASS, or METHOD) in the same file and creates an
    EXPORTS edge from FILE → symbol. Also sets is_exported=True on
    those symbol nodes.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write relationships to.
    """
    symbol_index = _build_symbol_index(storage)
    file_node_index = _build_file_node_index(storage)
    relationships: list[GraphRelationship] = []
    exported_node_ids: list[str] = []

    for file_path, result in parse_results.items():
        if not result.exports:
            continue

        file_symbols = symbol_index.get(file_path, {})
        source_id = file_node_index.get(file_path)
        if source_id is None:
            continue

        for exported_name in result.exports:
            target_id = file_symbols.get(exported_name)
            if target_id is None:
                continue

            rel_id = f"exports:{source_id}->{target_id}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.EXPORTS,
                source=source_id,
                target=target_id,
            ))
            exported_node_ids.append(target_id)

    if relationships:
        storage.add_relationships(relationships)

    if exported_node_ids:
        _mark_exported_nodes(storage, exported_node_ids)
