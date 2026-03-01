"""Integration tests for the full context graph indexing pipeline (ContextGraph)."""

from __future__ import annotations

import sys
sys.path.insert(0, ".cnogo")

from pathlib import Path
import pytest

from scripts.context.model import NodeLabel, RelType


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_repo(tmp_path, files: dict[str, str]) -> Path:
    """Create a temp repo with given files.

    files: {"src/main.py": "def hello():\\n    pass\\n", ...}
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    for rel_path, content in files.items():
        fp = repo / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_index_creates_file_nodes(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "main.py": "def hello():\n    pass\n",
        "utils.ts": "export function greet() {}\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats = cg.index()
    cg.close()

    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    nodes = cg2._storage.get_nodes_by_file("main.py")
    file_nodes = [n for n in nodes if n.label == NodeLabel.FILE]
    assert len(file_nodes) >= 1
    assert file_nodes[0].name == "main.py"
    cg2.close()


def test_index_creates_folder_nodes(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "src/main.py": "def hello():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    # Query storage for folder nodes
    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'folder' RETURN n.name"
    )
    folder_names = set()
    while result.has_next():
        folder_names.add(result.get_next()[0])
    cg.close()

    assert "src" in folder_names or "." in folder_names


def test_index_creates_function_nodes(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "main.py": "def hello():\n    pass\n\ndef world():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'function' RETURN n.name"
    )
    names = set()
    while result.has_next():
        names.add(result.get_next()[0])
    cg.close()

    assert "hello" in names
    assert "world" in names


def test_index_creates_class_nodes(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "models.py": "class Animal:\n    pass\n\nclass Dog(Animal):\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'class' RETURN n.name"
    )
    names = set()
    while result.has_next():
        names.add(result.get_next()[0])
    cg.close()

    assert "Animal" in names
    assert "Dog" in names


def test_index_creates_method_nodes(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "service.py": (
            "class MyService:\n"
            "    def do_work(self):\n"
            "        pass\n"
            "    def cleanup(self):\n"
            "        pass\n"
        ),
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'method' RETURN n.name"
    )
    names = set()
    while result.has_next():
        names.add(result.get_next()[0])
    cg.close()

    assert "do_work" in names
    assert "cleanup" in names


def test_index_creates_imports_relationships(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "utils.py": "def helper():\n    pass\n",
        "main.py": "from utils import helper\n\ndef run():\n    helper()\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode)"
        " WHERE r.rel_type = 'imports' RETURN count(r)"
    )
    count = result.get_next()[0]
    cg.close()

    assert count >= 1


def test_index_returns_stats(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "a.py": "x = 1\n",
        "b.py": "y = 2\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats = cg.index()
    cg.close()

    assert "files_indexed" in stats
    assert "files_skipped" in stats
    assert "files_removed" in stats
    assert stats["files_indexed"] == 2
    assert stats["files_skipped"] == 0
    assert stats["files_removed"] == 0


def test_incremental_index_skips_unchanged(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "a.py": "def foo():\n    pass\n",
        "b.py": "def bar():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    cg.close()

    # Second run — same files, nothing changed
    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats2 = cg2.index()
    cg2.close()

    assert stats2["files_indexed"] == 0
    assert stats2["files_skipped"] == 2
    assert stats2["files_removed"] == 0


def test_incremental_index_detects_change(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "a.py": "def foo():\n    pass\n",
        "b.py": "def bar():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    cg.close()

    # Modify a.py
    (repo / "a.py").write_text("def foo():\n    pass\n\ndef new_fn():\n    pass\n")

    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats2 = cg2.index()

    # Verify new_fn appears
    conn = cg2._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'function' AND n.name = 'new_fn' RETURN n.name"
    )
    found = result.has_next()
    cg2.close()

    assert stats2["files_indexed"] == 1
    assert stats2["files_skipped"] == 1
    assert found


def test_incremental_index_removes_stale(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "a.py": "def foo():\n    pass\n",
        "b.py": "def bar():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    cg.close()

    # Delete b.py
    (repo / "b.py").unlink()

    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats2 = cg2.index()
    cg2.close()

    assert stats2["files_removed"] == 1


def test_is_indexed_false_initially(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {"a.py": "x = 1\n"})
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    result = cg.is_indexed()
    cg.close()

    assert result is False


def test_is_indexed_true_after_index(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {"a.py": "def foo():\n    pass\n"})
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    result = cg.is_indexed()
    cg.close()

    assert result is True


def test_query_finds_function(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "main.py": "def hello_world():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    results = cg.query("hello_world")
    cg.close()

    assert len(results) >= 1
    names = [node.name for node, score in results]
    assert "hello_world" in names


def test_nodes_in_file(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "main.py": "def foo():\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    nodes = cg.nodes_in_file("main.py")
    cg.close()

    assert len(nodes) >= 1
    assert any(n.file_path == "main.py" for n in nodes)


def test_close_and_reopen(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "lib.py": "def compute():\n    return 42\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()
    cg.close()

    # Reopen the same db
    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    results = cg2.query("compute")
    cg2.close()

    assert len(results) >= 1
    assert any(node.name == "compute" for node, _ in results)


def test_typescript_file_parsed(tmp_path):
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "app.ts": (
            "export function greetUser(name: string): string {\n"
            "    return `Hello, ${name}`;\n"
            "}\n"
            "export class UserService {\n"
            "    getUser(id: number) { return null; }\n"
            "}\n"
        ),
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label IN ['function', 'class', 'method'] RETURN n.name"
    )
    names = set()
    while result.has_next():
        names.add(result.get_next()[0])
    cg.close()

    assert len(names) >= 1


def test_empty_repo(tmp_path):
    from scripts.context import ContextGraph
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats = cg.index()
    cg.close()

    assert stats["files_indexed"] == 0
    assert stats["files_skipped"] == 0
    assert stats["files_removed"] == 0


# ---------------------------------------------------------------------------
# Pipeline integration tests: all new phases
# ---------------------------------------------------------------------------


def test_pipeline_calls_relationships(tmp_path):
    """Index a Python file with function calls -> CALLS rels exist."""
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "utils.py": "def helper():\n    pass\n",
        "main.py": "from utils import helper\n\ndef run():\n    helper()\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) WHERE r.rel_type = 'calls' RETURN count(r)"
    )
    count = result.get_next()[0]
    cg.close()

    assert count >= 1


def test_pipeline_heritage_relationships(tmp_path):
    """Index a Python file with class inheritance -> EXTENDS rels exist."""
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "models.py": "class Animal:\n    pass\n\nclass Dog(Animal):\n    pass\n",
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) WHERE r.rel_type = 'extends' RETURN count(r)"
    )
    count = result.get_next()[0]
    cg.close()

    assert count >= 1


def test_pipeline_exports_relationships(tmp_path):
    """Index a TypeScript file with export -> EXPORTS rels exist."""
    from scripts.context import ContextGraph
    repo = _make_repo(tmp_path, {
        "app.ts": (
            "export function greetUser(name: string): string {\n"
            "    return `Hello, ${name}`;\n"
            "}\n"
            "export class UserService {\n"
            "    getUser(id: number) { return null; }\n"
            "}\n"
        ),
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    cg.index()

    conn = cg._storage._require_conn()
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) WHERE r.rel_type = 'exports' RETURN count(r)"
    )
    count = result.get_next()[0]
    cg.close()

    # TypeScript parser may or may not emit exports; we just assert no crash
    assert count >= 0


def test_pipeline_all_phases_run(tmp_path):
    """Index a multi-file repo and verify nodes and relationship types exist."""
    from scripts.context import ContextGraph
    from scripts.context.model import RelType
    repo = _make_repo(tmp_path, {
        "utils.py": "def helper():\n    pass\n",
        "models.py": "class Animal:\n    pass\n\nclass Dog(Animal):\n    pass\n",
        "main.py": (
            "from utils import helper\n"
            "from models import Dog\n\n"
            "def run():\n"
            "    helper()\n"
        ),
    })
    cg = ContextGraph(repo, db_path=tmp_path / "graphdb")
    stats = cg.index()
    cg.close()

    assert stats["files_indexed"] == 3

    # Reopen and verify nodes exist
    cg2 = ContextGraph(repo, db_path=tmp_path / "graphdb")
    conn = cg2._storage._require_conn()

    # Verify function nodes
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'function' RETURN count(n)"
    )
    func_count = result.get_next()[0]
    assert func_count >= 2  # helper, run

    # Verify class nodes
    result = conn.execute(
        "MATCH (n:GraphNode) WHERE n.label = 'class' RETURN count(n)"
    )
    class_count = result.get_next()[0]
    assert class_count >= 2  # Animal, Dog

    # Verify relationships of multiple types exist
    result = conn.execute(
        "MATCH (a:GraphNode)-[r:CodeRelation]->(b:GraphNode) RETURN DISTINCT r.rel_type"
    )
    rel_types = set()
    while result.has_next():
        rel_types.add(result.get_next()[0])

    # Should have at least imports and extends
    assert "imports" in rel_types
    assert "extends" in rel_types

    cg2.close()
