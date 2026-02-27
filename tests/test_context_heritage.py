"""Tests for heritage extraction phase."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.context.model import (
    GraphNode,
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import ParseResult, SymbolInfo


@pytest.fixture
def storage(tmp_path):
    from scripts.context.storage import GraphStorage
    s = GraphStorage(tmp_path / "test.db")
    s.initialize()
    yield s
    s.close()


def _add_file_node(storage, file_path):
    node_id = generate_id(NodeLabel.FILE, file_path, "")
    storage.add_nodes([GraphNode(
        id=node_id,
        label=NodeLabel.FILE,
        name=Path(file_path).name,
        file_path=file_path,
    )])
    return node_id


def _add_class_node(storage, file_path, name, start_line=1, end_line=10):
    node_id = generate_id(NodeLabel.CLASS, file_path, name)
    storage.add_nodes([GraphNode(
        id=node_id,
        label=NodeLabel.CLASS,
        name=name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
    )])
    return node_id


# --- process_heritage: EXTENDS ---


def test_heritage_creates_extends_edge(storage):
    from scripts.context.phases.heritage import process_heritage

    _add_file_node(storage, "models.py")
    _add_class_node(storage, "models.py", "Animal", 1, 10)
    _add_class_node(storage, "models.py", "Dog", 12, 20)

    parse_results = {
        "models.py": ParseResult(
            file_path="models.py",
            symbols=[
                SymbolInfo(name="Animal", kind="class", start_line=1, end_line=10),
                SymbolInfo(name="Dog", kind="class", start_line=12, end_line=20),
            ],
            heritage=[("Dog", "extends", "Animal")],
        ),
    }
    process_heritage(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.EXTENDS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    dog_id = generate_id(NodeLabel.CLASS, "models.py", "Dog")
    animal_id = generate_id(NodeLabel.CLASS, "models.py", "Animal")
    assert row[0] == dog_id
    assert row[1] == animal_id


def test_heritage_skips_unresolvable_parent(storage):
    from scripts.context.phases.heritage import process_heritage

    _add_file_node(storage, "models.py")
    _add_class_node(storage, "models.py", "Dog", 1, 10)

    parse_results = {
        "models.py": ParseResult(
            file_path="models.py",
            symbols=[
                SymbolInfo(name="Dog", kind="class", start_line=1, end_line=10),
            ],
            heritage=[("Dog", "extends", "UnknownBase")],
        ),
    }
    process_heritage(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT * FROM relationships WHERE type = ?",
        (RelType.EXTENDS.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 0


def test_heritage_cross_file_extends(storage):
    from scripts.context.phases.heritage import process_heritage

    _add_file_node(storage, "base.py")
    _add_file_node(storage, "child.py")
    _add_class_node(storage, "base.py", "Base", 1, 10)
    _add_class_node(storage, "child.py", "Child", 1, 10)

    parse_results = {
        "child.py": ParseResult(
            file_path="child.py",
            symbols=[
                SymbolInfo(name="Child", kind="class", start_line=1, end_line=10),
            ],
            heritage=[("Child", "extends", "Base")],
        ),
    }
    process_heritage(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.EXTENDS.value,),
    )
    row = cur.fetchone()
    assert row is not None
    child_id = generate_id(NodeLabel.CLASS, "child.py", "Child")
    base_id = generate_id(NodeLabel.CLASS, "base.py", "Base")
    assert row[0] == child_id
    assert row[1] == base_id


def test_heritage_implements_edge(storage):
    from scripts.context.phases.heritage import process_heritage

    _add_file_node(storage, "svc.py")
    iface_id = generate_id(NodeLabel.INTERFACE, "svc.py", "Serializable")
    storage.add_nodes([GraphNode(
        id=iface_id,
        label=NodeLabel.INTERFACE,
        name="Serializable",
        file_path="svc.py",
        start_line=1,
        end_line=5,
    )])
    _add_class_node(storage, "svc.py", "User", 7, 20)

    parse_results = {
        "svc.py": ParseResult(
            file_path="svc.py",
            symbols=[
                SymbolInfo(name="User", kind="class", start_line=7, end_line=20),
            ],
            heritage=[("User", "implements", "Serializable")],
        ),
    }
    process_heritage(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.IMPLEMENTS.value,),
    )
    row = cur.fetchone()
    assert row is not None


# --- process_symbols ---


def test_symbols_creates_function_node(storage):
    from scripts.context.phases.symbols import process_symbols

    _add_file_node(storage, "utils.py")

    parse_results = {
        "utils.py": ParseResult(
            file_path="utils.py",
            symbols=[
                SymbolInfo(name="helper", kind="function", start_line=1, end_line=5, signature="(x, y)"),
            ],
        ),
    }
    process_symbols(parse_results, storage)

    node_id = generate_id(NodeLabel.FUNCTION, "utils.py", "helper")
    node = storage.get_node(node_id)
    assert node is not None
    assert node.name == "helper"
    assert node.signature == "(x, y)"
    assert node.start_line == 1
    assert node.end_line == 5


def test_symbols_creates_class_and_method_nodes(storage):
    from scripts.context.phases.symbols import process_symbols

    _add_file_node(storage, "svc.py")

    parse_results = {
        "svc.py": ParseResult(
            file_path="svc.py",
            symbols=[
                SymbolInfo(name="Service", kind="class", start_line=1, end_line=20),
                SymbolInfo(name="run", kind="method", start_line=3, end_line=10, class_name="Service"),
            ],
        ),
    }
    process_symbols(parse_results, storage)

    cls_id = generate_id(NodeLabel.CLASS, "svc.py", "Service")
    method_id = generate_id(NodeLabel.METHOD, "svc.py", "run")
    assert storage.get_node(cls_id) is not None
    assert storage.get_node(method_id) is not None
    method = storage.get_node(method_id)
    assert method.class_name == "Service"


def test_symbols_creates_defines_edge(storage):
    from scripts.context.phases.symbols import process_symbols

    _add_file_node(storage, "utils.py")

    parse_results = {
        "utils.py": ParseResult(
            file_path="utils.py",
            symbols=[
                SymbolInfo(name="helper", kind="function", start_line=1, end_line=5),
            ],
        ),
    }
    process_symbols(parse_results, storage)

    cur = storage._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.DEFINES.value,),
    )
    row = cur.fetchone()
    assert row is not None
    file_id = generate_id(NodeLabel.FILE, "utils.py", "")
    func_id = generate_id(NodeLabel.FUNCTION, "utils.py", "helper")
    assert row[0] == file_id
    assert row[1] == func_id


def test_symbols_stores_decorators(storage):
    from scripts.context.phases.symbols import process_symbols

    _add_file_node(storage, "app.py")

    parse_results = {
        "app.py": ParseResult(
            file_path="app.py",
            symbols=[
                SymbolInfo(name="index", kind="function", start_line=1, end_line=5,
                           decorators=["route", "login_required"]),
            ],
        ),
    }
    process_symbols(parse_results, storage)

    node_id = generate_id(NodeLabel.FUNCTION, "app.py", "index")
    node = storage.get_node(node_id)
    assert node is not None
    assert node.properties.get("decorators") == ["route", "login_required"]
