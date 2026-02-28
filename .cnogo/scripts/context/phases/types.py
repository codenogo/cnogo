"""Types phase: creates USES_TYPE edges from type annotations.

For each TypeRef in ParseResult.type_refs, finds the source symbol
(function/method containing the annotation by matching file_path + line range)
and the target type node (CLASS, INTERFACE, TYPE_ALIAS, ENUM). Creates a
USES_TYPE edge from source → target.

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


def _build_type_index(storage: GraphStorage) -> dict[str, list[str]]:
    """Build mapping from type name to list of node IDs.

    Indexes CLASS, INTERFACE, TYPE_ALIAS, and ENUM nodes for type resolution.
    """
    assert storage._conn is not None
    index: dict[str, list[str]] = {}
    for label in (NodeLabel.CLASS, NodeLabel.INTERFACE, NodeLabel.TYPE_ALIAS, NodeLabel.ENUM):
        cur = storage._conn.execute(
            "SELECT id, name FROM nodes WHERE label = ?",
            (label.value,),
        )
        for node_id, name in cur.fetchall():
            index.setdefault(name, []).append(node_id)
    return index


def _build_symbol_index(storage: GraphStorage) -> list[tuple[str, str, int, int]]:
    """Build list of (node_id, file_path, start_line, end_line) for symbol nodes.

    Indexes FUNCTION and METHOD nodes for source symbol resolution.
    """
    assert storage._conn is not None
    symbols = []
    for label in (NodeLabel.FUNCTION, NodeLabel.METHOD):
        cur = storage._conn.execute(
            "SELECT id, file_path, start_line, end_line FROM nodes WHERE label = ?",
            (label.value,),
        )
        for node_id, file_path, start_line, end_line in cur.fetchall():
            symbols.append((node_id, file_path, start_line, end_line))
    return symbols


def _find_source_symbol(
    file_path: str,
    line: int,
    symbol_index: list[tuple[str, str, int, int]],
) -> str | None:
    """Find the function/method node whose line range contains the given line.

    Prefers the narrowest (innermost) containing range.
    """
    best_id = None
    best_range = None

    for node_id, sym_file, start_line, end_line in symbol_index:
        if sym_file != file_path:
            continue
        if start_line <= line <= end_line:
            span = end_line - start_line
            if best_range is None or span < best_range:
                best_id = node_id
                best_range = span

    return best_id


def _find_type_node(
    name: str,
    preferred_file: str,
    type_index: dict[str, list[str]],
) -> str | None:
    """Find a type node by name, preferring same-file matches."""
    candidates = type_index.get(name, [])
    if not candidates:
        return None

    # Prefer same-file match by checking if file_path appears in node_id
    for node_id in candidates:
        if preferred_file in node_id:
            return node_id

    # Fall back to first match
    return candidates[0]


def process_types(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create USES_TYPE edges from type annotation references.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write relationships to.
    """
    type_index = _build_type_index(storage)
    symbol_index = _build_symbol_index(storage)
    relationships: list[GraphRelationship] = []

    for file_path, result in parse_results.items():
        for type_ref in result.type_refs:
            # Find source symbol (function/method containing this annotation line)
            source_id = _find_source_symbol(file_path, type_ref.line, symbol_index)
            if source_id is None:
                continue

            # Find target type node
            target_id = _find_type_node(type_ref.name, file_path, type_index)
            if target_id is None:
                continue

            rel_id = f"uses_type:{source_id}->{target_id}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.USES_TYPE,
                source=source_id,
                target=target_id,
            ))

    if relationships:
        storage.add_relationships(relationships)
