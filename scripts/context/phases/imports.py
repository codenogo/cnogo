"""Import resolution phase.

Builds a file index mapping dotted module paths to FILE node IDs,
resolves imports to target files, and creates IMPORTS edges.

Zero external dependencies — stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import PurePosixPath

from scripts.context.model import (
    GraphRelationship,
    NodeLabel,
    RelType,
    generate_id,
)
from scripts.context.python_parser import ImportInfo, ParseResult
from scripts.context.storage import GraphStorage

# Standard library module names to skip (top-level only)
_STDLIB_MODULES = frozenset(sys.stdlib_module_names) if hasattr(sys, 'stdlib_module_names') else frozenset({
    "os", "sys", "re", "json", "math", "collections", "itertools", "functools",
    "pathlib", "typing", "dataclasses", "enum", "abc", "io", "copy", "hashlib",
    "sqlite3", "ast", "inspect", "textwrap", "argparse", "logging", "unittest",
    "tempfile", "shutil", "fnmatch", "glob", "contextlib", "importlib",
    "subprocess", "threading", "multiprocessing", "socket", "http", "urllib",
    "email", "html", "xml", "csv", "configparser", "struct", "codecs",
    "datetime", "time", "calendar", "random", "secrets", "string", "operator",
    "bisect", "heapq", "weakref", "types", "traceback", "warnings", "pdb",
    "profile", "pstats", "timeit", "dis", "pickle", "shelve", "marshal",
    "dbm", "gzip", "bz2", "lzma", "zipfile", "tarfile", "stat", "fileinput",
    "signal", "mmap", "ctypes", "platform", "sysconfig", "builtins",
    "__future__", "array", "queue", "select", "selectors", "asyncio",
    "concurrent", "venv", "ensurepip", "pip", "setuptools",
})


def build_file_index(storage: GraphStorage) -> dict[str, str]:
    """Build mapping from dotted module paths to FILE node IDs.

    For 'scripts/memory/__init__.py' → 'scripts.memory' maps to 'file:scripts/memory/__init__.py:'
    For 'scripts/memory/bridge.py' → 'scripts.memory.bridge' maps to 'file:scripts/memory/bridge.py:'
    """
    assert storage._conn is not None
    cur = storage._conn.execute(
        "SELECT id, file_path FROM nodes WHERE label = ?",
        (NodeLabel.FILE.value,),
    )

    index: dict[str, str] = {}
    for node_id, file_path in cur.fetchall():
        path = PurePosixPath(file_path)

        if path.name == "__init__.py":
            # Package: map parent directory as dotted path
            module_path = ".".join(path.parent.parts)
            if module_path:
                index[module_path] = node_id
        else:
            # Regular module: strip .py and convert to dotted path
            stem_parts = list(path.parent.parts) + [path.stem]
            module_path = ".".join(stem_parts)
            if module_path:
                index[module_path] = node_id

    return index


def _is_stdlib(module: str) -> bool:
    """Check if a module name is a stdlib module."""
    top_level = module.split(".")[0]
    return top_level in _STDLIB_MODULES


def resolve_import(
    imp: ImportInfo,
    source_file: str,
    file_index: dict[str, str],
) -> str | None:
    """Resolve an import to a FILE node ID.

    Returns the node ID of the target file, or None if unresolvable.
    """
    if imp.is_relative:
        return _resolve_relative(imp, source_file, file_index)
    else:
        return _resolve_absolute(imp, file_index)


def _resolve_absolute(imp: ImportInfo, file_index: dict[str, str]) -> str | None:
    """Resolve an absolute import."""
    module = imp.module
    if not module:
        return None

    if _is_stdlib(module):
        return None

    # Try exact module path
    if module in file_index:
        return file_index[module]

    # For 'from X import Y', X might be a package and Y a submodule
    # Try module.name for each imported name
    for name in imp.names:
        sub_module = f"{module}.{name}"
        if sub_module in file_index:
            return file_index[sub_module]

    return None


def _resolve_relative(
    imp: ImportInfo,
    source_file: str,
    file_index: dict[str, str],
) -> str | None:
    """Resolve a relative import via dot-counting from source directory."""
    source_path = PurePosixPath(source_file)
    # Go up `level` directories from the source file's directory
    base = source_path.parent
    for _ in range(imp.level - 1):
        base = base.parent

    # Build the target module path
    base_dotted = ".".join(base.parts) if base.parts else ""

    if imp.module:
        # from ..utils import helper → resolve 'utils' relative to base
        target = f"{base_dotted}.{imp.module}" if base_dotted else imp.module
    else:
        # from . import sibling → resolve each name relative to base
        for name in imp.names:
            target = f"{base_dotted}.{name}" if base_dotted else name
            if target in file_index:
                return file_index[target]
        return None

    if target in file_index:
        return file_index[target]

    return None


def process_imports(
    parse_results: dict[str, ParseResult],
    storage: GraphStorage,
) -> None:
    """Create IMPORTS edges from parse results.

    Args:
        parse_results: Mapping of file_path → ParseResult.
        storage: GraphStorage to write relationships to.
    """
    file_index = build_file_index(storage)
    relationships: list[GraphRelationship] = []

    for file_path, result in parse_results.items():
        source_id = generate_id(NodeLabel.FILE, file_path, "")

        for imp in result.imports:
            target_id = resolve_import(imp, file_path, file_index)
            if target_id is None:
                continue

            rel_id = f"imports:{source_id}->{target_id}"
            relationships.append(GraphRelationship(
                id=rel_id,
                type=RelType.IMPORTS,
                source=source_id,
                target=target_id,
                properties={"symbols": imp.names} if imp.names else {},
            ))

    if relationships:
        storage.add_relationships(relationships)
