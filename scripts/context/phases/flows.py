"""Execution flow tracing phase.

BFS from entry points through forward CALLS edges, creating Process nodes
with STEP_IN_PROCESS edges at each depth level.

Entry point heuristics (reused from dead_code phase):
- Functions named ``main`` -> entry point
- Functions/classes with ``test_`` or ``Test`` prefix -> entry point
- Any symbol in an ``__init__.py`` file -> entry point (exported)
- Any symbol already flagged is_entry_point in storage -> entry point

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage


@dataclass
class FlowStep:
    """A single step in an execution flow."""

    node: GraphNode
    depth: int


@dataclass
class FlowResult:
    """Result of tracing a single execution flow from an entry point."""

    process_id: str
    entry_point: GraphNode
    steps: list[FlowStep]


def _is_entry_point(node: GraphNode) -> bool:
    """Return True if the node is an entry point by heuristic or flag."""
    if node.is_entry_point:
        return True
    if node.file_path.endswith("__init__.py"):
        return True
    if node.name == "main" and node.label in (NodeLabel.FUNCTION, NodeLabel.METHOD):
        return True
    if node.name.startswith("test_") and node.label in (
        NodeLabel.FUNCTION,
        NodeLabel.METHOD,
    ):
        return True
    if node.name.startswith("Test") and node.label == NodeLabel.CLASS:
        return True
    return False


def trace_flows(
    storage: GraphStorage,
    max_depth: int = 10,
) -> list[FlowResult]:
    """Trace execution flows from all entry points.

    Forward BFS through CALLS edges, creating Process nodes and
    STEP_IN_PROCESS edges for each flow.

    Args:
        storage: Initialized GraphStorage with indexed nodes/relationships.
        max_depth: Maximum BFS depth (default 10).

    Returns:
        List of FlowResult, one per entry point found.
    """
    symbol_nodes = storage.get_all_symbol_nodes()
    entry_points = [n for n in symbol_nodes if _is_entry_point(n)]

    if not entry_points:
        return []

    results: list[FlowResult] = []
    new_nodes: list[GraphNode] = []
    new_edges: list[GraphRelationship] = []

    for ep in entry_points:
        process_id = f"process:{ep.file_path}:{ep.name}"
        steps: list[FlowStep] = []
        visited: set[str] = {ep.id}

        # BFS from entry point through forward CALLS edges
        queue: deque[tuple[str, int]] = deque()
        for callee in storage.get_callees(ep.id):
            if callee.id not in visited:
                queue.append((callee.id, 1))
                visited.add(callee.id)

        while queue:
            node_id, depth = queue.popleft()
            if depth > max_depth:
                continue
            node = storage.get_node(node_id)
            if node is None:
                continue

            steps.append(FlowStep(node=node, depth=depth))

            new_edges.append(GraphRelationship(
                id=f"step:{process_id}->{node_id}",
                type=RelType.STEP_IN_PROCESS,
                source=process_id,
                target=node_id,
                properties={"depth": depth},
            ))

            if depth < max_depth:
                for callee in storage.get_callees(node_id):
                    if callee.id not in visited:
                        queue.append((callee.id, depth + 1))
                        visited.add(callee.id)

        new_nodes.append(GraphNode(
            id=process_id,
            label=NodeLabel.PROCESS,
            name=ep.name,
            file_path=ep.file_path,
        ))

        results.append(FlowResult(
            process_id=process_id,
            entry_point=ep,
            steps=steps,
        ))

    if new_nodes:
        storage.add_nodes(new_nodes)
    if new_edges:
        storage.add_relationships(new_edges)

    return results
