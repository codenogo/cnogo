"""Context graph package — universal multi-language code intelligence engine."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Re-export existing symbols
from scripts.context.model import NodeLabel, RelType, GraphNode, GraphRelationship, generate_id
from scripts.context.storage import GraphStorage
from scripts.context.walker import walk, FileEntry
from scripts.context.parser_base import ParseResult
from scripts.context.parser_registry import get_parser
from scripts.context.phases.structure import process_structure
from scripts.context.phases.symbols import process_symbols
from scripts.context.phases.imports import process_imports

__all__ = ["NodeLabel", "RelType", "GraphNode", "GraphRelationship", "generate_id", "ContextGraph"]


class ContextGraph:
    """Main API for the universal context graph.

    Usage:
        cg = ContextGraph("/path/to/repo")
        cg.index()         # Build/update the graph
        nodes = cg.query("MyClass")  # Search
        cg.close()
    """

    def __init__(self, repo_path: str | Path, db_path: str | Path | None = None) -> None:
        """Initialize ContextGraph.

        Args:
            repo_path: Root of the repository to index.
            db_path: Path for KuzuDB storage. Defaults to <repo_path>/.cnogo/graph.kuzu/
        """
        self._repo_path = Path(repo_path).resolve()
        if db_path is None:
            db_path = self._repo_path / ".cnogo" / "graph.kuzu"
        self._storage = GraphStorage(db_path)
        self._storage.initialize()

    def index(self) -> dict[str, Any]:
        """Run the full indexing pipeline.

        Pipeline: walk → hash check → remove stale → structure → parse → symbols → imports

        Returns dict with stats: {"files_indexed": int, "files_skipped": int, "files_removed": int}
        """
        # 1. Walk the repo
        all_files = walk(self._repo_path)

        # 2. Hash check — compare with stored hashes for incremental indexing
        stored_hashes = self._storage.get_indexed_files()

        new_or_changed: list[FileEntry] = []
        current_paths: set[str] = set()
        skipped = 0

        for entry in all_files:
            fp = str(entry.path)
            current_paths.add(fp)
            if stored_hashes.get(fp) == entry.content_hash:
                skipped += 1
                continue
            new_or_changed.append(entry)

        # 3. Remove stale files (files that were indexed but no longer exist)
        removed = 0
        for old_fp in stored_hashes:
            if old_fp not in current_paths:
                self._storage.remove_nodes_by_file(old_fp)
                self._storage.remove_file_hash(old_fp)
                removed += 1

        # Remove nodes for files that changed (will be re-indexed)
        for entry in new_or_changed:
            fp = str(entry.path)
            if fp in stored_hashes:
                self._storage.remove_nodes_by_file(fp)

        if not new_or_changed:
            return {"files_indexed": 0, "files_skipped": skipped, "files_removed": removed}

        # 4. Structure phase — create FILE and FOLDER nodes
        process_structure(new_or_changed, self._storage)

        # 5. Parse files concurrently
        parse_results: dict[str, ParseResult] = {}

        def _parse_file(entry: FileEntry) -> tuple[str, ParseResult | None]:
            parser = get_parser(entry.language)
            if parser is None:
                return str(entry.path), None
            return str(entry.path), parser.parse(entry.content, str(entry.path))

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(_parse_file, e) for e in new_or_changed]
            for future in futures:
                fp, result = future.result()
                if result is not None:
                    parse_results[fp] = result

        # 6. Symbols phase
        process_symbols(parse_results, self._storage)

        # 7. Imports phase
        process_imports(parse_results, self._storage)

        # 8. Update file hashes
        for entry in new_or_changed:
            self._storage.update_file_hash(str(entry.path), entry.content_hash)

        return {
            "files_indexed": len(new_or_changed),
            "files_skipped": skipped,
            "files_removed": removed,
        }

    def is_indexed(self) -> bool:
        """Return True if any files have been indexed."""
        return bool(self._storage.get_indexed_files())

    def query(self, search_term: str, limit: int = 20) -> list[tuple[GraphNode, float]]:
        """Search the graph for nodes matching search_term."""
        return self._storage.search(search_term, limit=limit)

    def nodes_in_file(self, file_path: str) -> list[GraphNode]:
        """Return all graph nodes for a given file."""
        return self._storage.get_nodes_by_file(file_path)

    def close(self) -> None:
        """Close the graph storage."""
        self._storage.close()
