"""Symbols phase: creates FUNCTION/CLASS/METHOD nodes + DEFINES edges.

For each SymbolInfo from ParseResult, creates the appropriate node type
and a DEFINES edge from the FILE node to the symbol node.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import ParseResult
from scripts.context.storage import GraphStorage

_KIND_TO_LABEL = {
    "function": NodeLabel.FUNCTION,
    "class": NodeLabel.CLASS,
    "method": NodeLabel.METHOD,
}


def process_symbols(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create symbol nodes and DEFINES edges from parse results.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write nodes/relationships to.
    """
    nodes: list[GraphNode] = []
    relationships: list[GraphRelationship] = []

    for file_path, result in parse_results.items():
        file_id = generate_id(NodeLabel.FILE, file_path, "")

        for sym in result.symbols:
            label = _KIND_TO_LABEL.get(sym.kind)
            if label is None:
                continue

            node_id = generate_id(label, file_path, sym.name)
            props: dict = {}
            if sym.decorators:
                props["decorators"] = sym.decorators

            nodes.append(GraphNode(
                id=node_id,
                label=label,
                name=sym.name,
                file_path=file_path,
                start_line=sym.start_line,
                end_line=sym.end_line,
                content=sym.docstring,
                signature=sym.signature,
                class_name=sym.class_name,
                properties=props,
            ))

            # DEFINES edge: FILE → symbol
            rel_id = f"defines:{file_id}->{node_id}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.DEFINES,
                source=file_id,
                target=node_id,
            ))

    if nodes:
        storage.add_nodes(nodes)
    if relationships:
        storage.add_relationships(relationships)
