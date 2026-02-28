"""Context graph visualization module.

Provides Mermaid and DOT (Graphviz) renderers for the context graph.

Scope options:
- 'file'   — only nodes in the same file as the center node
- 'module' — nodes in the same directory as the center (or all if no center)
- 'full'   — entire graph

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import re
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode


def _sanitize_mermaid_id(node_id: str) -> str:
    """Convert a raw node ID into a Mermaid-safe identifier.

    Replaces characters that break Mermaid syntax (: / . - spaces) with _.
    """
    # Replace any non-alphanumeric character with underscore
    return re.sub(r"[^a-zA-Z0-9]", "_", node_id)


def _collect_subgraph(
    storage: "GraphStorage",
    scope: str,
    center: str | None,
    depth: int,
) -> tuple[list["GraphNode"], list[tuple[str, str, str]]]:
    """Collect nodes and edges within the given scope via BFS.

    Args:
        storage: GraphStorage instance with an active connection.
        scope:   'file', 'module', or 'full'.
        center:  Center node ID for BFS (required for 'file'/'module' scopes;
                 optional for 'full' scope to limit depth).
        depth:   BFS depth limit from center node.

    Returns:
        (nodes, edges) where edges are (source_id, target_id, rel_type) tuples.
    """
    assert storage._conn is not None

    if scope not in ("file", "module", "full"):
        raise ValueError(f"scope must be 'file', 'module', or 'full', got: {scope!r}")

    # --- Determine the candidate node set based on scope ---
    if scope == "full":
        if center is None:
            # Return all nodes and all edges
            cur = storage._conn.execute("SELECT * FROM nodes")
            all_nodes = [storage._row_to_node(row) for row in cur.fetchall()]
            cur = storage._conn.execute("SELECT source, target, type FROM relationships")
            all_edges = [(row[0], row[1], row[2].upper()) for row in cur.fetchall()]
            return all_nodes, all_edges

        # Full scope with center: BFS outward from center collecting everything
        # within depth hops (all edge types, both directions)
        candidate_ids = _bfs_all_edges(storage, center, depth)

    elif scope == "file":
        if center is None:
            # No center — return all nodes (treating as full)
            cur = storage._conn.execute("SELECT * FROM nodes")
            all_nodes = [storage._row_to_node(row) for row in cur.fetchall()]
            cur = storage._conn.execute("SELECT source, target, type FROM relationships")
            all_edges = [(row[0], row[1], row[2].upper()) for row in cur.fetchall()]
            return all_nodes, all_edges

        # Find file_path of center node
        center_node = storage.get_node(center)
        if center_node is None:
            return [], []

        file_path = center_node.file_path
        cur = storage._conn.execute(
            "SELECT id FROM nodes WHERE file_path = ?", (file_path,)
        )
        file_node_ids = {row[0] for row in cur.fetchall()}

        # BFS within the file, limited by depth
        bfs_ids = _bfs_all_edges(storage, center, depth)
        candidate_ids = bfs_ids & file_node_ids

    elif scope == "module":
        # Module = directory containing center's file (or entire graph if no center)
        if center is None:
            cur = storage._conn.execute("SELECT * FROM nodes")
            all_nodes = [storage._row_to_node(row) for row in cur.fetchall()]
            cur = storage._conn.execute("SELECT source, target, type FROM relationships")
            all_edges = [(row[0], row[1], row[2].upper()) for row in cur.fetchall()]
            return all_nodes, all_edges

        center_node = storage.get_node(center)
        if center_node is None:
            return [], []

        # Get directory of center node's file
        file_path = center_node.file_path
        if "/" in file_path:
            module_dir = file_path.rsplit("/", 1)[0]
            cur = storage._conn.execute(
                "SELECT id FROM nodes WHERE file_path LIKE ?",
                (module_dir + "/%",),
            )
        else:
            # Top-level file — include all top-level files (no subdirectory)
            cur = storage._conn.execute(
                "SELECT id FROM nodes WHERE file_path NOT LIKE '%/%'"
            )
        module_node_ids = {row[0] for row in cur.fetchall()}

        bfs_ids = _bfs_all_edges(storage, center, depth)
        candidate_ids = bfs_ids & module_node_ids

    # Fetch the actual node objects
    if not candidate_ids:
        return [], []

    placeholders = ",".join("?" * len(candidate_ids))
    id_list = list(candidate_ids)
    cur = storage._conn.execute(
        f"SELECT * FROM nodes WHERE id IN ({placeholders})", id_list
    )
    nodes = [storage._row_to_node(row) for row in cur.fetchall()]

    # Collect edges between nodes in the candidate set
    cur = storage._conn.execute(
        f"SELECT source, target, type FROM relationships "
        f"WHERE source IN ({placeholders}) AND target IN ({placeholders})",
        id_list + id_list,
    )
    edges = [(row[0], row[1], row[2].upper()) for row in cur.fetchall()]

    return nodes, edges


def _bfs_all_edges(
    storage: "GraphStorage",
    start_id: str,
    depth: int,
) -> set[str]:
    """BFS from start_id across all edge types (both directions), up to depth.

    Returns the set of visited node IDs (including start_id).
    """
    assert storage._conn is not None

    visited: set[str] = {start_id}
    queue: deque[tuple[str, int]] = deque([(start_id, 0)])

    while queue:
        node_id, d = queue.popleft()
        if d >= depth:
            continue

        # Outgoing edges
        cur = storage._conn.execute(
            "SELECT target FROM relationships WHERE source = ?", (node_id,)
        )
        for (target_id,) in cur.fetchall():
            if target_id not in visited:
                visited.add(target_id)
                queue.append((target_id, d + 1))

        # Incoming edges
        cur = storage._conn.execute(
            "SELECT source FROM relationships WHERE target = ?", (node_id,)
        )
        for (source_id,) in cur.fetchall():
            if source_id not in visited:
                visited.add(source_id)
                queue.append((source_id, d + 1))

    return visited


def render_mermaid(
    nodes: list["GraphNode"],
    edges: list[tuple[str, str, str]],
) -> str:
    """Render nodes and edges as Mermaid flowchart syntax.

    Args:
        nodes: List of GraphNode instances to render.
        edges: List of (source_id, target_id, rel_type) tuples.

    Returns:
        Mermaid flowchart string.

    Example output::

        flowchart TD
            node_id["Label (TYPE)"]
            node_id2["Label2 (TYPE)"]
            node_id -->|"CALLS"| node_id2
    """
    lines = ["flowchart TD"]

    # Node declarations
    for node in nodes:
        safe_id = _sanitize_mermaid_id(node.id)
        label = node.name
        node_type = node.label.value.upper()
        lines.append(f'    {safe_id}["{label} ({node_type})"]')

    # Edge declarations
    # Build a quick id→safe_id map to avoid repeated sanitization
    id_to_safe: dict[str, str] = {n.id: _sanitize_mermaid_id(n.id) for n in nodes}

    for source_id, target_id, rel_type in edges:
        src = id_to_safe.get(source_id, _sanitize_mermaid_id(source_id))
        tgt = id_to_safe.get(target_id, _sanitize_mermaid_id(target_id))
        lines.append(f'    {src} -->|"{rel_type}"| {tgt}')

    return "\n".join(lines) + "\n"


def render_dot(
    nodes: list["GraphNode"],
    edges: list[tuple[str, str, str]],
) -> str:
    """Render nodes and edges as DOT/Graphviz digraph syntax.

    Args:
        nodes: List of GraphNode instances to render.
        edges: List of (source_id, target_id, rel_type) tuples.

    Returns:
        DOT digraph string.

    Example output::

        digraph G {
            rankdir=TB;
            "node_id" [label="Label\\n(TYPE)" shape=box];
            "node_id2" [label="Label2\\n(TYPE)" shape=box];
            "node_id" -> "node_id2" [label="CALLS"];
        }
    """
    lines = ["digraph G {", "    rankdir=TB;"]

    # Node declarations — DOT allows arbitrary strings as IDs when quoted
    for node in nodes:
        node_type = node.label.value.upper()
        # Escape backslashes and quotes in node ID and label
        safe_id = node.id.replace("\\", "\\\\").replace('"', '\\"')
        label = f"{node.name}\\n({node_type})"
        lines.append(f'    "{safe_id}" [label="{label}" shape=box];')

    # Edge declarations
    for source_id, target_id, rel_type in edges:
        src = source_id.replace("\\", "\\\\").replace('"', '\\"')
        tgt = target_id.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'    "{src}" -> "{tgt}" [label="{rel_type}"];')

    lines.append("}")
    return "\n".join(lines) + "\n"
