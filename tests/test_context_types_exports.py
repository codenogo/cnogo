"""Type annotation and exports phase tests."""

from __future__ import annotations

import textwrap

import pytest

from tests.conftest_context import make_export_storage, make_storage_with_nodes


# --- types phase (USES_TYPE edges) ---


def test_uses_type_edges_from_param_annotations(tmp_path):
    """USES_TYPE edges should be created from function parameter annotations."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType

    db = make_storage_with_nodes(tmp_path)

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            type_refs=[
                TypeRef(name="MyClass", kind="param", line=12),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target, type FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    source, target, rel_type = rows[0]
    assert source == "function:mymodule.py:my_func"
    assert target == "class:mymodule.py:MyClass"
    assert rel_type == RelType.USES_TYPE.value
    db.close()


def test_uses_type_edges_from_return_annotations(tmp_path):
    """USES_TYPE edges should be created from return type annotations."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test2.db")
    db.initialize()

    class_node = GraphNode(
        id="class:service.py:Response",
        label=NodeLabel.CLASS,
        name="Response",
        file_path="service.py",
        start_line=1,
        end_line=5,
    )
    func_node = GraphNode(
        id="function:service.py:get_response",
        label=NodeLabel.FUNCTION,
        name="get_response",
        file_path="service.py",
        start_line=7,
        end_line=12,
    )
    db.add_nodes([class_node, func_node])

    parse_results = {
        "service.py": ParseResult(
            file_path="service.py",
            type_refs=[
                TypeRef(name="Response", kind="return", line=7),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target, type FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    source, target, rel_type = rows[0]
    assert source == "function:service.py:get_response"
    assert target == "class:service.py:Response"
    db.close()


def test_uses_type_resolves_same_file_class(tmp_path):
    """USES_TYPE edges should resolve to same-file class nodes."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "test3.db")
    db.initialize()

    class_a = GraphNode(
        id="class:file_a.py:Widget",
        label=NodeLabel.CLASS,
        name="Widget",
        file_path="file_a.py",
        start_line=1,
        end_line=5,
    )
    class_b = GraphNode(
        id="class:file_b.py:Widget",
        label=NodeLabel.CLASS,
        name="Widget",
        file_path="file_b.py",
        start_line=1,
        end_line=5,
    )
    func_node = GraphNode(
        id="function:file_a.py:render",
        label=NodeLabel.FUNCTION,
        name="render",
        file_path="file_a.py",
        start_line=7,
        end_line=10,
    )
    db.add_nodes([class_a, class_b, func_node])

    parse_results = {
        "file_a.py": ParseResult(
            file_path="file_a.py",
            type_refs=[
                TypeRef(name="Widget", kind="param", line=7),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 1
    source, target = rows[0]
    assert target == "class:file_a.py:Widget"
    db.close()


def test_uses_type_no_edge_for_unresolvable_type(tmp_path):
    """No USES_TYPE edges should be created for unresolvable type names."""
    from scripts.context.phases.types import process_types
    from scripts.context.python_parser import ParseResult, TypeRef
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage

    db = GraphStorage(tmp_path / "test4.db")
    db.initialize()

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            type_refs=[
                TypeRef(name="str", kind="param", line=5),
                TypeRef(name="int", kind="return", line=5),
                TypeRef(name="NonExistentClass", kind="param", line=5),
            ],
        )
    }

    process_types(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.USES_TYPE.value,),
    )
    count = cur.fetchone()[0]
    assert count == 0
    db.close()


def test_uses_type_pipeline_integration(tmp_path):
    """index() pipeline should produce USES_TYPE edges for typed functions."""
    from scripts.context import ContextGraph
    from scripts.context.model import RelType

    source = textwrap.dedent("""\
        class MyModel:
            pass

        def process(obj: MyModel) -> MyModel:
            return obj
    """)
    (tmp_path / "typed_module.py").write_text(source)

    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        assert g._storage._conn is not None
        cur = g._storage._conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE type = ?",
            (RelType.USES_TYPE.value,),
        )
        count = cur.fetchone()[0]
        assert count >= 1
    finally:
        g.close()


# --- exports phase (EXPORTS edges) ---


def test_exports_edges_created_from_all_list(tmp_path):
    """EXPORTS edges should be created from __all__ entries."""
    from scripts.context.phases.exports import process_exports
    from scripts.context.python_parser import ParseResult
    from scripts.context.model import RelType

    db = make_export_storage(tmp_path, "exp1.db")

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            exports=["my_func", "MyClass"],
        )
    }

    process_exports(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT source, target, type FROM relationships WHERE type = ?",
        (RelType.EXPORTS.value,),
    )
    rows = cur.fetchall()
    assert len(rows) == 2
    targets = {row[1] for row in rows}
    assert "function:mymodule.py:my_func" in targets
    assert "class:mymodule.py:MyClass" in targets
    db.close()


def test_exports_sets_is_exported_true(tmp_path):
    """Exported symbols should have is_exported=True after process_exports."""
    from scripts.context.phases.exports import process_exports
    from scripts.context.python_parser import ParseResult

    db = make_export_storage(tmp_path, "exp2.db")

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            exports=["my_func"],
        )
    }

    process_exports(parse_results, db)

    node = db.get_node("function:mymodule.py:my_func")
    assert node is not None
    assert node.is_exported is True
    db.close()


def test_exports_no_edge_for_unknown_name(tmp_path):
    """No EXPORTS edges should be created for names not found in the graph."""
    from scripts.context.phases.exports import process_exports
    from scripts.context.python_parser import ParseResult
    from scripts.context.model import RelType

    db = make_export_storage(tmp_path, "exp3.db")

    parse_results = {
        "mymodule.py": ParseResult(
            file_path="mymodule.py",
            exports=["nonexistent_symbol"],
        )
    }

    process_exports(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.EXPORTS.value,),
    )
    count = cur.fetchone()[0]
    assert count == 0
    db.close()


def test_exports_multiple_from_same_file(tmp_path):
    """Multiple exports from same file should produce one edge per symbol."""
    from scripts.context.phases.exports import process_exports
    from scripts.context.python_parser import ParseResult
    from scripts.context.model import RelType
    from scripts.context.storage import GraphStorage
    from scripts.context.model import GraphNode, NodeLabel

    db = GraphStorage(tmp_path / "exp4.db")
    db.initialize()

    file_node = GraphNode(
        id="file:pkg.py:",
        label=NodeLabel.FILE,
        name="pkg.py",
        file_path="pkg.py",
    )
    nodes = [file_node]
    for i in range(4):
        nodes.append(GraphNode(
            id=f"function:pkg.py:func_{i}",
            label=NodeLabel.FUNCTION,
            name=f"func_{i}",
            file_path="pkg.py",
            start_line=i * 5 + 1,
            end_line=i * 5 + 5,
        ))
    db.add_nodes(nodes)

    parse_results = {
        "pkg.py": ParseResult(
            file_path="pkg.py",
            exports=["func_0", "func_1", "func_2", "func_3"],
        )
    }

    process_exports(parse_results, db)

    assert db._conn is not None
    cur = db._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.EXPORTS.value,),
    )
    count = cur.fetchone()[0]
    assert count == 4
    db.close()


def test_exports_pipeline_integration(tmp_path):
    """index() pipeline should produce EXPORTS edges from __all__."""
    from scripts.context import ContextGraph
    from scripts.context.model import RelType

    source = textwrap.dedent("""\
        __all__ = ["exported_func", "ExportedClass"]

        def exported_func():
            pass

        class ExportedClass:
            pass

        def _private():
            pass
    """)
    (tmp_path / "exports_module.py").write_text(source)

    g = ContextGraph(repo_path=tmp_path)
    try:
        g.index()
        assert g._storage._conn is not None
        cur = g._storage._conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE type = ?",
            (RelType.EXPORTS.value,),
        )
        count = cur.fetchone()[0]
        assert count >= 2

        func_nodes = g.query("exported_func")
        assert len(func_nodes) >= 1
        assert func_nodes[0].is_exported is True
    finally:
        g.close()
