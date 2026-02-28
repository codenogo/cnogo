"""Tests for graph impact integration in workflow_checks_core."""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def _make_python_repo(tmp_path):
    """Create a repo with cross-file dependencies."""
    (tmp_path / "lib.py").write_text(textwrap.dedent("""\
        def helper():
            pass
    """))
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from lib import helper

        def run():
            helper()
    """))


def test_graph_impact_section_returns_enabled(tmp_path):
    """_graph_impact_section should return enabled=True with valid graph."""
    _make_python_repo(tmp_path)
    result = checks._graph_impact_section(tmp_path, {"lib.py"})
    assert result["enabled"] is True
    assert "affected_files" in result
    assert "affected_symbols" in result
    assert "total_affected" in result
    assert "per_file" in result
    assert "graph_status" in result


def test_graph_impact_section_disabled_on_error(tmp_path):
    """_graph_impact_section should return enabled=False on error."""
    # Use a path where DB creation will fail (not a directory)
    bad_path = Path("/dev/null/impossible")
    result = checks._graph_impact_section(bad_path, {"foo.py"})
    assert result["enabled"] is False
    assert "error" in result


def test_graph_impact_section_empty_changed_files(tmp_path):
    """_graph_impact_section with no changed files should return enabled with empty data."""
    result = checks._graph_impact_section(tmp_path, set())
    assert result["enabled"] is True
    assert result["total_affected"] == 0
    assert result["affected_files"] == []


def test_graph_impact_section_resolves_import_without_repo_on_syspath(tmp_path):
    """_graph_impact_section must add root to sys.path so ContextGraph imports succeed.

    Reproduces the 'No module named scripts' error from REVIEW.json when the
    repo root is not already on sys.path (e.g. when called from a subprocess).
    """
    _make_python_repo(tmp_path)
    repo_root = str(Path(__file__).resolve().parent.parent)
    # Temporarily remove repo root from sys.path to simulate subprocess env
    original_path = sys.path[:]
    sys.path[:] = [p for p in sys.path if p != repo_root]
    try:
        # Must still succeed — the function should add root internally
        result = checks._graph_impact_section(Path(repo_root), {"tests/test_workflow_checks.py"})
        assert result["enabled"] is True, f"Expected enabled=True, got error: {result.get('error')}"
    finally:
        sys.path[:] = original_path
