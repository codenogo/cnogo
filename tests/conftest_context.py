"""Shared fixtures and helpers for context graph tests."""

from __future__ import annotations

import textwrap

import pytest


@pytest.fixture
def graph(tmp_path):
    from scripts.context import ContextGraph
    g = ContextGraph(repo_path=tmp_path)
    yield g
    g.close()


def add_function_node(storage, file_path, name, label=None):
    """Add a function (or other symbol) node to storage. Returns the node ID."""
    from scripts.context.model import GraphNode, NodeLabel, generate_id
    if label is None:
        label = NodeLabel.FUNCTION
    node_id = generate_id(label, file_path, name)
    node = GraphNode(
        id=node_id,
        label=label,
        name=name,
        file_path=file_path,
        start_line=1,
    )
    storage.add_nodes([node])
    return node_id


def add_call_edge(storage, caller_id, callee_id):
    """Add a CALLS edge between two node IDs."""
    from scripts.context.model import GraphRelationship, RelType
    storage.add_relationships([
        GraphRelationship(
            id=f"calls:{caller_id}->{callee_id}",
            type=RelType.CALLS,
            source=caller_id,
            target=callee_id,
        )
    ])


def add_import_edge(storage, source_id, target_id):
    """Add an IMPORTS edge between two node IDs."""
    from scripts.context.model import GraphRelationship, RelType
    storage.add_relationships([
        GraphRelationship(
            id=f"imports:{source_id}->{target_id}",
            type=RelType.IMPORTS,
            source=source_id,
            target=target_id,
        )
    ])


def write_python_files(tmp_path):
    """Create a small repo with cross-file dependencies for impact testing."""
    (tmp_path / "lib.py").write_text(textwrap.dedent("""\
        def helper():
            pass
    """))
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from lib import helper

        def run():
            helper()
    """))
    (tmp_path / "util.py").write_text(textwrap.dedent("""\
        def standalone():
            pass
    """))


def write_docstring_files(tmp_path):
    """Create Python files with docstrings for FTS testing."""
    (tmp_path / "calculator.py").write_text(textwrap.dedent('''\
        def add_numbers(a, b):
            """Add two numbers together and return the sum."""
            return a + b

        def multiply(a, b):
            """Multiply two values and return the product."""
            return a * b

        class MathEngine:
            """A mathematical computation engine for complex calculations."""

            def compute(self, expr):
                """Evaluate a mathematical expression string."""
                pass
    '''))


def make_storage_with_nodes(tmp_path):
    """Create a GraphStorage with a function and class node for type tests."""
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test.db")
    db.initialize()

    class_node = GraphNode(
        id="class:mymodule.py:MyClass",
        label=NodeLabel.CLASS,
        name="MyClass",
        file_path="mymodule.py",
        start_line=1,
        end_line=10,
    )
    func_node = GraphNode(
        id="function:mymodule.py:my_func",
        label=NodeLabel.FUNCTION,
        name="my_func",
        file_path="mymodule.py",
        start_line=12,
        end_line=15,
    )
    db.add_nodes([class_node, func_node])
    return db


def make_export_storage(tmp_path, db_name="export_test.db"):
    """Create a GraphStorage with FILE, FUNCTION, CLASS, and METHOD nodes."""
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / db_name)
    db.initialize()

    file_node = GraphNode(
        id="file:mymodule.py:",
        label=NodeLabel.FILE,
        name="mymodule.py",
        file_path="mymodule.py",
    )
    func_node = GraphNode(
        id="function:mymodule.py:my_func",
        label=NodeLabel.FUNCTION,
        name="my_func",
        file_path="mymodule.py",
        start_line=1,
        end_line=5,
    )
    class_node = GraphNode(
        id="class:mymodule.py:MyClass",
        label=NodeLabel.CLASS,
        name="MyClass",
        file_path="mymodule.py",
        start_line=7,
        end_line=15,
    )
    db.add_nodes([file_node, func_node, class_node])
    return db
