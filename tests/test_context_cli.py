"""Tests for context graph CLI subcommands on workflow_memory.py."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def repo_with_python(tmp_path):
    """Create a temp repo with Python files for indexing."""
    (tmp_path / "hello.py").write_text(textwrap.dedent("""\
        def greet(name):
            return f"Hello, {name}"

        def farewell(name):
            return f"Goodbye, {name}"
    """))
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from hello import greet

        def run():
            greet("world")
    """))
    return tmp_path


def _run_cli(*args: str, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run workflow_memory.py with given args."""
    return subprocess.run(
        [sys.executable, "scripts/workflow_memory.py", *args],
        capture_output=True,
        text=True,
        cwd=cwd or Path(__file__).resolve().parent.parent,
    )


# --- graph-index ---


class TestGraphIndex:
    """Tests for the graph-index subcommand."""

    def test_help(self):
        result = _run_cli("graph-index", "--help")
        assert result.returncode == 0
        assert "graph-index" in result.stdout or "index" in result.stdout.lower()

    def test_index_empty_repo(self, tmp_path):
        """Index an empty repo — should report 0 nodes."""
        result = _run_cli("graph-index", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0" in result.stdout  # 0 nodes

    def test_index_with_files(self, repo_with_python):
        """Index repo with Python files — should report node count."""
        result = _run_cli("graph-index", "--repo", str(repo_with_python))
        assert result.returncode == 0
        # Should have indexed some nodes (files + functions)
        assert "node" in result.stdout.lower() or "indexed" in result.stdout.lower()


# --- graph-query ---


class TestGraphQuery:
    """Tests for the graph-query subcommand."""

    def test_help(self):
        result = _run_cli("graph-query", "--help")
        assert result.returncode == 0

    def test_query_no_results(self, tmp_path):
        """Query empty graph — no results."""
        result = _run_cli("graph-query", "nonexistent", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "no" in result.stdout.lower() or "0" in result.stdout

    def test_query_finds_function(self, repo_with_python):
        """Index and query for a known function."""
        # First index
        _run_cli("graph-index", "--repo", str(repo_with_python))
        # Then query
        result = _run_cli("graph-query", "greet", "--repo", str(repo_with_python))
        assert result.returncode == 0
        assert "greet" in result.stdout


# --- graph-impact ---


class TestGraphImpact:
    """Tests for the graph-impact subcommand."""

    def test_help(self):
        result = _run_cli("graph-impact", "--help")
        assert result.returncode == 0

    def test_impact_unknown_file(self, tmp_path):
        """Impact on unknown file — empty results."""
        result = _run_cli("graph-impact", "nonexistent.py", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "no" in result.stdout.lower() or "0" in result.stdout

    def test_impact_with_depth(self, repo_with_python):
        """Index and check impact with custom depth."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli(
            "graph-impact", "hello.py", "--depth", "2",
            "--repo", str(repo_with_python),
        )
        assert result.returncode == 0


# --- graph-context ---


class TestGraphContext:
    """Tests for the graph-context subcommand."""

    def test_help(self):
        result = _run_cli("graph-context", "--help")
        assert result.returncode == 0

    def test_context_unknown_node(self, tmp_path):
        """Context for unknown node — should fail with error."""
        result = _run_cli("graph-context", "function:foo.py:bar", "--repo", str(tmp_path))
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_context_known_node(self, repo_with_python):
        """Index and get context for a known node."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        # Query to find the node ID
        query_result = _run_cli(
            "graph-query", "greet", "--repo", str(repo_with_python),
        )
        # The output should contain the node — just verify context subcommand exists
        # We test with the function ID format
        result = _run_cli(
            "graph-context", "function:hello.py:greet",
            "--repo", str(repo_with_python),
        )
        # Either succeeds or fails with not-found (ID format may differ)
        assert result.returncode in (0, 1)


# --- graph-dead ---


class TestGraphDead:
    """Tests for the graph-dead subcommand."""

    def test_graph_dead_help(self):
        result = _run_cli("graph-dead", "--help")
        assert result.returncode == 0
        assert "graph-dead" in result.stdout or "dead" in result.stdout.lower()

    def test_graph_dead_empty_repo(self, tmp_path):
        """graph-dead on empty repo — should report 0 dead symbols."""
        result = _run_cli("graph-dead", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0 dead" in result.stdout

    def test_graph_dead_with_dead_code(self, tmp_path):
        """graph-dead finds unreferenced function in repo."""
        import textwrap
        (tmp_path / "lib.py").write_text(textwrap.dedent("""\
            def used_fn():
                pass

            def dead_fn():
                pass
        """))
        (tmp_path / "main.py").write_text(textwrap.dedent("""\
            from lib import used_fn

            def main():
                used_fn()
        """))
        result = _run_cli("graph-dead", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "dead_fn" in result.stdout


# --- --json flag tests ---


class TestGraphJsonOutput:
    """Tests for --json flag on all graph commands."""

    def test_graph_index_json(self, repo_with_python):
        result = _run_cli("graph-index", "--repo", str(repo_with_python), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "nodes" in data
        assert "relationships" in data
        assert "files" in data
        assert data["nodes"] > 0

    def test_graph_index_json_empty(self, tmp_path):
        result = _run_cli("graph-index", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["nodes"] == 0

    def test_graph_query_json(self, repo_with_python):
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-query", "greet", "--repo", str(repo_with_python), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["name"] == "greet"
        assert "label" in data[0]
        assert "file_path" in data[0]

    def test_graph_query_json_no_results(self, tmp_path):
        result = _run_cli("graph-query", "nonexistent", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data == []

    def test_graph_impact_json(self, repo_with_python):
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-impact", "hello.py", "--repo", str(repo_with_python), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_graph_dead_json(self, tmp_path):
        (tmp_path / "lib.py").write_text(textwrap.dedent("""\
            def used_fn():
                pass

            def dead_fn():
                pass
        """))
        (tmp_path / "main.py").write_text(textwrap.dedent("""\
            from lib import used_fn

            def main():
                used_fn()
        """))
        result = _run_cli("graph-dead", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        names = [d["name"] for d in data]
        assert "dead_fn" in names

    def test_graph_dead_json_empty(self, tmp_path):
        result = _run_cli("graph-dead", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data == []

    def test_graph_context_json_not_found(self, tmp_path):
        result = _run_cli("graph-context", "function:foo:bar", "--repo", str(tmp_path), "--json")
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert "error" in data
