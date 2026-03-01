"""Tests for the heritage phase: EXTENDS and IMPLEMENTS relationships."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import sys
sys.path.insert(0, ".cnogo")

from scripts.context.model import NodeLabel, RelType, GraphNode, GraphRelationship, generate_id
from scripts.context.storage import GraphStorage
from scripts.context.parser_base import ParseResult, SymbolInfo, TypeRef, ImportInfo, CallInfo
from scripts.context.phases.structure import process_structure
from scripts.context.phases.symbols import process_symbols
from scripts.context.walker import FileEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file_entry(path_str: str, content: str = "") -> FileEntry:
    return FileEntry(
        path=Path(path_str),
        language="python",
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


def _setup_graph(tmp_path, files: list[FileEntry], parse_results: dict[str, ParseResult]) -> GraphStorage:
    """Create graph with structure + symbol nodes."""
    storage = GraphStorage(tmp_path / "db")
    storage.initialize()
    process_structure(files, storage)
    process_symbols(parse_results, storage)
    return storage


@pytest.fixture
def storage(tmp_path):
    s = GraphStorage(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Heritage tests
# ---------------------------------------------------------------------------

def test_heritage_extends_same_file(tmp_path):
    """class Dog(Animal) in same file -> EXTENDS relationship."""
    from scripts.context.phases.heritage import process_heritage

    content = "class Animal:\n    pass\n\nclass Dog(Animal):\n    pass\n"
    files = [_make_file_entry("models.py", content)]
    parse_results = {
        "models.py": ParseResult(
            symbols=[
                SymbolInfo(name="Animal", kind="class", start_line=1, end_line=2),
                SymbolInfo(name="Dog", kind="class", start_line=4, end_line=5),
            ],
            heritage=[("Dog", "Animal", "extends")],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    dog_id = generate_id(NodeLabel.CLASS, "models.py", "Dog")
    related = storage.get_related_nodes(dog_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "Animal"
    storage.close()


def test_heritage_extends_cross_file(tmp_path):
    """Child in file A, parent in file B -> EXTENDS."""
    from scripts.context.phases.heritage import process_heritage

    files = [
        _make_file_entry("base.py", "class Animal:\n    pass\n"),
        _make_file_entry("child.py", "class Dog(Animal):\n    pass\n"),
    ]
    parse_results = {
        "base.py": ParseResult(
            symbols=[SymbolInfo(name="Animal", kind="class", start_line=1, end_line=2)],
        ),
        "child.py": ParseResult(
            symbols=[SymbolInfo(name="Dog", kind="class", start_line=1, end_line=2)],
            heritage=[("Dog", "Animal", "extends")],
        ),
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    dog_id = generate_id(NodeLabel.CLASS, "child.py", "Dog")
    related = storage.get_related_nodes(dog_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "Animal"
    storage.close()


def test_heritage_implements(tmp_path):
    """class User implements ISerializable -> IMPLEMENTS."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("svc.py")]
    parse_results = {
        "svc.py": ParseResult(
            symbols=[
                SymbolInfo(name="ISerializable", kind="interface", start_line=1, end_line=3),
                SymbolInfo(name="User", kind="class", start_line=5, end_line=15),
            ],
            heritage=[("User", "ISerializable", "implements")],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    user_id = generate_id(NodeLabel.CLASS, "svc.py", "User")
    related = storage.get_related_nodes(user_id, RelType.IMPLEMENTS, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "ISerializable"
    storage.close()


def test_heritage_multiple_parents(tmp_path):
    """class Dog(Animal, Pet) -> two EXTENDS relationships."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[
                SymbolInfo(name="Animal", kind="class", start_line=1, end_line=2),
                SymbolInfo(name="Pet", kind="class", start_line=4, end_line=5),
                SymbolInfo(name="Dog", kind="class", start_line=7, end_line=10),
            ],
            heritage=[
                ("Dog", "Animal", "extends"),
                ("Dog", "Pet", "extends"),
            ],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    dog_id = generate_id(NodeLabel.CLASS, "models.py", "Dog")
    related = storage.get_related_nodes(dog_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 2
    names = {n.name for n in related}
    assert names == {"Animal", "Pet"}
    storage.close()


def test_heritage_extends_and_implements(tmp_path):
    """class Foo extends Bar implements IBaz -> EXTENDS + IMPLEMENTS."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("code.py")]
    parse_results = {
        "code.py": ParseResult(
            symbols=[
                SymbolInfo(name="Bar", kind="class", start_line=1, end_line=2),
                SymbolInfo(name="IBaz", kind="interface", start_line=4, end_line=5),
                SymbolInfo(name="Foo", kind="class", start_line=7, end_line=15),
            ],
            heritage=[
                ("Foo", "Bar", "extends"),
                ("Foo", "IBaz", "implements"),
            ],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    foo_id = generate_id(NodeLabel.CLASS, "code.py", "Foo")
    extends_rels = storage.get_related_nodes(foo_id, RelType.EXTENDS, direction="outgoing")
    implements_rels = storage.get_related_nodes(foo_id, RelType.IMPLEMENTS, direction="outgoing")
    assert len(extends_rels) == 1
    assert extends_rels[0].name == "Bar"
    assert len(implements_rels) == 1
    assert implements_rels[0].name == "IBaz"
    storage.close()


def test_heritage_parent_not_in_graph(tmp_path):
    """Parent class not indexed -> no crash, no relationship."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[SymbolInfo(name="Dog", kind="class", start_line=1, end_line=5)],
            heritage=[("Dog", "MissingParent", "extends")],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    # Should not crash
    process_heritage(parse_results, storage)

    dog_id = generate_id(NodeLabel.CLASS, "models.py", "Dog")
    related = storage.get_related_nodes(dog_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 0
    storage.close()


def test_heritage_child_not_in_graph(tmp_path):
    """Child class not indexed -> no crash, no relationship."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[SymbolInfo(name="Animal", kind="class", start_line=1, end_line=5)],
            # MissingChild is in heritage but NOT in symbols
            heritage=[("MissingChild", "Animal", "extends")],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    # Should not crash
    process_heritage(parse_results, storage)

    animal_id = generate_id(NodeLabel.CLASS, "models.py", "Animal")
    # No incoming EXTENDS edges to Animal
    related = storage.get_related_nodes(animal_id, RelType.EXTENDS, direction="incoming")
    assert len(related) == 0
    storage.close()


def test_heritage_empty_results(tmp_path):
    """Empty parse_results -> no crash."""
    from scripts.context.phases.heritage import process_heritage

    storage = GraphStorage(tmp_path / "db")
    storage.initialize()

    # Should not crash
    process_heritage({}, storage)

    storage.close()


def test_heritage_dedup(tmp_path):
    """Same heritage tuple appearing twice -> only one relationship created."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("models.py")]
    parse_results = {
        "models.py": ParseResult(
            symbols=[
                SymbolInfo(name="Animal", kind="class", start_line=1, end_line=2),
                SymbolInfo(name="Dog", kind="class", start_line=4, end_line=8),
            ],
            heritage=[
                ("Dog", "Animal", "extends"),
                ("Dog", "Animal", "extends"),  # duplicate
            ],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    dog_id = generate_id(NodeLabel.CLASS, "models.py", "Dog")
    related = storage.get_related_nodes(dog_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 1
    storage.close()


def test_heritage_interface_extends(tmp_path):
    """Interface IB extends IA -> EXTENDS relationship."""
    from scripts.context.phases.heritage import process_heritage

    files = [_make_file_entry("types.py")]
    parse_results = {
        "types.py": ParseResult(
            symbols=[
                SymbolInfo(name="IA", kind="interface", start_line=1, end_line=3),
                SymbolInfo(name="IB", kind="class", start_line=5, end_line=7),
            ],
            heritage=[("IB", "IA", "extends")],
        )
    }
    storage = _setup_graph(tmp_path, files, parse_results)

    process_heritage(parse_results, storage)

    ib_id = generate_id(NodeLabel.CLASS, "types.py", "IB")
    related = storage.get_related_nodes(ib_id, RelType.EXTENDS, direction="outgoing")
    assert len(related) == 1
    assert related[0].name == "IA"
    storage.close()
