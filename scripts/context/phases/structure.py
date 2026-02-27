"""Structure phase: creates File and Folder nodes + CONTAINS edges.

For each FileEntry, creates a FILE node. Extracts unique directory paths,
creates FOLDER nodes. Connects folders with CONTAINS relationships
(parent→child folder, folder→file).

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.storage import GraphStorage
from scripts.context.walker import FileEntry


def process_structure(files: list[FileEntry], storage: GraphStorage) -> None:
    """Create File and Folder nodes with CONTAINS edges from file entries.

    Args:
        files: List of FileEntry objects from the walker.
        storage: GraphStorage instance to write nodes/relationships to.
    """
    nodes: list[GraphNode] = []
    relationships: list[GraphRelationship] = []
    seen_folders: set[str] = set()

    for entry in files:
        file_path_str = str(PurePosixPath(entry.path))

        # Create FILE node
        file_id = generate_id(NodeLabel.FILE, file_path_str, "")
        nodes.append(GraphNode(
            id=file_id,
            label=NodeLabel.FILE,
            name=PurePosixPath(entry.path).name,
            file_path=file_path_str,
            language=entry.language,
            properties={"content_hash": entry.content_hash},
        ))

        # Extract folder chain and create FOLDER nodes + CONTAINS edges
        parts = PurePosixPath(entry.path).parts
        if len(parts) > 1:
            # File is in a subdirectory
            for i in range(1, len(parts)):
                folder_path = str(PurePosixPath(*parts[:i]))

                if folder_path not in seen_folders:
                    seen_folders.add(folder_path)
                    folder_id = generate_id(NodeLabel.FOLDER, folder_path, "")
                    nodes.append(GraphNode(
                        id=folder_id,
                        label=NodeLabel.FOLDER,
                        name=parts[i - 1],
                        file_path=folder_path,
                    ))

                    # CONTAINS edge from parent folder to this folder
                    if i > 1:
                        parent_path = str(PurePosixPath(*parts[:i - 1]))
                        parent_id = generate_id(NodeLabel.FOLDER, parent_path, "")
                        rel_id = f"contains:{parent_path}->{folder_path}"
                        relationships.append(GraphRelationship(
                            id=rel_id,
                            type=RelType.CONTAINS,
                            source=parent_id,
                            target=folder_id,
                        ))

            # CONTAINS edge from immediate parent folder to file
            parent_folder = str(PurePosixPath(*parts[:-1]))
            parent_id = generate_id(NodeLabel.FOLDER, parent_folder, "")
            rel_id = f"contains:{parent_folder}->{file_path_str}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.CONTAINS,
                source=parent_id,
                target=file_id,
            ))

    if nodes:
        storage.add_nodes(nodes)
    if relationships:
        storage.add_relationships(relationships)
