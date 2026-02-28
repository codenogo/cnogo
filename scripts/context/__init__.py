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
from scripts.context.phases.community import CommunityDetectionResult, detect_communities
from scripts.context.phases.coupling import CouplingResult, compute_coupling
from scripts.context.phases.dead_code import DeadCodeResult, detect_dead_code
from scripts.context.phases.flows import FlowResult, trace_flows
from scripts.context.phases.heritage import process_heritage
from scripts.context.phases.impact import ImpactResult, impact_analysis
from scripts.context.phases.imports import process_imports
from scripts.context.phases.structure import process_structure
from scripts.context.phases.symbols import process_symbols
from scripts.context.python_parser import PythonParser
from scripts.context.storage import GraphStorage
from scripts.context.walker import walk

__all__ = [
    "CommunityDetectionResult",
    "ContextGraph",
    "CouplingResult",
    "DeadCodeResult",
    "FlowResult",
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

        # Step 8: Trace execution flows from entry points
        trace_flows(self._storage)

        # Step 9: Rebuild FTS index
        self._storage.rebuild_fts()

        # Step 10: Update file hashes
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

    def impact(self, file_path: str, max_depth: int = 3) -> list[ImpactResult]:
        """Analyze change impact for a file (BFS blast radius)."""
        return impact_analysis(self._storage, file_path, max_depth)

    def context(self, node_id: str) -> dict:
        """Get context around a node (callers, callees, imports, heritage).

        Returns a dict with keys: node, callers, callees, importers, imports,
        parent_classes, child_classes. Each value is a list of GraphNode.

        Raises ValueError if node_id is not found.
        """
        node = self._storage.get_node(node_id)
        if node is None:
            raise ValueError(f"Node '{node_id}' not found")

        return {
            "node": node,
            "callers": self._storage.get_related_nodes(node_id, RelType.CALLS, "incoming"),
            "callees": self._storage.get_related_nodes(node_id, RelType.CALLS, "outgoing"),
            "importers": self._storage.get_related_nodes(node_id, RelType.IMPORTS, "incoming"),
            "imports": self._storage.get_related_nodes(node_id, RelType.IMPORTS, "outgoing"),
            "parent_classes": self._storage.get_related_nodes(node_id, RelType.EXTENDS, "outgoing"),
            "child_classes": self._storage.get_related_nodes(node_id, RelType.EXTENDS, "incoming"),
        }

    def communities(self, min_size: int = 2) -> CommunityDetectionResult:
        """Detect communities of tightly-coupled symbols via label propagation."""
        self.index()
        return detect_communities(self._storage, min_size=min_size)

    def coupling(self, threshold: float = 0.5) -> list[CouplingResult]:
        """Compute structural coupling between symbols via Jaccard similarity."""
        return compute_coupling(self._storage, threshold)

    def dead_code(self) -> list[DeadCodeResult]:
        """Detect dead (unreferenced) symbols in the graph."""
        return detect_dead_code(self._storage)

    def flows(self, max_depth: int = 10) -> list[FlowResult]:
        """Trace execution flows from entry points through forward CALLS edges."""
        self.index()
        return trace_flows(self._storage, max_depth)

    def search(self, query: str, limit: int = 20) -> list[tuple[GraphNode, float]]:
        """Full-text search over symbol names, signatures, and docstrings.

        Args:
            query: Search query string (supports FTS5 syntax).
            limit: Maximum number of results (default 20).

        Returns:
            List of (GraphNode, score) tuples, highest relevance first.
        """
        self.index()
        return self._storage.search(query, limit)

    def review_impact(self, changed_files: list[str]) -> dict:
        """Compute blast-radius impact for a set of changed files.

        Auto-indexes the graph for freshness, then runs impact analysis
        on each changed file and aggregates results.

        Returns a dict with keys:
            graph_status, affected_files, affected_symbols,
            per_file, total_affected.
        """
        self.index()

        empty: dict = {
            "graph_status": "indexed",
            "affected_files": [],
            "affected_symbols": [],
            "per_file": {},
            "total_affected": 0,
        }

        if not changed_files:
            return empty

        seen_files: set[str] = set()
        seen_symbols: dict[str, dict] = {}
        per_file: dict[str, list[dict]] = {}

        for fpath in changed_files:
            impacts = self.impact(fpath)
            file_entries: list[dict] = []
            for ir in impacts:
                node = ir.node
                entry = {
                    "name": node.name,
                    "label": node.label.value if hasattr(node.label, "value") else str(node.label),
                    "file_path": node.file_path,
                    "depth": ir.depth,
                }
                file_entries.append(entry)
                if node.file_path:
                    seen_files.add(node.file_path)
                if node.id not in seen_symbols:
                    seen_symbols[node.id] = entry
            per_file[fpath] = file_entries

        return {
            "graph_status": "indexed",
            "affected_files": sorted(seen_files),
            "affected_symbols": list(seen_symbols.values()),
            "per_file": per_file,
            "total_affected": len(seen_symbols),
        }

    def close(self) -> None:
        """Close the underlying storage connection."""
        self._storage.close()
