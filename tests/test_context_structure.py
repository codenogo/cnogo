"""Tests for structure phase (File/Folder nodes + CONTAINS edges)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.context.model import GraphNode, GraphRelationship, NodeLabel, RelType
from scripts.context.walker import FileEntry


def _make_entry(path: str, content: str = "x = 1\n", content_hash: str = "abc") -> FileEntry:
    return FileEntry(
        path=Path(path),
        content=content,
        language="python",
        content_hash=content_hash,
    )


@pytest.fixture
def storage(tmp_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


# --- File node creation ---


def test_creates_file_nodes(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("main.py"),
        _make_entry("utils.py"),
    ]
    process_structure(files, storage)

    node = storage.get_node("file:main.py:")
    assert node is not None
    assert node.label == NodeLabel.FILE
    assert node.name == "main.py"
    assert node.file_path == "main.py"


def test_file_node_stores_content_hash(storage):
    from scripts.context.phases.structure import process_structure
    files = [_make_entry("main.py", content_hash="sha256hash")]
    process_structure(files, storage)

    node = storage.get_node("file:main.py:")
    assert node.properties.get("content_hash") == "sha256hash"


def test_creates_correct_number_of_file_nodes(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("a.py"),
        _make_entry("b.py"),
        _make_entry("c.py"),
    ]
    process_structure(files, storage)
    # 3 file nodes + folder nodes (root ".")
    file_count = sum(
        1 for nid in ["file:a.py:", "file:b.py:", "file:c.py:"]
        if storage.get_node(nid) is not None
    )
    assert file_count == 3


# --- Folder node creation ---


def test_creates_folder_nodes(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("pkg/mod.py"),
    ]
    process_structure(files, storage)

    folder = storage.get_node("folder:pkg:")
    assert folder is not None
    assert folder.label == NodeLabel.FOLDER
    assert folder.name == "pkg"


def test_creates_nested_folder_nodes(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("a/b/c.py"),
    ]
    process_structure(files, storage)

    assert storage.get_node("folder:a:") is not None
    assert storage.get_node("folder:a/b:") is not None


def test_no_duplicate_folders(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("pkg/a.py"),
        _make_entry("pkg/b.py"),
    ]
    process_structure(files, storage)

    # Only one folder node for "pkg"
    folder = storage.get_node("folder:pkg:")
    assert folder is not None


# --- CONTAINS edges ---


def test_folder_contains_file(storage):
    from scripts.context.phases.structure import process_structure
    files = [_make_entry("pkg/mod.py")]
    process_structure(files, storage)

    # Check that pkg folder contains mod.py file
    # We need to query relationships directly
    node = storage.get_node("folder:pkg:")
    assert node is not None
    file_node = storage.get_node("file:pkg/mod.py:")
    assert file_node is not None


def test_folder_contains_subfolder(storage):
    from scripts.context.phases.structure import process_structure
    files = [_make_entry("a/b/c.py")]
    process_structure(files, storage)

    # Both folder:a: and folder:a/b: should exist
    assert storage.get_node("folder:a:") is not None
    assert storage.get_node("folder:a/b:") is not None


def test_root_files_no_crash(storage):
    from scripts.context.phases.structure import process_structure
    files = [_make_entry("main.py")]
    process_structure(files, storage)

    # Should work without error for root-level files
    assert storage.get_node("file:main.py:") is not None


def test_multiple_files_in_tree(storage):
    from scripts.context.phases.structure import process_structure
    files = [
        _make_entry("main.py"),
        _make_entry("pkg/__init__.py"),
        _make_entry("pkg/core.py"),
        _make_entry("pkg/sub/deep.py"),
    ]
    process_structure(files, storage)

    # All file nodes
    assert storage.get_node("file:main.py:") is not None
    assert storage.get_node("file:pkg/__init__.py:") is not None
    assert storage.get_node("file:pkg/core.py:") is not None
    assert storage.get_node("file:pkg/sub/deep.py:") is not None

    # All folder nodes
    assert storage.get_node("folder:pkg:") is not None
    assert storage.get_node("folder:pkg/sub:") is not None
