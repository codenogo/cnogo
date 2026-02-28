"""Tests for PostCommit graph reindex hook in workflow_hooks.py."""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest

# Ensure repo root and .cnogo/scripts are on sys.path for imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".cnogo" / "scripts"))

import workflow_hooks as hooks


@pytest.fixture
def repo_with_python(tmp_path):
    """Create a temp dir with Python files for graph indexing."""
    (tmp_path / "hello.py").write_text(textwrap.dedent("""\
        def greet(name):
            return f"Hello, {name}"
    """))
    (tmp_path / "main.py").write_text(textwrap.dedent("""\
        from hello import greet

        def run():
            greet("world")
    """))
    return tmp_path


class TestPostCommitGraph:
    """Tests for the post_commit_graph() function."""

    def test_reindex_creates_graph_db(self, repo_with_python):
        """post_commit_graph should create graph.db when given a repo with Python files."""
        graph_db = repo_with_python / ".cnogo" / "graph.db"
        assert not graph_db.exists()

        result = hooks.post_commit_graph(repo_root_override=repo_with_python)
        assert result == 0
        assert graph_db.exists()

    def test_reindex_no_graph_db_creates_fresh(self, tmp_path):
        """post_commit_graph on empty dir should create empty graph without error."""
        result = hooks.post_commit_graph(repo_root_override=tmp_path)
        assert result == 0

    def test_reindex_idempotent(self, repo_with_python):
        """Calling post_commit_graph twice should produce the same result."""
        result1 = hooks.post_commit_graph(repo_root_override=repo_with_python)
        assert result1 == 0

        result2 = hooks.post_commit_graph(repo_root_override=repo_with_python)
        assert result2 == 0

    def test_skips_non_commit_commands(self):
        """post_commit_graph should skip (return 0) when CLAUDE_TOOL_INPUT is not a git commit."""
        with mock.patch.dict(os.environ, {"CLAUDE_TOOL_INPUT": '{"command": "ls -la"}'}):
            result = hooks.post_commit_graph()
            assert result == 0

    def test_detects_git_commit_command(self):
        """post_commit_graph should detect git commit in CLAUDE_TOOL_INPUT."""
        assert hooks._is_git_commit_command('git commit -m "test"')
        assert hooks._is_git_commit_command("git commit --amend")
        assert hooks._is_git_commit_command('  git   commit -m "msg"')
        assert not hooks._is_git_commit_command("git status")
        assert not hooks._is_git_commit_command("git push")
        assert not hooks._is_git_commit_command("echo git commit")
