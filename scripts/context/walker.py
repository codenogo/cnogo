"""File walker for context graph ingestion.

Walks a repository discovering Python files, reading content, and computing
SHA-256 hashes for incremental re-indexing support.

Supports .gitignore patterns via fnmatch and has built-in skip patterns
for common non-source directories.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath


# Directories always skipped regardless of .gitignore
_DEFAULT_SKIP = frozenset({
    "__pycache__",
    ".git",
    ".cnogo",
    "node_modules",
    ".venv",
    ".tox",
})


@dataclass
class FileEntry:
    """A discovered file with its content and metadata."""

    path: Path
    content: str
    language: str
    content_hash: str


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(content.encode()).hexdigest()


def _load_gitignore(repo_path: Path) -> list[str]:
    """Load .gitignore patterns from the repo root."""
    gitignore = repo_path / ".gitignore"
    if not gitignore.exists():
        return []
    patterns = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def _is_ignored(rel_path: PurePosixPath, gitignore_patterns: list[str]) -> bool:
    """Check if a relative path matches any gitignore pattern."""
    rel_str = str(rel_path)
    for pattern in gitignore_patterns:
        # Directory pattern (e.g. "build/")
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if any(part == dir_name for part in rel_path.parts):
                return True
        # File/glob pattern
        if fnmatch(rel_path.name, pattern):
            return True
        if fnmatch(rel_str, pattern):
            return True
    return False


def _in_skip_dir(rel_path: Path) -> bool:
    """Check if path is under a default-skip directory."""
    return any(part in _DEFAULT_SKIP for part in rel_path.parts)


def walk(repo_path: str | Path) -> list[FileEntry]:
    """Walk a repository and return FileEntry list for all Python files.

    Args:
        repo_path: Root directory to walk.

    Returns:
        List of FileEntry objects, sorted by path.
    """
    repo_path = Path(repo_path)
    gitignore_patterns = _load_gitignore(repo_path)
    entries: list[FileEntry] = []

    for abs_path in sorted(repo_path.rglob("*.py")):
        rel_path = abs_path.relative_to(repo_path)

        if _in_skip_dir(rel_path):
            continue

        if _is_ignored(PurePosixPath(rel_path), gitignore_patterns):
            continue

        content = abs_path.read_text()
        entries.append(FileEntry(
            path=rel_path,
            content=content,
            language="python",
            content_hash=_compute_hash(content),
        ))

    return entries
