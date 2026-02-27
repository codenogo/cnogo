"""Tests for the full context graph indexing pipeline."""

from __future__ import annotations

import os

import pytest

from scripts.context.model import NodeLabel, RelType, generate_id


@pytest.fixture
def repo(tmp_path):
    """Create a small Python project to index."""
    # utils.py
    (tmp_path / "utils.py").write_text(
        "def helper(x):\n"
        "    return x + 1\n"
    )
    # main.py
    (tmp_path / "main.py").write_text(
        "from utils import helper\n"
        "\n"
        "def run():\n"
        "    return helper(42)\n"
    )
    # pkg/__init__.py
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    # pkg/svc.py
    (pkg / "svc.py").write_text(
        "class Base:\n"
        "    def process(self):\n"
        "        pass\n"
        "\n"
        "class Service(Base):\n"
        "    def run(self):\n"
        "        self.process()\n"
    )
    return tmp_path


def test_pipeline_creates_file_nodes(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    assert g._storage._conn is not None
    cur = g._storage._conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE label = ?",
        (NodeLabel.FILE.value,),
    )
    count = cur.fetchone()[0]
    # At least utils.py, main.py, pkg/__init__.py, pkg/svc.py
    assert count >= 4
    g.close()


def test_pipeline_creates_folder_nodes(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE label = ?",
        (NodeLabel.FOLDER.value,),
    )
    count = cur.fetchone()[0]
    assert count >= 1  # at least "pkg"
    g.close()


def test_pipeline_creates_function_nodes(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT name FROM nodes WHERE label = ?",
        (NodeLabel.FUNCTION.value,),
    )
    names = {row[0] for row in cur.fetchall()}
    assert "helper" in names
    assert "run" in names
    g.close()


def test_pipeline_creates_class_nodes(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT name FROM nodes WHERE label = ?",
        (NodeLabel.CLASS.value,),
    )
    names = {row[0] for row in cur.fetchall()}
    assert "Base" in names
    assert "Service" in names
    g.close()


def test_pipeline_creates_imports_edges(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.IMPORTS.value,),
    )
    count = cur.fetchone()[0]
    assert count >= 1  # main.py → utils.py
    g.close()


def test_pipeline_creates_calls_edges(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.CALLS.value,),
    )
    count = cur.fetchone()[0]
    assert count >= 1  # run() → helper()
    g.close()


def test_pipeline_creates_extends_edges(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    cur = g._storage._conn.execute(
        "SELECT COUNT(*) FROM relationships WHERE type = ?",
        (RelType.EXTENDS.value,),
    )
    count = cur.fetchone()[0]
    assert count >= 1  # Service extends Base
    g.close()


def test_pipeline_incremental_skips_unchanged(repo):
    """Second index() call should be fast — unchanged files skipped."""
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    # Get node count after first index
    count1 = g._storage.node_count()

    # Index again — no files changed
    g.index()
    count2 = g._storage.node_count()

    assert count1 == count2
    g.close()


def test_pipeline_incremental_detects_changes(repo):
    """Modified files should be re-indexed."""
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    # Modify utils.py
    (repo / "utils.py").write_text(
        "def helper(x):\n"
        "    return x + 1\n"
        "\n"
        "def new_func():\n"
        "    return 42\n"
    )

    g.index()

    # Should now have new_func
    cur = g._storage._conn.execute(
        "SELECT name FROM nodes WHERE label = ? AND file_path LIKE ?",
        (NodeLabel.FUNCTION.value, "%utils.py"),
    )
    names = {row[0] for row in cur.fetchall()}
    assert "new_func" in names
    assert "helper" in names
    g.close()


def test_pipeline_query_by_name(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    results = g.query("helper")
    assert len(results) >= 1
    assert any(n.name == "helper" for n in results)
    g.close()


def test_pipeline_query_no_match(repo):
    from scripts.context import ContextGraph
    g = ContextGraph(repo)
    g.index()

    results = g.query("nonexistent_function_xyz")
    assert len(results) == 0
    g.close()
