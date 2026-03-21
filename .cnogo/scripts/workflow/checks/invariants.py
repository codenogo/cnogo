"""Invariant and file-scope helpers for workflow checks."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

_CODE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs", ".kt"}
_SCAN_IGNORE_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    "__pycache__",
}


@dataclass
class InvariantFinding:
    rule: str
    severity: str  # warn|fail
    file: str
    line: int
    message: str


def git_name_only(root: Path, cmd: str, *, run_shell: Callable[..., tuple[int, str]]) -> list[str]:
    rc, out = run_shell(cmd, cwd=root, timeout_sec=30)
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_relpaths(root: Path, *, fallback: str = "none", run_shell: Callable[..., tuple[int, str]]) -> set[str]:
    """Return changed/untracked relative file paths, with optional HEAD fallback."""
    names: set[str] = set()
    names.update(git_name_only(root, "git diff --name-only --diff-filter=ACMR", run_shell=run_shell))
    names.update(git_name_only(root, "git diff --cached --name-only --diff-filter=ACMR", run_shell=run_shell))
    names.update(git_name_only(root, "git ls-files --others --exclude-standard", run_shell=run_shell))
    if not names and fallback == "head":
        names.update(git_name_only(root, "git show --name-only --pretty='' HEAD", run_shell=run_shell))
    return names


def git_ref_exists(root: Path, ref: str, *, run_shell: Callable[..., tuple[int, str]]) -> bool:
    rc, _ = run_shell(f"git rev-parse --verify --quiet {ref}", cwd=root, timeout_sec=30)
    return rc == 0


def changed_relpaths_against_base(root: Path, *, run_shell: Callable[..., tuple[int, str]]) -> set[str]:
    """
    Return changed files in HEAD compared to a likely default branch.
    Used for feature-scoped CI runs where working tree is clean.
    """
    base_ref = ""
    for candidate in ("origin/main", "origin/master", "main", "master"):
        if git_ref_exists(root, candidate, run_shell=run_shell):
            base_ref = candidate
            break
    if not base_ref:
        return set()

    rc, out = run_shell(f"git merge-base HEAD {base_ref}", cwd=root, timeout_sec=30)
    if rc != 0:
        return set()
    merge_base = out.strip().splitlines()[-1] if out.strip() else ""
    if not merge_base:
        return set()

    return set(
        git_name_only(
            root,
            f"git diff --name-only --diff-filter=ACMR {merge_base}...HEAD",
            run_shell=run_shell,
        )
    )


def changed_files(root: Path, *, fallback: str = "none", run_shell: Callable[..., tuple[int, str]]) -> list[Path]:
    """Return changed/untracked files, with configurable fallback when tree is clean."""
    names = changed_relpaths(root, fallback=fallback, run_shell=run_shell)
    files: list[Path] = []
    for name in sorted(names):
        path = (root / name).resolve()
        if path.exists() and path.is_file():
            files.append(path)
    return files


def repo_files(root: Path) -> list[Path]:
    """Return all repo files while pruning ignored directories early."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [directory for directory in dirnames if directory not in _SCAN_IGNORE_PARTS]
        dir_path = Path(dirpath)
        for name in filenames:
            path = dir_path / name
            if path.is_file():
                files.append(path)
    return files


def target_files_for_invariants(
    root: Path,
    cfg: dict[str, Any],
    *,
    changed_files_fallback: str = "none",
    run_shell: Callable[..., tuple[int, str]],
) -> list[Path]:
    scope = cfg.get("scanScope", "changed")
    candidates = repo_files(root) if scope == "repo" else changed_files(root, fallback=changed_files_fallback, run_shell=run_shell)
    out: list[Path] = []
    for path in candidates:
        if path.suffix.lower() not in _CODE_EXTS:
            continue
        if any(part in _SCAN_IGNORE_PARTS for part in path.parts):
            continue
        out.append(path)
    return out


def command_prefers_repo_root(pkg_path: str, cmd: str) -> bool:
    """Heuristic: command references package path explicitly, so run from repo root."""
    normalized = pkg_path.strip().strip("./")
    if not normalized:
        return False
    return normalized + "/" in cmd


def is_spotless_not_configured(cmd: str, output: str) -> bool:
    lower_cmd = cmd.lower()
    if "spotless" not in lower_cmd:
        return False
    lower_out = output.lower()
    patterns = (
        "no plugin found for prefix 'spotless'",
        'task "spotlesscheck" not found',
        "task 'spotlesscheck' not found",
        'task "spotlessapply" not found',
        "task 'spotlessapply' not found",
        "could not find method spotless",
        "plugin with id 'com.diffplug.spotless' not found",
    )
    return any(pattern in lower_out for pattern in patterns)


