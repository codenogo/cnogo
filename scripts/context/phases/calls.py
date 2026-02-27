"""Call tracing phase with confidence scoring.

For each CallInfo, finds the containing symbol (caller) via bisect on
line ranges, resolves the target (callee) with tiered confidence, and
creates CALLS edges.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import bisect
import json

from scripts.context.model import (
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import CallInfo, ParseResult, SymbolInfo
from scripts.context.storage import GraphStorage

# Common builtins/stdlib functions to skip — reduces noise significantly
CALL_BLOCKLIST = frozenset({
    "print", "len", "range", "isinstance", "hasattr", "getattr",
    "setattr", "super", "type", "enumerate", "zip", "map", "filter",
    "sorted", "reversed", "list", "dict", "set", "tuple", "str", "int",
    "float", "bool", "bytes", "repr", "id", "hash", "callable",
    "iter", "next", "abs", "min", "max", "sum", "any", "all",
    "open", "input", "vars", "dir", "help", "breakpoint",
    "issubclass", "delattr", "property", "staticmethod", "classmethod",
    "NotImplementedError", "ValueError", "TypeError", "KeyError",
    "RuntimeError", "AttributeError", "IndexError", "Exception",
    "OSError", "IOError", "FileNotFoundError", "ImportError",
})

# Confidence tiers
_CONF_SAME_FILE = 1.0
_CONF_IMPORT_RESOLVED = 1.0
_CONF_RECEIVER_METHOD = 0.8
_CONF_GLOBAL_FUZZY = 0.5


def find_containing_symbol(
    line: int,
    symbols: list[SymbolInfo],
) -> SymbolInfo | None:
    """Find the most specific symbol containing a given line.

    Prefers methods over classes (narrower scope).
    Uses bisect for efficient lookup on sorted start_lines.
    """
    # Sort by start_line for bisect, but also keep end_line for filtering
    sorted_syms = sorted(symbols, key=lambda s: s.start_line)
    start_lines = [s.start_line for s in sorted_syms]

    # Find insertion point — candidates are all symbols starting at or before `line`
    idx = bisect.bisect_right(start_lines, line)

    best: SymbolInfo | None = None
    best_span = float("inf")

    # Check all candidates that start at or before `line`
    for i in range(idx):
        sym = sorted_syms[i]
        if sym.start_line <= line <= sym.end_line:
            span = sym.end_line - sym.start_line
            # Prefer narrower (more specific) symbol
            if span < best_span:
                best = sym
                best_span = span

    return best


def _build_name_index(storage: GraphStorage) -> dict[str, list[str]]:
    """Build mapping from symbol name to list of node IDs.

    Indexes FUNCTION, CLASS, and METHOD nodes.
    """
    assert storage._conn is not None
    index: dict[str, list[str]] = {}
    for label in (NodeLabel.FUNCTION, NodeLabel.CLASS, NodeLabel.METHOD):
        cur = storage._conn.execute(
            "SELECT id, name FROM nodes WHERE label = ?",
            (label.value,),
        )
        for node_id, name in cur.fetchall():
            index.setdefault(name, []).append(node_id)
    return index


def _build_import_map(storage: GraphStorage) -> dict[str, dict[str, str]]:
    """Build mapping: source_file → {symbol_name → target_file_path}.

    Uses IMPORTS edges with 'symbols' property to know which names
    were imported from which file.
    """
    assert storage._conn is not None
    cur = storage._conn.execute(
        "SELECT source, target, properties_json FROM relationships WHERE type = ?",
        (RelType.IMPORTS.value,),
    )

    import_map: dict[str, dict[str, str]] = {}
    for source_id, target_id, props_json in cur.fetchall():
        props = json.loads(props_json)
        symbols = props.get("symbols", [])
        if not symbols:
            continue

        # Extract file_path from target node
        target_node = storage._conn.execute(
            "SELECT file_path FROM nodes WHERE id = ?", (target_id,)
        ).fetchone()
        if target_node is None:
            continue
        target_file = target_node[0]

        # Extract source file_path
        source_node = storage._conn.execute(
            "SELECT file_path FROM nodes WHERE id = ?", (source_id,)
        ).fetchone()
        if source_node is None:
            continue
        source_file = source_node[0]

        file_map = import_map.setdefault(source_file, {})
        for sym_name in symbols:
            file_map[sym_name] = target_file

    return import_map


def _resolve_call(
    call: CallInfo,
    source_file: str,
    caller: SymbolInfo | None,
    file_symbols: dict[str, list[SymbolInfo]],
    name_index: dict[str, list[str]],
    import_map: dict[str, dict[str, str]],
) -> tuple[str | None, float]:
    """Resolve a call to a target node ID with confidence.

    Priority:
    1. Same-file exact match → 1.0
    2. Import-resolved match → 1.0
    3. self/cls receiver method on same class → 0.8
    4. Global fuzzy match → 0.5

    Returns (target_node_id, confidence) or (None, 0).
    """
    name = call.name

    # Priority 0: self/cls receiver → check class methods first (most specific)
    if call.receiver in ("self", "cls") and caller and caller.class_name:
        for sym in file_symbols.get(source_file, []):
            if sym.name == name and sym.kind == "method" and sym.class_name == caller.class_name:
                return generate_id(NodeLabel.METHOD, source_file, name), _CONF_RECEIVER_METHOD

    # Priority 1: Same-file exact name match (bare calls only)
    if not call.receiver:
        for sym in file_symbols.get(source_file, []):
            if sym.name == name and sym is not caller:
                label = {
                    "function": NodeLabel.FUNCTION,
                    "class": NodeLabel.CLASS,
                    "method": NodeLabel.METHOD,
                }.get(sym.kind)
                if label:
                    return generate_id(label, source_file, name), _CONF_SAME_FILE

    # Priority 2: Import-resolved match
    imported_symbols = import_map.get(source_file, {})
    if name in imported_symbols:
        target_file = imported_symbols[name]
        # First check parse results for the target file
        for sym in file_symbols.get(target_file, []):
            if sym.name == name:
                label = {
                    "function": NodeLabel.FUNCTION,
                    "class": NodeLabel.CLASS,
                    "method": NodeLabel.METHOD,
                }.get(sym.kind)
                if label:
                    return generate_id(label, target_file, name), _CONF_IMPORT_RESOLVED
        # Fallback: check name_index for nodes in the target file
        for node_id in name_index.get(name, []):
            if target_file in node_id:
                return node_id, _CONF_IMPORT_RESOLVED

    # Priority 3: Global fuzzy match
    if name in name_index:
        candidates = name_index[name]
        if candidates:
            return candidates[0], _CONF_GLOBAL_FUZZY

    return None, 0.0


def process_calls(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create CALLS edges from parse results.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write relationships to.
    """
    name_index = _build_name_index(storage)
    import_map = _build_import_map(storage)

    # Build per-file symbol lists from parse results
    file_symbols: dict[str, list[SymbolInfo]] = {}
    for file_path, result in parse_results.items():
        file_symbols[file_path] = result.symbols

    relationships: list[GraphRelationship] = []

    for file_path, result in parse_results.items():
        for call in result.calls:
            # Skip blocklisted builtins
            if call.name in CALL_BLOCKLIST:
                continue

            # Find containing symbol (caller)
            caller = find_containing_symbol(call.line, result.symbols)

            # Determine caller node ID
            if caller is not None:
                caller_label = {
                    "function": NodeLabel.FUNCTION,
                    "class": NodeLabel.CLASS,
                    "method": NodeLabel.METHOD,
                }.get(caller.kind)
                if caller_label:
                    caller_id = generate_id(caller_label, file_path, caller.name)
                else:
                    caller_id = generate_id(NodeLabel.FILE, file_path, "")
            else:
                # Module-level call — use FILE as caller
                caller_id = generate_id(NodeLabel.FILE, file_path, "")

            # Resolve target
            target_id, confidence = _resolve_call(
                call, file_path, caller, file_symbols, name_index, import_map,
            )
            if target_id is None:
                continue

            rel_id = f"calls:{caller_id}->{target_id}:{call.line}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.CALLS,
                source=caller_id,
                target=target_id,
                properties={"confidence": confidence},
            ))

    if relationships:
        storage.add_relationships(relationships)
