"""Repo-shape and policy helpers for workflow validation."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import load_workflow_config, workflow_packages
from scripts.workflow.shared.packages import infer_task_package as _shared_infer_task_package


def detect_repo_shape(root: Path, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Heuristic repo-shape detection to support single-repo, monorepo, and polyglot repos.

    Optimization: if WORKFLOW.json has non-empty packages[], use that instead of a full
    manifest walk. Falls back to a single-pass walk only when repoShape is "auto" and
    packages are absent or empty.
    """
    resolved_cfg = cfg if isinstance(cfg, dict) else load_workflow_config(root)
    packages = resolved_cfg.get("packages")

    if isinstance(packages, list) and packages:
        kind_counts: dict[str, int] = {}
        for package in packages:
            if isinstance(package, dict):
                kind = str(package.get("kind", "other"))
                kind_counts[kind] = kind_counts.get(kind, 0) + 1
        manifest_total = sum(kind_counts.values())
        languages = len(kind_counts.keys() - {"other"})
        return {
            "package_json": kind_counts.get("node", 0),
            "pom_xml": kind_counts.get("java", 0),
            "pyproject_toml": kind_counts.get("python", 0),
            "go_mod": kind_counts.get("go", 0),
            "cargo_toml": kind_counts.get("rust", 0),
            "monorepo": manifest_total > 1,
            "polyglot": languages > 1,
        }

    counts = {
        "package_json": 0,
        "pom_xml": 0,
        "pyproject_toml": 0,
        "go_mod": 0,
        "cargo_toml": 0,
    }
    ignore_dirs = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        "target",
        "__pycache__",
    }
    for _dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [directory for directory in dirnames if directory not in ignore_dirs]
        name_set = set(filenames)
        if "package.json" in name_set:
            counts["package_json"] += 1
        if "pom.xml" in name_set:
            counts["pom_xml"] += 1
        if "pyproject.toml" in name_set:
            counts["pyproject_toml"] += 1
        if "go.mod" in name_set:
            counts["go_mod"] += 1
        if "Cargo.toml" in name_set:
            counts["cargo_toml"] += 1

    manifest_total = sum(counts.values())
    languages = sum(1 for value in counts.values() if value > 0)
    return {
        "package_json": counts["package_json"],
        "pom_xml": counts["pom_xml"],
        "pyproject_toml": counts["pyproject_toml"],
        "go_mod": counts["go_mod"],
        "cargo_toml": counts["cargo_toml"],
        "monorepo": manifest_total > 1,
        "polyglot": languages > 1,
    }


def packages_from_cfg(cfg: dict[str, Any]) -> list[dict[str, str]]:
    packages: list[dict[str, str]] = []
    for package in workflow_packages(cfg):
        path = package.get("path")
        if isinstance(path, str) and path.strip():
            packages.append({"path": path.strip(), "name": str(package.get("name") or "").strip()})
    return packages


def infer_task_package(files: list[str], packages: list[dict[str, str]]) -> str | None:
    return _shared_infer_task_package(files, packages)


def _get_policy_level(
    cfg: dict[str, Any],
    *,
    key: str,
    default: str,
    allowed: set[str],
) -> str:
    enforcement = cfg.get("enforcement") if isinstance(cfg.get("enforcement"), dict) else {}
    level = enforcement.get(key, default)
    if level not in allowed:
        return default
    return level


def get_monorepo_scope_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(cfg, key="monorepoVerifyScope", default="warn", allowed={"warn", "error"})


def get_operating_principles_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(cfg, key="operatingPrinciples", default="warn", allowed={"off", "warn", "error"})


def get_tdd_mode_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(cfg, key="tddMode", default="error", allowed={"off", "warn", "error"})


def get_verification_before_completion_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(
        cfg,
        key="verificationBeforeCompletion",
        default="error",
        allowed={"off", "warn", "error"},
    )


def get_two_stage_review_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(cfg, key="twoStageReview", default="error", allowed={"off", "warn", "error"})


def get_task_ownership_level(cfg: dict[str, Any]) -> str:
    return _get_policy_level(cfg, key="taskOwnership", default="error", allowed={"off", "warn", "error"})


def verify_cmd_scoped(cmd: str) -> bool:
    """
    Returns True if a verification command looks scoped to a package.
    Heuristic: uses `cd <dir> && ...` or common workspace flags.
    """
    stripped = cmd.strip()
    if not stripped:
        return True
    if re.search(r"(^|\s)cd\s+[^;&|]+\s*&&", stripped):
        return True
    if "pnpm -C " in stripped or "pnpm --dir " in stripped:
        return True
    if "npm --prefix " in stripped:
        return True
    if "yarn workspace " in stripped or "pnpm -F " in stripped or "pnpm --filter " in stripped:
        return True
    if "mvn -f " in stripped or "mvn --file " in stripped:
        return True
    if "gradle -p " in stripped or "./gradlew -p " in stripped:
        return True
    if "go test " in stripped or "cargo test" in stripped:
        return True
    if "pytest" in stripped or "ruff" in stripped:
        return True
    return False
