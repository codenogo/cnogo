"""Context graph package.

Provides a code knowledge graph backed by SQLite for codebase understanding.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from pathlib import Path

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.storage import GraphStorage

__all__ = [
    "ContextGraph",
    "GraphNode",
    "GraphRelationship",
    "NodeLabel",
    "RelType",
]


class ContextGraph:
    """Code knowledge graph backed by SQLite storage.

    Usage::

        graph = ContextGraph(repo_path=".")
        graph.index()          # Build/update the graph
        graph.query("foo")     # Search for symbols
        graph.impact("a.py")   # Analyze change impact
    """

    def __init__(self, repo_path: str | Path = ".") -> None:
        self.repo_path = Path(repo_path)
        self.db_path = self.repo_path / ".cnogo" / "graph.db"
        self._storage = GraphStorage(self.db_path)
        self._storage.initialize()

    def is_indexed(self) -> bool:
        """Check if the graph has any indexed nodes."""
        return self._storage.node_count() > 0

    def index(self) -> None:
        """Build or incrementally update the context graph."""
        raise NotImplementedError

    def query(self, name: str) -> list[GraphNode]:
        """Search for nodes by name."""
        raise NotImplementedError

    def impact(self, file_path: str) -> list[GraphNode]:
        """Analyze change impact for a file."""
        raise NotImplementedError

    def context(self, node_id: str) -> dict:
        """Get context around a node (callers, callees, etc.)."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the underlying storage connection."""
        self._storage.close()