def path_matches_patterns(relpath: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if not pattern:
            continue
        if relpath == pattern:
            return True
        if fnmatch.fnmatch(relpath, pattern):
            return True
    return False


def run_invariant_checks(
    root: Path,
    wf: dict[str, Any],
    *,
    changed_files_fallback: str = "none",
    invariants_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    run_shell: Callable[..., tuple[int, str]],
) -> list[InvariantFinding]:
    cfg = invariants_cfg(wf)
    if not cfg.get("enabled", True):
        return []

    findings: list[InvariantFinding] = []
    files = target_files_for_invariants(
        root,
        cfg,
        changed_files_fallback=changed_files_fallback,
        run_shell=run_shell,
    )
    ticket_re = re.compile(r"(?:[A-Z][A-Z0-9]+-\d+|#[0-9]+)")
    todo_re = re.compile(r"\b(?:TODO|FIXME|XXX)\b")
    bare_except_re = re.compile(r"^\s*except\s*:\s*(#.*)?$")
    forbidden = cfg.get("forbiddenImportPatterns", [])
    max_file_lines = int(cfg.get("maxFileLines", 800))
    max_file_lines_exceptions = cfg.get("maxFileLinesExceptions", [])
    if not isinstance(max_file_lines_exceptions, list):
        max_file_lines_exceptions = []
    max_line_len = int(cfg.get("maxLineLength", 140))
    python_bare_except = cfg.get("pythonBareExcept", "warn")
    todo_requires_ticket = bool(cfg.get("todoRequiresTicket", True))

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        lines = text.splitlines()
        rel = str(path.relative_to(root))

        exempt_from_file_size = path_matches_patterns(rel, max_file_lines_exceptions)
        if len(lines) > max_file_lines and not exempt_from_file_size:
            findings.append(
                InvariantFinding(
                    rule="max-file-lines",
                    severity="warn",
                    file=rel,
                    line=1,
                    message=f"File has {len(lines)} lines (max {max_file_lines}).",
                )
            )

        for idx, line in enumerate(lines, start=1):
            if len(line) > max_line_len and not line.strip().startswith("http"):
                findings.append(
                    InvariantFinding(
                        rule="max-line-length",
                        severity="warn",
                        file=rel,
                        line=idx,
                        message=f"Line length {len(line)} exceeds {max_line_len}.",
                    )
                )

            if todo_requires_ticket and todo_re.search(line):
                stripped = line.lstrip()
                is_comment = stripped.startswith(("#", "//", "/*", "*", "--"))
                if is_comment and not ticket_re.search(line):
                    findings.append(
                        InvariantFinding(
                            rule="todo-requires-ticket",
                            severity="warn",
                            file=rel,
                            line=idx,
                            message="TODO/FIXME/XXX without ticket reference (e.g., ABC-123 or #123).",
                        )
                    )

            if path.suffix.lower() == ".py" and python_bare_except != "off" and bare_except_re.match(line):
                findings.append(
                    InvariantFinding(
                        rule="python-bare-except",
                        severity="fail" if python_bare_except == "fail" else "warn",
                        file=rel,
                        line=idx,
                        message="Bare except detected; catch a specific exception type.",
                    )
                )

            if line.lstrip().startswith(("import ", "from ")):
                for pattern_cfg in forbidden:
                    if not isinstance(pattern_cfg, dict):
                        continue
                    pattern = pattern_cfg.get("pattern", "")
                    mode = pattern_cfg.get("mode", "substring")
                    if not isinstance(pattern, str) or not pattern:
                        continue
                    matched = False
                    if mode == "regex":
                        try:
                            matched = re.search(pattern, line) is not None
                        except re.error:
                            matched = False
                    else:
                        matched = pattern in line
                    if matched:
                        findings.append(
                            InvariantFinding(
                                rule="forbidden-import-pattern",
                                severity="fail" if pattern_cfg.get("severity") == "fail" else "warn",
                                file=rel,
                                line=idx,
                                message=str(pattern_cfg.get("message") or "Forbidden import pattern matched."),
                            )
                        )

        if len(findings) > 500:
            break

    return findings


def summarize_invariants(findings: list[InvariantFinding]) -> dict[str, int]:
    summary = {"total": len(findings), "warn": 0, "fail": 0}
    for finding in findings:
        if finding.severity == "fail":
            summary["fail"] += 1
        else:
            summary["warn"] += 1
    return summary
