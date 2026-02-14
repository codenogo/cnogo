#!/usr/bin/env python3
"""
Workflow Validator for Universal Development Workflow Pack

Validates that planning artifacts follow the workflow rules and that
machine-checkable contracts exist for key markdown files.

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from workflow_utils import load_json as _load_json, repo_root as _utils_repo_root


FEATURE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
QUICK_DIR_RE = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
PLAN_MD_RE = re.compile(r"^(?P<num>[0-9]{2})-PLAN\.md$")


def _repo_root(start: Path) -> Path:
    return _utils_repo_root()


def _is_git_repo(root: Path) -> bool:
    try:
        subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _staged_files(root: Path) -> list[Path]:
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=root, stderr=subprocess.DEVNULL
    ).decode()
    files: list[Path] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        files.append(root / line)
    return files


@dataclass
class Finding:
    level: str  # "ERROR" | "WARN"
    message: str
    path: str | None = None

    def format(self) -> str:
        loc = f" ({self.path})" if self.path else ""
        return f"[{self.level}]{loc} {self.message}"


def _require(path: Path, findings: list[Finding], msg: str) -> None:
    if not path.exists():
        findings.append(Finding("ERROR", msg, str(path)))


def _validate_feature_slug(name: str, findings: list[Finding], path: Path) -> None:
    if not FEATURE_SLUG_RE.match(name):
        findings.append(
            Finding(
                "ERROR",
                "Feature directory must be kebab-case slug (lowercase letters/numbers/hyphens). Example: 'websocket-notifications'.",
                str(path),
            )
        )


MEMORY_ID_RE = re.compile(r"^cn-[a-z0-9]+(\.\d+)*$")


def _validate_memory_id(value: Any, field_name: str, findings: list[Finding], path: Path) -> None:
    """Validate optional memory ID fields (memoryEpicId, memoryId)."""
    if value is None:
        return  # Optional field, absence is fine
    if not isinstance(value, str) or not MEMORY_ID_RE.match(value):
        findings.append(Finding(
            "WARN",
            f"{field_name} has invalid format (expected cn-<base36>[.N]): {value!r}",
            str(path),
        ))


def _validate_plan_contract(contract: Any, findings: list[Finding], path: Path) -> None:
    if not isinstance(contract, dict):
        findings.append(Finding("ERROR", "Plan contract must be a JSON object.", str(path)))
        return

    if "schemaVersion" not in contract:
        findings.append(Finding("WARN", "Plan contract missing schemaVersion (recommended).", str(path)))

    # Validate optional memory fields
    _validate_memory_id(contract.get("memoryEpicId"), "memoryEpicId", findings, path)

    # Validate optional parallelizable hint
    parallelizable = contract.get("parallelizable")
    if parallelizable is not None and not isinstance(parallelizable, bool):
        findings.append(Finding("WARN", "Plan contract: 'parallelizable' should be a boolean if present.", str(path)))

    tasks = contract.get("tasks")
    if not isinstance(tasks, list):
        findings.append(Finding("ERROR", "Plan contract must include 'tasks' array.", str(path)))
        return

    if len(tasks) == 0:
        findings.append(Finding("ERROR", "Plan must include at least 1 task.", str(path)))
    if len(tasks) > 3:
        findings.append(Finding("ERROR", "Plan has >3 tasks. Split into multiple plans to keep context fresh.", str(path)))

    for i, t in enumerate(tasks, start=1):
        if not isinstance(t, dict):
            findings.append(Finding("ERROR", f"Task {i} must be an object.", str(path)))
            continue
        name = t.get("name")
        if not isinstance(name, str) or not name.strip():
            findings.append(Finding("ERROR", f"Task {i} missing non-empty 'name'.", str(path)))
        files = t.get("files")
        if not isinstance(files, list) or not files:
            findings.append(Finding("ERROR", f"Task {i} must include non-empty 'files' array.", str(path)))
        else:
            for fp in files:
                if not isinstance(fp, str) or not fp.strip():
                    findings.append(Finding("ERROR", f"Task {i} has empty file path.", str(path)))
                    continue
                if "*" in fp or "…" in fp or fp.endswith("/"):
                    findings.append(Finding("WARN", f"Task {i} file path looks ambiguous: {fp!r}", str(path)))
        verify = t.get("verify")
        if not isinstance(verify, list) or not verify or not all(isinstance(x, str) and x.strip() for x in verify):
            findings.append(Finding("ERROR", f"Task {i} must include non-empty 'verify' array of commands.", str(path)))
        # Validate optional memory ID per task
        _validate_memory_id(t.get("memoryId"), f"Task {i} memoryId", findings, path)


def _validate_quick_contract(contract: Any, findings: list[Finding], path: Path) -> None:
    if not isinstance(contract, dict):
        findings.append(Finding("ERROR", "Quick contract must be a JSON object.", str(path)))
        return
    if "schemaVersion" not in contract:
        findings.append(Finding("WARN", "Quick contract missing schemaVersion (recommended).", str(path)))
    goal = contract.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        findings.append(Finding("ERROR", "Quick contract missing non-empty 'goal'.", str(path)))
    files = contract.get("files")
    if not isinstance(files, list) or not files:
        findings.append(Finding("ERROR", "Quick contract missing non-empty 'files' array.", str(path)))
    verify = contract.get("verify")
    if not isinstance(verify, list) or not verify:
        findings.append(Finding("ERROR", "Quick contract missing non-empty 'verify' array of commands.", str(path)))


def _iter_feature_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "features"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def _iter_quick_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "quick"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def _iter_research_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "research"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def _iter_ideas_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "ideas"
    if not base.is_dir():
        return []
    return [p for p in base.iterdir() if p.is_dir()]


def _detect_repo_shape(root: Path) -> dict[str, Any]:
    """
    Heuristic repo-shape detection to support single-repo, monorepo, and polyglot repos.
    This is used only for validation warnings unless configured stricter via WORKFLOW.json.

    Optimization: if WORKFLOW.json has non-empty packages[], use that instead of rglob.
    Falls back to rglob only when repoShape is "auto" AND packages is empty.
    """
    cfg = _load_workflow_config(root)
    pkgs = cfg.get("packages")

    # Fast path: use configured packages[] if available
    if isinstance(pkgs, list) and pkgs:
        kind_counts: dict[str, int] = {}
        for p in pkgs:
            if isinstance(p, dict):
                kind = str(p.get("kind", "other"))
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

    # Slow path: rglob fallback when packages[] is empty or missing
    def count(glob: str, *, exclude_node_modules: bool = True) -> int:
        paths = list(root.rglob(glob))
        if exclude_node_modules:
            paths = [p for p in paths if "node_modules" not in p.parts and ".git" not in p.parts]
        return len(paths)

    pkg_json = count("package.json")
    pom = count("pom.xml")
    pyproject = count("pyproject.toml")
    go_mod = count("go.mod")
    cargo = count("Cargo.toml")

    manifest_total = pkg_json + pom + pyproject + go_mod + cargo
    languages = sum(1 for x in [pkg_json, pom, pyproject, go_mod, cargo] if x > 0)

    return {
        "package_json": pkg_json,
        "pom_xml": pom,
        "pyproject_toml": pyproject,
        "go_mod": go_mod,
        "cargo_toml": cargo,
        "monorepo": manifest_total > 1,
        "polyglot": languages > 1,
    }


def _load_workflow_config(root: Path) -> dict[str, Any]:
    cfg_path = root / "docs" / "planning" / "WORKFLOW.json"
    if not cfg_path.exists():
        return {}
    try:
        cfg = _load_json(cfg_path)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _validate_workflow_config(cfg: dict[str, Any], findings: list[Finding], root: Path) -> None:
    """
    Minimal validation of WORKFLOW.json without external dependencies.
    The JSON Schema is provided for editors; this is runtime sanity checking.
    """
    cfg_path = root / "docs" / "planning" / "WORKFLOW.json"

    version = cfg.get("version")
    if not isinstance(version, int) or version < 1:
        findings.append(Finding("WARN", "WORKFLOW.json: 'version' should be an integer >= 1.", str(cfg_path)))

    repo_shape = cfg.get("repoShape")
    if repo_shape not in {"auto", "single", "monorepo", "polyglot"}:
        findings.append(Finding("WARN", "WORKFLOW.json: 'repoShape' should be one of auto|single|monorepo|polyglot.", str(cfg_path)))

    perf = cfg.get("performance")
    if perf is not None and not isinstance(perf, dict):
        findings.append(Finding("WARN", "WORKFLOW.json: 'performance' should be an object.", str(cfg_path)))
    elif isinstance(perf, dict):
        pef = perf.get("postEditFormat", "auto")
        if pef not in {"auto", "off"}:
            findings.append(Finding("WARN", "WORKFLOW.json: performance.postEditFormat should be auto|off.", str(cfg_path)))
        scope = perf.get("postEditFormatScope", "changed")
        if scope not in {"changed", "repo"}:
            findings.append(Finding("WARN", "WORKFLOW.json: performance.postEditFormatScope should be changed|repo.", str(cfg_path)))

    enf = cfg.get("enforcement")
    if enf is not None and not isinstance(enf, dict):
        findings.append(Finding("WARN", "WORKFLOW.json: 'enforcement' should be an object.", str(cfg_path)))
    elif isinstance(enf, dict):
        mvs = enf.get("monorepoVerifyScope", "warn")
        if mvs not in {"warn", "error"}:
            findings.append(Finding("WARN", "WORKFLOW.json: enforcement.monorepoVerifyScope should be warn|error.", str(cfg_path)))
        kc = enf.get("karpathyChecklist", "warn")
        if kc not in {"off", "warn", "error"}:
            findings.append(Finding("WARN", "WORKFLOW.json: enforcement.karpathyChecklist should be off|warn|error.", str(cfg_path)))

    pkgs = cfg.get("packages")
    if pkgs is not None and not isinstance(pkgs, list):
        findings.append(Finding("WARN", "WORKFLOW.json: 'packages' should be an array.", str(cfg_path)))
    elif isinstance(pkgs, list):
        for i, p in enumerate(pkgs, start=1):
            if not isinstance(p, dict):
                findings.append(Finding("WARN", f"WORKFLOW.json: packages[{i}] should be an object.", str(cfg_path)))
                continue
            path = p.get("path")
            if not isinstance(path, str) or not path.strip():
                findings.append(Finding("WARN", f"WORKFLOW.json: packages[{i}].path is required.", str(cfg_path)))
                continue
            # Soft check: warn if the configured package path doesn't exist (helps catch typos).
            if not (root / path).exists():
                findings.append(Finding("WARN", f"WORKFLOW.json: packages[{i}].path does not exist: {path}", str(cfg_path)))
            cmds = p.get("commands")
            if cmds is not None and not isinstance(cmds, dict):
                findings.append(Finding("WARN", f"WORKFLOW.json: packages[{i}].commands should be an object.", str(cfg_path)))
            elif isinstance(cmds, dict):
                for k in ["build", "test", "lint", "format", "typecheck", "run"]:
                    v = cmds.get(k)
                    if v is not None and (not isinstance(v, str) or not v.strip()):
                        findings.append(Finding("WARN", f"WORKFLOW.json: packages[{i}].commands.{k} should be a non-empty string.", str(cfg_path)))

    research = cfg.get("research")
    if research is not None and not isinstance(research, dict):
        findings.append(Finding("WARN", "WORKFLOW.json: 'research' should be an object.", str(cfg_path)))
    elif isinstance(research, dict):
        mode = research.get("mode", "auto")
        if mode not in {"off", "local", "mcp", "web", "auto"}:
            findings.append(Finding("WARN", "WORKFLOW.json: research.mode should be off|local|mcp|web|auto.", str(cfg_path)))
        ms = research.get("minSources", 0)
        if not isinstance(ms, int) or ms < 0:
            findings.append(Finding("WARN", "WORKFLOW.json: research.minSources should be an integer >= 0.", str(cfg_path)))

    agent_teams = cfg.get("agentTeams")
    if agent_teams is not None and not isinstance(agent_teams, dict):
        findings.append(Finding("WARN", "WORKFLOW.json: 'agentTeams' should be an object.", str(cfg_path)))
    elif isinstance(agent_teams, dict):
        stale = agent_teams.get("staleIndicatorMinutes")
        if stale is not None:
            if isinstance(stale, bool) or not isinstance(stale, int) or stale <= 0:
                findings.append(Finding("WARN", "WORKFLOW.json: agentTeams.staleIndicatorMinutes should be an integer > 0.", str(cfg_path)))
        wt_mode = agent_teams.get("worktreeMode")
        if wt_mode is not None:
            if isinstance(wt_mode, bool) or not isinstance(wt_mode, str) or wt_mode not in ("always", "off"):
                findings.append(Finding("WARN", "WORKFLOW.json: agentTeams.worktreeMode should be 'always' or 'off'.", str(cfg_path)))


def _packages_from_cfg(cfg: dict[str, Any]) -> list[dict[str, str]]:
    pkgs = cfg.get("packages")
    if not isinstance(pkgs, list):
        return []
    out: list[dict[str, str]] = []
    for p in pkgs:
        if not isinstance(p, dict):
            continue
        path = p.get("path")
        if isinstance(path, str) and path.strip():
            out.append({"path": path.strip(), "name": str(p.get("name") or "").strip()})
    # Sort longer paths first to match most specific package
    out.sort(key=lambda x: len(x["path"]), reverse=True)
    return out


def _infer_task_package(files: list[str], packages: list[dict[str, str]]) -> str | None:
    """
    If all files fall under a single configured package path, return that path.
    """
    if not files or not packages:
        return None
    matched: set[str] = set()
    for f in files:
        fp = f.lstrip("./")
        for p in packages:
            base = p["path"].rstrip("/").lstrip("./")
            if fp == base or fp.startswith(base + "/"):
                matched.add(p["path"])
                break
        else:
            matched.add("__outside__")
    # If everything matches the same package path, return it.
    if len(matched) == 1:
        only = next(iter(matched))
        if only != "__outside__":
            return only
    return None


def _get_monorepo_scope_level(cfg: dict[str, Any]) -> str:
    # warn|error, default warn
    enforcement = cfg.get("enforcement") if isinstance(cfg.get("enforcement"), dict) else {}
    level = enforcement.get("monorepoVerifyScope", "warn")
    if level not in {"warn", "error"}:
        return "warn"
    return level


def _get_karpathy_checklist_level(cfg: dict[str, Any]) -> str:
    enforcement = cfg.get("enforcement") if isinstance(cfg.get("enforcement"), dict) else {}
    level = enforcement.get("karpathyChecklist", "warn")
    if level not in {"off", "warn", "error"}:
        return "warn"
    return level


def _verify_cmd_scoped(cmd: str) -> bool:
    """
    Returns True if a verification command looks scoped to a package.
    Heuristic: uses `cd <dir> && ...` or common workspace flags.
    """
    c = cmd.strip()
    if not c:
        return True
    if re.search(r"(^|\s)cd\s+[^;&|]+\s*&&", c):
        return True
    # common monorepo/workspace patterns
    if "pnpm -C " in c or "pnpm --dir " in c:
        return True
    if "npm --prefix " in c:
        return True
    if "yarn workspace " in c or "pnpm -F " in c or "pnpm --filter " in c:
        return True
    if "mvn -f " in c or "mvn --file " in c:
        return True
    if "gradle -p " in c or "./gradlew -p " in c:
        return True
    if "go test " in c or "cargo test" in c:
        # Usually repo-root is acceptable for Go/Rust; treat as scoped enough.
        return True
    if "pytest" in c or "ruff" in c:
        # Often repo-root is acceptable; treat as scoped enough.
        return True
    return False


def _validate_features(
    root: Path,
    findings: list[Finding],
    touched,
    shape: dict[str, Any],
    monorepo_scope_level: str,
    karpathy_level: str,
    packages_cfg: list[dict[str, str]],
) -> None:
    """Validate feature directories: context, plans, summaries, reviews."""
    for feature_dir in _iter_feature_dirs(root):
        if not touched(feature_dir):
            continue
        _validate_feature_slug(feature_dir.name, findings, feature_dir)

        context_md = feature_dir / "CONTEXT.md"
        context_json = feature_dir / "CONTEXT.json"
        if context_md.exists():
            _require(context_json, findings, "Missing CONTEXT.json contract for CONTEXT.md")
            if context_json.exists():
                try:
                    c = _load_json(context_json)
                    if not isinstance(c, dict):
                        findings.append(Finding("ERROR", "CONTEXT.json must be a JSON object.", str(context_json)))
                    elif "schemaVersion" not in c:
                        findings.append(Finding("WARN", "CONTEXT.json missing schemaVersion (recommended).", str(context_json)))
                except Exception as e:
                    findings.append(Finding("ERROR", f"Failed to parse CONTEXT.json: {e}", str(context_json)))

        for p in feature_dir.iterdir():
            if not p.is_file():
                continue
            m = PLAN_MD_RE.match(p.name)
            if not m:
                continue
            num = m.group("num")
            plan_json = feature_dir / f"{num}-PLAN.json"
            _require(plan_json, findings, f"Missing plan contract {num}-PLAN.json for {p.name}")
            if plan_json.exists():
                try:
                    contract = _load_json(plan_json)
                    _validate_plan_contract(contract, findings, plan_json)

                    # Monorepo/polyglot ergonomics: warn/error when verify commands are not scoped.
                    if shape.get("monorepo") and isinstance(contract, dict):
                        tasks = contract.get("tasks")
                        if isinstance(tasks, list):
                            for idx, task in enumerate(tasks, start=1):
                                if not isinstance(task, dict):
                                    continue
                                cwd = task.get("cwd")
                                verify = task.get("verify")
                                files = task.get("files")
                                if isinstance(cwd, str) and cwd.strip():
                                    continue  # explicit cwd is considered scoped
                                inferred = None
                                if isinstance(files, list) and all(isinstance(x, str) for x in files):
                                    inferred = _infer_task_package([str(x) for x in files], packages_cfg)
                                if isinstance(verify, list) and any(isinstance(v, str) and v.strip() for v in verify):
                                    unscoped = [v for v in verify if isinstance(v, str) and v.strip() and not _verify_cmd_scoped(v)]
                                    if unscoped:
                                        msg = (
                                            f"Plan task {idx} has verify commands that may be unscoped for a monorepo/polyglot repo. "
                                            f"Add task.cwd or scope verify with `cd <pkg> && ...` / workspace flags."
                                        )
                                        if inferred:
                                            msg += f" Inferred package cwd from files: {inferred!r}."
                                        lvl = "ERROR" if monorepo_scope_level == "error" else "WARN"
                                        findings.append(Finding(lvl, msg, str(plan_json)))
                except Exception as e:
                    findings.append(Finding("ERROR", f"Failed to parse plan contract: {e}", str(plan_json)))

            summary_md = feature_dir / f"{num}-SUMMARY.md"
            summary_json = feature_dir / f"{num}-SUMMARY.json"
            if summary_md.exists():
                _require(summary_json, findings, f"Missing summary contract {num}-SUMMARY.json for {summary_md.name}")
                if summary_json.exists():
                    try:
                        s = _load_json(summary_json)
                        if not isinstance(s, dict):
                            findings.append(Finding("ERROR", "Summary contract must be a JSON object.", str(summary_json)))
                        outcome = s.get("outcome")
                        if outcome not in {"complete", "partial", "failed"}:
                            findings.append(
                                Finding("ERROR", "Summary contract must include outcome: complete|partial|failed", str(summary_json))
                            )
                    except Exception as e:
                        findings.append(Finding("ERROR", f"Failed to parse summary contract: {e}", str(summary_json)))

        _validate_ci_verification(feature_dir, findings, karpathy_level)


def _validate_ci_verification(
    feature_dir: Path,
    findings: list[Finding],
    karpathy_level: str,
) -> None:
    """Validate review, CI verification, and human verification artifacts within a feature."""
    # Review artifacts
    review_md = feature_dir / "REVIEW.md"
    review_json = feature_dir / "REVIEW.json"
    if review_md.exists():
        _require(review_json, findings, "Missing REVIEW.json contract for REVIEW.md")
        if karpathy_level != "off":
            try:
                txt = review_md.read_text(encoding="utf-8", errors="replace")
                has = ("Karpathy" in txt) and ("Checklist" in txt or "Principles" in txt)
                if not has:
                    lvl = "ERROR" if karpathy_level == "error" else "WARN"
                    findings.append(Finding(lvl, "REVIEW.md missing Karpathy checklist section (enforced by WORKFLOW.json).", str(review_md)))
            except Exception:
                pass
        if review_json.exists():
            try:
                r = _load_json(review_json)
                if isinstance(r, dict) and "schemaVersion" not in r:
                    findings.append(Finding("WARN", "REVIEW.json missing schemaVersion (recommended).", str(review_json)))
            except Exception:
                pass

    # CI verification artifacts
    vci_md = feature_dir / "VERIFICATION-CI.md"
    vci_json = feature_dir / "VERIFICATION-CI.json"
    if vci_md.exists():
        _require(vci_json, findings, "Missing VERIFICATION-CI.json contract for VERIFICATION-CI.md")
        if vci_json.exists():
            try:
                vc = _load_json(vci_json)
                if isinstance(vc, dict) and "schemaVersion" not in vc:
                    findings.append(Finding("WARN", "VERIFICATION-CI.json missing schemaVersion (recommended).", str(vci_json)))
            except Exception:
                pass

    # Human verification artifacts
    v_md = feature_dir / "VERIFICATION.md"
    v_json = feature_dir / "VERIFICATION.json"
    if v_md.exists():
        _require(v_json, findings, "Missing VERIFICATION.json contract for VERIFICATION.md")
        if v_json.exists():
            try:
                vh = _load_json(v_json)
                if isinstance(vh, dict) and "schemaVersion" not in vh:
                    findings.append(Finding("WARN", "VERIFICATION.json missing schemaVersion (recommended).", str(v_json)))
            except Exception:
                pass


def _validate_quick_tasks(root: Path, findings: list[Finding], touched) -> None:
    """Validate quick task directories."""
    for quick_dir in _iter_quick_dirs(root):
        if not touched(quick_dir):
            continue
        if not QUICK_DIR_RE.match(quick_dir.name):
            findings.append(
                Finding(
                    "ERROR",
                    "Quick task directory must be NNN-slug (e.g. 001-fix-typo).",
                    str(quick_dir),
                )
            )
        plan_md = quick_dir / "PLAN.md"
        plan_json = quick_dir / "PLAN.json"
        if plan_md.exists():
            _require(plan_json, findings, "Missing PLAN.json contract for quick PLAN.md")
            if plan_json.exists():
                try:
                    qc = _load_json(plan_json)
                    _validate_quick_contract(qc, findings, plan_json)
                except Exception as e:
                    findings.append(Finding("ERROR", f"Failed to parse quick plan contract: {e}", str(plan_json)))
        summary_md = quick_dir / "SUMMARY.md"
        summary_json = quick_dir / "SUMMARY.json"
        if summary_md.exists():
            _require(summary_json, findings, "Missing SUMMARY.json contract for quick SUMMARY.md")


def _validate_research(root: Path, findings: list[Finding], touched) -> None:
    """Validate research artifact directories."""
    for rdir in _iter_research_dirs(root):
        if not touched(rdir):
            continue
        rmd = rdir / "RESEARCH.md"
        rjson = rdir / "RESEARCH.json"
        if rmd.exists():
            _require(rjson, findings, "Missing RESEARCH.json contract for RESEARCH.md")
            if rjson.exists():
                try:
                    r = _load_json(rjson)
                    if not isinstance(r, dict):
                        findings.append(Finding("ERROR", "RESEARCH.json must be a JSON object.", str(rjson)))
                    else:
                        if "schemaVersion" not in r:
                            findings.append(Finding("WARN", "RESEARCH.json missing schemaVersion (recommended).", str(rjson)))
                        sources = r.get("sources")
                        if sources is not None and not isinstance(sources, list):
                            findings.append(Finding("WARN", "RESEARCH.json: sources should be an array.", str(rjson)))
                except Exception as e:
                    findings.append(Finding("ERROR", f"Failed to parse RESEARCH.json: {e}", str(rjson)))


def _validate_brainstorm(root: Path, findings: list[Finding], touched) -> None:
    """Validate brainstorm/ideas artifact directories."""
    for idir in _iter_ideas_dirs(root):
        if not touched(idir):
            continue
        bmd = idir / "BRAINSTORM.md"
        bjson = idir / "BRAINSTORM.json"
        if bmd.exists():
            _require(bjson, findings, "Missing BRAINSTORM.json contract for BRAINSTORM.md")
            if bjson.exists():
                try:
                    b = _load_json(bjson)
                    if not isinstance(b, dict):
                        findings.append(Finding("ERROR", "BRAINSTORM.json must be a JSON object.", str(bjson)))
                    else:
                        if "schemaVersion" not in b:
                            findings.append(Finding("WARN", "BRAINSTORM.json missing schemaVersion (recommended).", str(bjson)))
                except Exception as e:
                    findings.append(Finding("ERROR", f"Failed to parse BRAINSTORM.json: {e}", str(bjson)))


def _validate_worktree_session(root: Path, findings: list[Finding]) -> None:
    """Validate .cnogo/worktree-session.json schema if it exists."""
    session_path = root / ".cnogo" / "worktree-session.json"
    if not session_path.exists():
        return
    try:
        data = _load_json(session_path)
    except Exception as e:
        findings.append(Finding("ERROR", f"Failed to parse worktree-session.json: {e}", str(session_path)))
        return
    if not isinstance(data, dict):
        findings.append(Finding("ERROR", "worktree-session.json must be a JSON object.", str(session_path)))
        return

    valid_phases = {"setup", "executing", "agents_complete", "merging", "merged", "verified", "committed", "cleaned"}

    sv = data.get("schemaVersion")
    if not isinstance(sv, int):
        findings.append(Finding("WARN", "worktree-session.json: schemaVersion should be an integer.", str(session_path)))
    for field in ("feature", "planNumber", "baseCommit", "baseBranch"):
        val = data.get(field)
        if not isinstance(val, str):
            findings.append(Finding("WARN", f"worktree-session.json: {field} should be a string.", str(session_path)))
    phase = data.get("phase")
    if not isinstance(phase, str) or phase not in valid_phases:
        findings.append(Finding("WARN", f"worktree-session.json: phase should be one of {sorted(valid_phases)}.", str(session_path)))
    for arr_field in ("worktrees", "mergeOrder", "mergedSoFar"):
        val = data.get(arr_field)
        if not isinstance(val, list):
            findings.append(Finding("WARN", f"worktree-session.json: {arr_field} should be an array.", str(session_path)))


def validate_repo(root: Path, *, staged_only: bool) -> list[Finding]:
    findings: list[Finding] = []

    cfg = _load_workflow_config(root)
    _validate_workflow_config(cfg, findings, root)
    shape = _detect_repo_shape(root)
    monorepo_scope_level = _get_monorepo_scope_level(cfg)
    karpathy_level = _get_karpathy_checklist_level(cfg)
    packages_cfg = _packages_from_cfg(cfg)

    # Core files
    _require(root / "docs" / "planning" / "PROJECT.md", findings, "Missing planning doc PROJECT.md")
    _require(root / ".cnogo" / "memory.db", findings, "Memory engine not initialized — run: python3 scripts/workflow_memory.py init")
    _require(root / "docs" / "planning" / "ROADMAP.md", findings, "Missing planning doc ROADMAP.md")

    if staged_only:
        if not _is_git_repo(root):
            findings.append(Finding("ERROR", "--staged requires a git repository.", str(root)))
            return findings
        staged = set(_staged_files(root))

        def touched(path: Path) -> bool:
            try:
                for f in staged:
                    if str(f).startswith(str(path)):
                        return True
                return False
            except Exception:
                return False
    else:
        def touched(_path: Path) -> bool:
            return True

    _validate_features(root, findings, touched, shape, monorepo_scope_level, karpathy_level, packages_cfg)
    _validate_quick_tasks(root, findings, touched)
    _validate_research(root, findings, touched)
    _validate_brainstorm(root, findings, touched)
    _validate_worktree_session(root, findings)

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow planning artifacts.")
    parser.add_argument("--root", default=".", help="Repo root (defaults to current directory).")
    parser.add_argument("--staged", action="store_true", help="Validate only areas touched by staged changes.")
    parser.add_argument("--json", action="store_true", help="Emit findings as JSON.")
    args = parser.parse_args()

    root = _repo_root(Path(args.root))
    findings = validate_repo(root, staged_only=args.staged)

    if args.json:
        print(
            json.dumps(
                [
                    {"level": f.level, "message": f.message, "path": f.path}
                    for f in findings
                ],
                indent=2,
            )
        )
    else:
        if not findings:
            print("✅ Workflow validation passed")
        else:
            for f in findings:
                print(f.format())

    errors = [f for f in findings if f.level == "ERROR"]
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

