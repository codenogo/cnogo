"""Tests for context graph file walker."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


@pytest.fixture
def repo(tmp_path):
    """Create a minimal repo structure for testing."""
    # Python files
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "utils.py").write_text("def helper(): pass\n")

    # Nested package
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "core.py").write_text("class Core: pass\n")

    return tmp_path


# --- Discovery ---


def test_walk_discovers_py_files(repo):
    from scripts.context.walker import walk
    entries = walk(repo)
    paths = {e.path for e in entries}
    assert Path("main.py") in paths
    assert Path("utils.py") in paths
    assert Path("pkg/__init__.py") in paths
    assert Path("pkg/core.py") in paths


def test_walk_returns_file_entries(repo):
    from scripts.context.walker import walk
    entries = walk(repo)
    assert len(entries) == 4
    for entry in entries:
        assert entry.language == "python"
        assert entry.content_hash != ""


def test_walk_reads_content(repo):
    from scripts.context.walker import walk
    entries = walk(repo)
    by_path = {str(e.path): e for e in entries}
    assert by_path["main.py"].content == "print('hello')\n"


# --- Content hashing ---


def test_content_hash_is_sha256(repo):
    from scripts.context.walker import walk
    entries = walk(repo)
    by_path = {str(e.path): e for e in entries}
    expected = hashlib.sha256(b"print('hello')\n").hexdigest()
    assert by_path["main.py"].content_hash == expected


def test_content_hash_changes_with_content(repo):
    from scripts.context.walker import walk
    entries1 = walk(repo)
    by_path1 = {str(e.path): e for e in entries1}
    hash1 = by_path1["main.py"].content_hash

    (repo / "main.py").write_text("print('changed')\n")
    entries2 = walk(repo)
    by_path2 = {str(e.path): e for e in entries2}
    hash2 = by_path2["main.py"].content_hash

    assert hash1 != hash2


# --- Default skip patterns ---


def test_skip_pycache(repo):
    from scripts.context.walker import walk
    cache = repo / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-39.pyc").write_text("")
    (cache / "cached.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any("__pycache__" in p for p in paths)


def test_skip_dot_git(repo):
    from scripts.context.walker import walk
    git = repo / ".git"
    git.mkdir()
    (git / "config.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any(".git" in p for p in paths)


def test_skip_cnogo(repo):
    from scripts.context.walker import walk
    cnogo = repo / ".cnogo"
    cnogo.mkdir()
    (cnogo / "memory.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any(".cnogo" in p for p in paths)


def test_skip_node_modules(repo):
    from scripts.context.walker import walk
    nm = repo / "node_modules"
    nm.mkdir()
    (nm / "script.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any("node_modules" in p for p in paths)


def test_skip_venv(repo):
    from scripts.context.walker import walk
    venv = repo / ".venv"
    venv.mkdir()
    (venv / "activate.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any(".venv" in p for p in paths)


def test_skip_tox(repo):
    from scripts.context.walker import walk
    tox = repo / ".tox"
    tox.mkdir()
    (tox / "test.py").write_text("x = 1\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any(".tox" in p for p in paths)


# --- Gitignore filtering ---


def test_gitignore_filtering(repo):
    from scripts.context.walker import walk
    (repo / "generated.py").write_text("# auto\n")
    (repo / ".gitignore").write_text("generated.py\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert "generated.py" not in paths


def test_gitignore_directory_pattern(repo):
    from scripts.context.walker import walk
    build = repo / "build"
    build.mkdir()
    (build / "output.py").write_text("x = 1\n")
    (repo / ".gitignore").write_text("build/\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert not any("build" in p for p in paths)


def test_gitignore_glob_pattern(repo):
    from scripts.context.walker import walk
    (repo / "test_tmp.py").write_text("x = 1\n")
    (repo / ".gitignore").write_text("test_tmp*.py\n")

    entries = walk(repo)
    paths = {str(e.path) for e in entries}
    assert "test_tmp.py" not in paths


def test_walk_empty_dir(tmp_path):
    from scripts.context.walker import walk
    entries = walk(tmp_path)
    assert entries == []


def test_walk_paths_are_relative(repo):
    from scripts.context.walker import walk
    entries = walk(repo)
    for entry in entries:
        assert not entry.path.is_absolute()


# --- Multi-language discovery ---


@pytest.fixture
def multilang_repo(tmp_path):
    """Create a repo with multiple language files."""
    (tmp_path / "main.py").write_text("print('hello')\n")
    (tmp_path / "app.ts").write_text("const x: number = 1;\n")
    (tmp_path / "component.tsx").write_text("export default function App() {}\n")
    (tmp_path / "index.js").write_text("module.exports = {};\n")
    (tmp_path / "utils.jsx").write_text("export const fn = () => {};\n")
    (tmp_path / "main.go").write_text("package main\n")
    (tmp_path / "Main.java").write_text("class Main {}\n")
    (tmp_path / "lib.rs").write_text("fn main() {}\n")
    (tmp_path / "script.rb").write_text("puts 'hello'\n")
    (tmp_path / "README.md").write_text("# Readme\n")  # should be skipped
    (tmp_path / "data.json").write_text("{}\n")  # should be skipped
    return tmp_path


def test_walk_discovers_ts_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "app.ts" in by_path
    assert by_path["app.ts"].language == "typescript"


def test_walk_discovers_tsx_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "component.tsx" in by_path
    assert by_path["component.tsx"].language == "typescript"


def test_walk_discovers_js_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "index.js" in by_path
    assert by_path["index.js"].language == "javascript"


def test_walk_discovers_jsx_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "utils.jsx" in by_path
    assert by_path["utils.jsx"].language == "javascript"


def test_walk_discovers_go_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "main.go" in by_path
    assert by_path["main.go"].language == "go"


def test_walk_discovers_java_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "Main.java" in by_path
    assert by_path["Main.java"].language == "java"


def test_walk_discovers_rust_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "lib.rs" in by_path
    assert by_path["lib.rs"].language == "rust"


def test_walk_discovers_ruby_files(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    by_path = {str(e.path): e for e in entries}
    assert "script.rb" in by_path
    assert by_path["script.rb"].language == "ruby"


def test_walk_skips_unsupported_extensions(multilang_repo):
    from scripts.context.walker import walk
    entries = walk(multilang_repo)
    paths = {str(e.path) for e in entries}
    assert "README.md" not in paths
    assert "data.json" not in paths


def test_supported_extensions_dict_exists():
    from scripts.context.walker import SUPPORTED_EXTENSIONS
    assert ".py" in SUPPORTED_EXTENSIONS
    assert ".ts" in SUPPORTED_EXTENSIONS
    assert ".tsx" in SUPPORTED_EXTENSIONS
    assert ".js" in SUPPORTED_EXTENSIONS
    assert ".jsx" in SUPPORTED_EXTENSIONS
    assert SUPPORTED_EXTENSIONS[".py"] == "python"
    assert SUPPORTED_EXTENSIONS[".ts"] == "typescript"
    assert SUPPORTED_EXTENSIONS[".js"] == "javascript"
