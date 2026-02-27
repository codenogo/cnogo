"""Context graph package.

Provides a code knowledge graph backed by SQLite for codebase understanding.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
)
from scripts.context.phases.calls import process_calls
from scripts.context.phases.heritage import process_heritage
from scripts.context.phases.imports import process_imports
from scripts.context.phases.structure import process_structure
from scripts.context.phases.symbols import process_symbols
from scripts.context.python_parser import PythonParser
from scripts.context.storage import GraphStorage
from scripts.context.walker import walk

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
        """Build or incrementally update the context graph.

        Pipeline: walk → structure → symbols → imports → calls → heritage.
        Compares file hashes for incremental updates.
        """
        # Step 1: Walk files
        files = walk(self.repo_path)

        # Step 2: Compare hashes for incremental indexing
        indexed_hashes = self._storage.get_indexed_files()
        changed_files = []
        current_paths = set()

        for entry in files:
            file_path = str(PurePosixPath(entry.path))
            current_paths.add(file_path)
            old_hash = indexed_hashes.get(file_path)
            if old_hash != entry.content_hash:
                changed_files.append(entry)

        # Step 3: Remove stale files (deleted from disk)
        for stale_path in set(indexed_hashes.keys()) - current_paths:
            self._storage.remove_nodes_by_file(stale_path)
            self._storage.remove_file_hash(stale_path)

        if not changed_files:
            return

        # Step 4: Remove old nodes for changed files
        for entry in changed_files:
            file_path = str(PurePosixPath(entry.path))
            self._storage.remove_nodes_by_file(file_path)

        # Step 5: Run structure phase (creates FILE + FOLDER nodes)
        process_structure(changed_files, self._storage)

        # Step 6: Parse changed files
        parse_results = {}
        for entry in changed_files:
            file_path = str(PurePosixPath(entry.path))
            result = PythonParser.parse(entry.content, file_path)
            parse_results[file_path] = result

        # Step 7: Run phases in order
        process_symbols(parse_results, self._storage)
        process_imports(parse_results, self._storage)
        process_calls(parse_results, self._storage)
        process_heritage(parse_results, self._storage)

        # Step 8: Update file hashes
        for entry in changed_files:
            file_path = str(PurePosixPath(entry.path))
            self._storage.update_file_hash(file_path, entry.content_hash)

    def query(self, name: str) -> list[GraphNode]:
        """Search for nodes by name."""
        assert self._storage._conn is not None
        cur = self._storage._conn.execute(
            "SELECT * FROM nodes WHERE name = ?", (name,)
        )
        return [self._storage._row_to_node(row) for row in cur.fetchall()]

    def impact(self, file_path: str) -> list[GraphNode]:
        """Analyze change impact for a file."""
        raise NotImplementedError

    def context(self, node_id: str) -> dict:
        """Get context around a node (callers, callees, etc.)."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the underlying storage connection."""
        self._storage.close()
