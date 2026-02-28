"""Context graph SQLite storage backend.

Provides persistent storage for the context graph using stdlib sqlite3.
Follows memory engine's storage patterns (WAL mode, upsert).

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts.context.model import GraphNode, GraphRelationship, NodeLabel, RelType


class GraphStorage:
    """SQLite-backed storage for context graph nodes and relationships."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Create tables and indexes. Idempotent."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL DEFAULT '',
                start_line INTEGER NOT NULL DEFAULT 0,
                end_line INTEGER NOT NULL DEFAULT 0,
                content TEXT NOT NULL DEFAULT '',
                signature TEXT NOT NULL DEFAULT '',
                language TEXT NOT NULL DEFAULT '',
                class_name TEXT NOT NULL DEFAULT '',
                is_dead INTEGER NOT NULL DEFAULT 0,
                is_entry_point INTEGER NOT NULL DEFAULT 0,
                is_exported INTEGER NOT NULL DEFAULT 0,
                properties_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                properties_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS file_hashes (
                file_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);
            CREATE INDEX IF NOT EXISTS idx_nodes_file_path ON nodes(file_path);
            CREATE INDEX IF NOT EXISTS idx_rels_source ON relationships(source);
            CREATE INDEX IF NOT EXISTS idx_rels_target ON relationships(target);
            CREATE INDEX IF NOT EXISTS idx_rels_type ON relationships(type);
        """)
        self._conn.commit()

    def is_initialized(self) -> bool:
        """Check if the database has been initialized with tables."""
        if self._conn is None:
            return False
        try:
            cur = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='nodes'"
            )
            return cur.fetchone() is not None
        except sqlite3.Error:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Node CRUD ---

    def add_nodes(self, nodes: list[GraphNode]) -> None:
        """Insert or replace nodes (upsert)."""
        assert self._conn is not None
        self._conn.executemany(
            """INSERT OR REPLACE INTO nodes
               (id, label, name, file_path, start_line, end_line,
                content, signature, language, class_name,
                is_dead, is_entry_point, is_exported, properties_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    n.id,
                    n.label.value,
                    n.name,
                    n.file_path,
                    n.start_line,
                    n.end_line,
                    n.content,
                    n.signature,
                    n.language,
                    n.class_name,
                    int(n.is_dead),
                    int(n.is_entry_point),
                    int(n.is_exported),
                    json.dumps(n.properties),
                )
                for n in nodes
            ],
        )
        self._conn.commit()

    def get_node(self, node_id: str) -> GraphNode | None:
        """Retrieve a node by ID, or None if not found."""
        assert self._conn is not None
        cur = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_node(row)

    def node_count(self) -> int:
        """Return the total number of nodes."""
        assert self._conn is not None
        cur = self._conn.execute("SELECT COUNT(*) FROM nodes")
        return cur.fetchone()[0]

    # --- Relationship CRUD ---

    def add_relationships(self, rels: list[GraphRelationship]) -> None:
        """Insert or replace relationships (upsert)."""
        assert self._conn is not None
        self._conn.executemany(
            """INSERT OR REPLACE INTO relationships
               (id, type, source, target, properties_json)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    r.id,
                    r.type.value,
                    r.source,
                    r.target,
                    json.dumps(r.properties),
                )
                for r in rels
            ],
        )
        self._conn.commit()

    def get_callers(self, node_id: str) -> list[GraphNode]:
        """Get nodes that call the given node (incoming CALLS edges)."""
        assert self._conn is not None
        cur = self._conn.execute(
            """SELECT n.* FROM nodes n
               JOIN relationships r ON n.id = r.source
               WHERE r.target = ? AND r.type = ?""",
            (node_id, RelType.CALLS.value),
        )
        return [self._row_to_node(row) for row in cur.fetchall()]

    def get_callees(self, node_id: str) -> list[GraphNode]:
        """Get nodes called by the given node (outgoing CALLS edges)."""
        assert self._conn is not None
        cur = self._conn.execute(
            """SELECT n.* FROM nodes n
               JOIN relationships r ON n.id = r.target
               WHERE r.source = ? AND r.type = ?""",
            (node_id, RelType.CALLS.value),
        )
        return [self._row_to_node(row) for row in cur.fetchall()]

    def get_callers_with_confidence(
        self, node_id: str
    ) -> list[tuple[GraphNode, float]]:
        """Get callers with their confidence scores."""
        assert self._conn is not None
        cur = self._conn.execute(
            """SELECT n.*, r.properties_json FROM nodes n
               JOIN relationships r ON n.id = r.source
               WHERE r.target = ? AND r.type = ?""",
            (node_id, RelType.CALLS.value),
        )
        results = []
        for row in cur.fetchall():
            node = self._row_to_node(row[:14])
            props = json.loads(row[14])
            confidence = props.get("confidence", 1.0)
            results.append((node, confidence))
        return results

    def get_related_nodes(
        self,
        node_id: str,
        rel_type: RelType,
        direction: str = "outgoing",
    ) -> list[GraphNode]:
        """Get nodes related to node_id via edges of rel_type.

        Args:
            node_id: The anchor node ID.
            rel_type: Relationship type to traverse.
            direction: "outgoing" (node_id is source) or "incoming" (node_id is target).

        Returns:
            List of related GraphNode instances.
        """
        assert self._conn is not None
        if direction == "outgoing":
            cur = self._conn.execute(
                """SELECT n.* FROM nodes n
                   JOIN relationships r ON n.id = r.target
                   WHERE r.source = ? AND r.type = ?""",
                (node_id, rel_type.value),
            )
        else:
            cur = self._conn.execute(
                """SELECT n.* FROM nodes n
                   JOIN relationships r ON n.id = r.source
                   WHERE r.target = ? AND r.type = ?""",
                (node_id, rel_type.value),
            )
        return [self._row_to_node(row) for row in cur.fetchall()]

    # --- File hash tracking ---

    def get_indexed_files(self) -> dict[str, str]:
        """Return mapping of file_path → content_hash for all indexed files."""
        assert self._conn is not None
        cur = self._conn.execute("SELECT file_path, content_hash FROM file_hashes")
        return dict(cur.fetchall())

    def update_file_hash(self, file_path: str, content_hash: str) -> None:
        """Insert or update a file's content hash."""
        assert self._conn is not None
        self._conn.execute(
            "INSERT OR REPLACE INTO file_hashes (file_path, content_hash) VALUES (?, ?)",
            (file_path, content_hash),
        )
        self._conn.commit()

    def remove_file_hash(self, file_path: str) -> None:
        """Remove a file's content hash entry."""
        assert self._conn is not None
        self._conn.execute(
            "DELETE FROM file_hashes WHERE file_path = ?", (file_path,)
        )
        self._conn.commit()

    # --- Remove by file ---

    def remove_nodes_by_file(self, file_path: str) -> int:
        """Remove all nodes for a file and their associated relationships.

        Returns the number of nodes removed.
        """
        assert self._conn is not None
        # Get IDs of nodes to remove
        cur = self._conn.execute(
            "SELECT id FROM nodes WHERE file_path = ?", (file_path,)
        )
        node_ids = [row[0] for row in cur.fetchall()]
        if not node_ids:
            return 0

        placeholders = ",".join("?" * len(node_ids))
        # Remove relationships where source or target is being deleted
        self._conn.execute(
            f"DELETE FROM relationships WHERE source IN ({placeholders}) OR target IN ({placeholders})",
            node_ids + node_ids,
        )
        # Remove the nodes
        self._conn.execute(
            f"DELETE FROM nodes WHERE id IN ({placeholders})", node_ids
        )
        self._conn.commit()
        return len(node_ids)

    # --- Internal helpers ---

    @staticmethod
    def _row_to_node(row: tuple) -> GraphNode:
        """Convert a database row to a GraphNode."""
        return GraphNode(
            id=row[0],
            label=NodeLabel(row[1]),
            name=row[2],
            file_path=row[3],
            start_line=row[4],
            end_line=row[5],
            content=row[6],
            signature=row[7],
            language=row[8],
            class_name=row[9],
            is_dead=bool(row[10]),
            is_entry_point=bool(row[11]),
            is_exported=bool(row[12]),
            properties=json.loads(row[13]),
        )
