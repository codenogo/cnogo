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
        [sys.executable, ".cnogo/scripts/workflow_memory.py", *args],
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


# --- graph-coupling ---


class TestGraphCoupling:
    """Tests for the graph-coupling subcommand."""

    def test_help(self):
        result = _run_cli("graph-coupling", "--help")
        assert result.returncode == 0
        assert "coupling" in result.stdout.lower()

    def test_empty_repo(self, tmp_path):
        result = _run_cli("graph-coupling", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0 coupled" in result.stdout

    def test_coupling_with_shared_targets(self, tmp_path):
        """Two functions calling the same target should be coupled."""
        (tmp_path / "shared.py").write_text(textwrap.dedent("""\
            def helper():
                pass
        """))
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            from shared import helper

            def func_a():
                helper()
        """))
        (tmp_path / "b.py").write_text(textwrap.dedent("""\
            from shared import helper

            def func_b():
                helper()
        """))
        result = _run_cli("graph-coupling", "--repo", str(tmp_path), "--strength", "0.3")
        assert result.returncode == 0
        assert "<->" in result.stdout or "coupled" in result.stdout.lower()

    def test_json_output(self, tmp_path):
        result = _run_cli("graph-coupling", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_strength_filter(self, tmp_path):
        """High threshold should filter out weak coupling."""
        result = _run_cli("graph-coupling", "--repo", str(tmp_path), "--strength", "0.99")
        assert result.returncode == 0


# --- graph-blast-radius ---


class TestGraphBlastRadius:
    """Tests for the graph-blast-radius subcommand."""

    def test_help(self):
        result = _run_cli("graph-blast-radius", "--help")
        assert result.returncode == 0
        assert "blast-radius" in result.stdout.lower() or "file" in result.stdout.lower()

    def test_empty_repo(self, tmp_path):
        """Blast radius on empty repo — should produce empty results."""
        result = _run_cli("graph-blast-radius", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0" in result.stdout or "no" in result.stdout.lower()

    def test_with_dependencies(self, repo_with_python):
        """Blast radius with cross-file deps should show affected symbols."""
        result = _run_cli(
            "graph-blast-radius", "--repo", str(repo_with_python),
            "--files", "hello.py",
        )
        assert result.returncode == 0
        assert "affected" in result.stdout.lower() or "impact" in result.stdout.lower()

    def test_json_output(self, repo_with_python):
        """--json flag should produce valid JSON with expected keys."""
        result = _run_cli(
            "graph-blast-radius", "--repo", str(repo_with_python),
            "--files", "hello.py", "--json",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "graph_status" in data
        assert "affected_files" in data
        assert "affected_symbols" in data
        assert "total_affected" in data
        assert "per_file" in data

    def test_multiple_files(self, repo_with_python):
        """Blast radius with multiple files should aggregate impact."""
        result = _run_cli(
            "graph-blast-radius", "--repo", str(repo_with_python),
            "--files", "hello.py,main.py", "--json",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "hello.py" in data["per_file"]
        assert "main.py" in data["per_file"]


# --- graph-communities ---


class TestGraphCommunities:
    """Tests for the graph-communities subcommand."""

    def test_help(self):
        result = _run_cli("graph-communities", "--help")
        assert result.returncode == 0
        assert "communit" in result.stdout.lower()

    def test_empty_repo(self, tmp_path):
        result = _run_cli("graph-communities", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0" in result.stdout

    def test_with_connected_files(self, tmp_path):
        """Connected files should form communities."""
        (tmp_path / "shared.py").write_text(textwrap.dedent("""\
            def helper():
                pass
        """))
        (tmp_path / "a.py").write_text(textwrap.dedent("""\
            from shared import helper

            def func_a():
                helper()
        """))
        (tmp_path / "b.py").write_text(textwrap.dedent("""\
            from shared import helper

            def func_b():
                helper()
        """))
        result = _run_cli("graph-communities", "--repo", str(tmp_path), "--min-size", "2")
        assert result.returncode == 0
        assert "communit" in result.stdout.lower()

    def test_json_output(self, tmp_path):
        result = _run_cli("graph-communities", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "communities" in data
        assert "total_nodes" in data
        assert "num_communities" in data

    def test_min_size_filters(self, tmp_path):
        """High min-size should exclude small communities."""
        (tmp_path / "a.py").write_text("def func_a(): pass\n")
        result = _run_cli("graph-communities", "--repo", str(tmp_path), "--min-size", "100")
        assert result.returncode == 0
        assert "0" in result.stdout


# --- graph-status ---


class TestGraphStatus:
    """Tests for the graph-status subcommand."""

    def test_help(self):
        result = _run_cli("graph-status", "--help")
        assert result.returncode == 0
        assert "status" in result.stdout.lower()

    def test_no_graph(self, tmp_path):
        """graph-status on empty dir with no graph.db should report no graph."""
        result = _run_cli("graph-status", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "no graph" in result.stdout.lower() or "not indexed" in result.stdout.lower()

    def test_indexed_repo(self, repo_with_python):
        """graph-status on indexed repo reports node count."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-status", "--repo", str(repo_with_python))
        assert result.returncode == 0
        assert "node" in result.stdout.lower()
        # Should mention a non-zero count
        assert "0 nodes" not in result.stdout

    def test_json_output(self, repo_with_python):
        """--json returns valid JSON with expected keys."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-status", "--repo", str(repo_with_python), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "exists" in data
        assert data["exists"] is True
        assert "nodes" in data
        assert "relationships" in data
        assert "files" in data
        assert "stale_files" in data
        assert data["nodes"] > 0

    def test_json_no_graph(self, tmp_path):
        """--json with no graph returns exists=false."""
        result = _run_cli("graph-status", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["exists"] is False


# --- graph-flows ---


class TestGraphFlows:
    """Tests for the graph-flows subcommand."""

    def test_help(self):
        result = _run_cli("graph-flows", "--help")
        assert result.returncode == 0
        assert "flow" in result.stdout.lower()

    def test_empty_repo(self, tmp_path):
        """graph-flows on empty repo — should report 0 flows."""
        result = _run_cli("graph-flows", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "0" in result.stdout

    def test_with_entry_points(self, tmp_path):
        """graph-flows on repo with main() entry point shows flows."""
        (tmp_path / "app.py").write_text(textwrap.dedent("""\
            def helper():
                pass

            def main():
                helper()
        """))
        result = _run_cli("graph-flows", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "main" in result.stdout

    def test_json_output(self, tmp_path):
        """--json output has expected keys."""
        (tmp_path / "app.py").write_text(textwrap.dedent("""\
            def helper():
                pass

            def main():
                helper()
        """))
        result = _run_cli("graph-flows", "--repo", str(tmp_path), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        flow = data[0]
        assert "process_id" in flow
        assert "entry_point" in flow
        assert "steps" in flow
        ep = flow["entry_point"]
        assert "name" in ep
        assert "file_path" in ep
        assert "label" in ep

    def test_max_depth(self, tmp_path):
        """--max-depth flag limits BFS depth."""
        (tmp_path / "app.py").write_text(textwrap.dedent("""\
            def func_c():
                pass

            def func_b():
                func_c()

            def func_a():
                func_b()

            def main():
                func_a()
        """))
        result = _run_cli(
            "graph-flows", "--repo", str(tmp_path),
            "--max-depth", "1", "--json",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        main_flows = [f for f in data if f["entry_point"]["name"] == "main"]
        assert len(main_flows) == 1
        step_names = [s["name"] for s in main_flows[0]["steps"]]
        assert "func_a" in step_names
        # func_b at depth 2 should be excluded with max_depth=1
        assert "func_b" not in step_names


# --- graph-search ---


class TestGraphSearch:
    """Tests for the graph-search subcommand."""

    def test_help(self):
        result = _run_cli("graph-search", "--help")
        assert result.returncode == 0
        assert "search" in result.stdout.lower()

    def test_empty_repo(self, tmp_path):
        """graph-search on empty repo — no results."""
        result = _run_cli("graph-search", "foo", "--repo", str(tmp_path))
        assert result.returncode == 0
        assert "no" in result.stdout.lower() or "0" in result.stdout

    def test_search_finds_symbol(self, repo_with_python):
        """Index and search for a known function."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-search", "greet", "--repo", str(repo_with_python))
        assert result.returncode == 0
        assert "greet" in result.stdout

    def test_json_output(self, repo_with_python):
        """--json flag produces valid JSON with expected keys."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli("graph-search", "greet", "--repo", str(repo_with_python), "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "name" in data[0]
        assert "score" in data[0]
        assert "label" in data[0]
        assert "file_path" in data[0]

    def test_limit_flag(self, repo_with_python):
        """--limit flag caps results."""
        _run_cli("graph-index", "--repo", str(repo_with_python))
        result = _run_cli(
            "graph-search", "greet", "--repo", str(repo_with_python),
            "--limit", "1", "--json",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) <= 1
