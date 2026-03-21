"""Shared package/path helpers for workflow orchestration."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import load_workflow_config, workflow_packages


def normalize_package_path(path: str) -> str:
    normalized = path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def configured_packages(root: Path) -> list[dict[str, Any]]:
    return workflow_packages(load_workflow_config(root))


def infer_task_package(
    files: list[str],
    packages: list[dict[str, Any]],
    *,
    cwd: str | None = None,
) -> str | None:
    if cwd and isinstance(cwd, str) and cwd.strip():
        normalized_cwd = normalize_package_path(cwd)
        for package in packages:
            package_path = package.get("path")
            if isinstance(package_path, str) and normalize_package_path(package_path) == normalized_cwd:
                return package_path

    if not files or not packages:
        return None

    matched: set[str] = set()
    for file_path in files:
        normalized_file = str(file_path).lstrip("./")
        for package in packages:
            package_path = package.get("path")
            if not isinstance(package_path, str):
                continue
            base = normalize_package_path(package_path)
            if not base:
                matched.add(package_path)
                break
            if normalized_file == base or normalized_file.startswith(base + "/"):
                matched.add(package_path)
                break
        else:
            matched.add("__outside__")

    if len(matched) == 1:
        only = next(iter(matched))
        if only != "__outside__":
            return only
    return None


def package_has_changes(pkg_path: str, changed_relpaths: set[str]) -> bool:
    normalized = normalize_package_path(pkg_path)
    if normalized in {"", "."}:
        return bool(changed_relpaths)
    prefix = normalized + "/"
    return any(path == normalized or path.startswith(prefix) for path in changed_relpaths)


def scope_package_command(package_path: str, command: str) -> str:
    normalized_path = normalize_package_path(package_path)
    if not normalized_path:
        return command
    return f"cd {shlex.quote(normalized_path)} && {command}"
