#!/usr/bin/env python3
"""
Package-aware check runner for this workflow pack.

Reads docs/planning/WORKFLOW.json packages[].commands and runs checks per package:
- verify-ci: writes VERIFICATION-CI.md/json under a feature folder
- review: writes REVIEW.md/json under feature folder if inferable from memory, else under work/review/
- entropy: scans for invariant drift and can write background cleanup tasks

No external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_utils import load_json, load_workflow as _load_workflow_util, repo_root, write_json


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_shell(cmd: str, cwd: Path) -> tuple[int, str]:
    # WORKFLOW.json is a trusted file (equivalent to Makefile) — shell=True is intentional.
    try:
        out = subprocess.check_output(cmd, cwd=cwd, shell=True, stderr=subprocess.STDOUT).decode(errors="replace")
        return 0, out
    except subprocess.CalledProcessError as e:
        out = (e.output or b"").decode(errors="replace")
        return int(e.returncode or 1), out
    except FileNotFoundError as e:
        return 127, str(e)
    except Exception as e:
        return 1, str(e)


def git_branch(root: Path) -> str:
    rc, out = run_shell("git branch --show-current", cwd=root)
    return out.strip() if rc == 0 else ""


def infer_feature_from_state(root: Path) -> str | None:
    """Infer the active feature slug from memory engine, with branch fallback."""
    # Try memory engine first
    try:
        import sys
        sys.path.insert(0, str(root))
        from scripts.memory import is_initialized, list_issues
        if is_initialized(root):
            # Look for in-progress epics first, then open epics
            for status in ("in_progress", "open"):
                epics = list_issues(
                    issue_type="epic", status=status, root=root
                )
                for epic in epics:
                    if epic.feature_slug:
                        return epic.feature_slug
    except Exception:
        pass
    # Fallback: parse branch name (e.g. feature/foo-bar -> foo-bar)
    branch = git_branch(root)
    if branch and "/" in branch:
        slug = branch.split("/", 1)[1]
        if slug and slug not in {"main", "master", "develop"}:
            return slug
    return None


@dataclass
class CheckResult:
    name: str
    result: str  # pass|fail|skipped|warn
    details: str = ""
    cmd: str | None = None


@dataclass
class InvariantFinding:
    rule: str
    severity: str  # warn|fail
    file: str
    line: int
    message: str


DEFAULT_REVIEW_PRINCIPLES = [
    "Think Before Coding",
    "Simplicity First",
    "Surgical Changes",
    "Goal-Driven Execution",
    "Prefer shared utility packages over hand-rolled helpers",
    "Don't probe data YOLO-style",
    "Validate boundaries",
    "Typed SDKs",
]
REVIEW_SCHEMA_VERSION = 2


def load_workflow(root: Path | None = None) -> dict[str, Any]:
    return _load_workflow_util()


def packages_from_workflow(wf: dict[str, Any]) -> list[dict[str, Any]]:
    pkgs = wf.get("packages")
    if not isinstance(pkgs, list):
        return []
    out: list[dict[str, Any]] = []
    for p in pkgs:
        if isinstance(p, dict) and isinstance(p.get("path"), str):
            out.append(p)
    return out


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


def _invariants_cfg(wf: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": True,
        "scanScope": "changed",
        "maxFileLines": 800,
        "maxLineLength": 140,
        "todoRequiresTicket": True,
        "pythonBareExcept": "warn",
        "forbiddenImportPatterns": [
            {
                "pattern": r"^\s*from\s+\S+\s+import\s+\*",
                "mode": "regex",
                "severity": "warn",
                "message": "Avoid wildcard imports.",
            }
        ],
    }
    raw = wf.get("invariants")
    if not isinstance(raw, dict):
        return defaults
    cfg = dict(defaults)
    if isinstance(raw.get("enabled"), bool):
        cfg["enabled"] = raw["enabled"]
    if raw.get("scanScope") in {"changed", "repo"}:
        cfg["scanScope"] = raw["scanScope"]
    for key in ("maxFileLines", "maxLineLength"):
        v = raw.get(key)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            cfg[key] = v
    if isinstance(raw.get("todoRequiresTicket"), bool):
        cfg["todoRequiresTicket"] = raw["todoRequiresTicket"]
    if raw.get("pythonBareExcept") in {"off", "warn", "fail"}:
        cfg["pythonBareExcept"] = raw["pythonBareExcept"]
    fip = raw.get("forbiddenImportPatterns")
    if isinstance(fip, list):
        normalized: list[dict[str, str]] = []
        for it in fip:
            if not isinstance(it, dict):
                continue
            pattern = it.get("pattern")
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            mode = it.get("mode", "substring")
            if mode not in {"substring", "regex"}:
                mode = "substring"
            sev = it.get("severity", "warn")
            if sev not in {"warn", "fail"}:
                sev = "warn"
            msg = it.get("message")
            normalized.append(
                {
                    "pattern": pattern,
                    "mode": mode,
                    "severity": sev,
                    "message": msg if isinstance(msg, str) and msg.strip() else "Forbidden import pattern matched.",
                }
            )
        cfg["forbiddenImportPatterns"] = normalized
    return cfg


def _entropy_cfg(wf: dict[str, Any]) -> dict[str, Any]:
    defaults = {"enabled": True, "mode": "background", "maxFilesPerTask": 3, "maxTasksPerRun": 3}
    raw = wf.get("entropy")
    if not isinstance(raw, dict):
        return defaults
    cfg = dict(defaults)
    if isinstance(raw.get("enabled"), bool):
        cfg["enabled"] = raw["enabled"]
    if raw.get("mode") in {"background", "manual"}:
        cfg["mode"] = raw["mode"]
    for key in ("maxFilesPerTask", "maxTasksPerRun"):
        val = raw.get(key)
        if isinstance(val, int) and not isinstance(val, bool) and val > 0:
            cfg[key] = val
    return cfg


def _review_principles(wf: dict[str, Any]) -> list[str]:
    """Load enforced review principles from WORKFLOW.json enforcement.reviewPrinciples."""
    enforcement = wf.get("enforcement") if isinstance(wf.get("enforcement"), dict) else {}
    raw = enforcement.get("reviewPrinciples")
    if not isinstance(raw, list):
        return list(DEFAULT_REVIEW_PRINCIPLES)

    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out if out else list(DEFAULT_REVIEW_PRINCIPLES)


def _git_name_only(root: Path, cmd: str) -> list[str]:
    rc, out = run_shell(cmd, cwd=root)
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _changed_files(root: Path) -> list[Path]:
    """Return changed/untracked files, with HEAD fallback when tree is clean."""
    names: set[str] = set()
    names.update(_git_name_only(root, "git diff --name-only --diff-filter=ACMR"))
    names.update(_git_name_only(root, "git diff --cached --name-only --diff-filter=ACMR"))
    names.update(_git_name_only(root, "git ls-files --others --exclude-standard"))
    if not names:
        names.update(_git_name_only(root, "git show --name-only --pretty='' HEAD"))
    files: list[Path] = []
    for name in sorted(names):
        p = (root / name).resolve()
        if p.exists() and p.is_file():
            files.append(p)
    return files


def _repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _SCAN_IGNORE_PARTS for part in p.parts):
            continue
        files.append(p)
    return files


def _target_files_for_invariants(root: Path, cfg: dict[str, Any]) -> list[Path]:
    scope = cfg.get("scanScope", "changed")
    candidates = _repo_files(root) if scope == "repo" else _changed_files(root)
    out: list[Path] = []
    for p in candidates:
        if p.suffix.lower() not in _CODE_EXTS:
            continue
        if any(part in _SCAN_IGNORE_PARTS for part in p.parts):
            continue
        out.append(p)
    return out


def _command_prefers_repo_root(pkg_path: str, cmd: str) -> bool:
    """Heuristic: command references package path explicitly, so run from repo root."""
    normalized = pkg_path.strip().strip("./")
    if not normalized:
        return False
    marker = normalized + "/"
    return marker in cmd


def run_invariant_checks(root: Path, wf: dict[str, Any]) -> list[InvariantFinding]:
    cfg = _invariants_cfg(wf)
    if not cfg.get("enabled", True):
        return []

    findings: list[InvariantFinding] = []
    files = _target_files_for_invariants(root, cfg)
    ticket_re = re.compile(r"(?:[A-Z][A-Z0-9]+-\d+|#[0-9]+)")
    todo_re = re.compile(r"\b(?:TODO|FIXME|XXX)\b")
    bare_except_re = re.compile(r"^\s*except\s*:\s*(#.*)?$")
    forbidden = cfg.get("forbiddenImportPatterns", [])
    max_file_lines = int(cfg.get("maxFileLines", 800))
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

        if len(lines) > max_file_lines:
            findings.append(
                InvariantFinding(
                    rule="max-file-lines",
                    severity="warn",
                    file=rel,
                    line=1,
                    message=f"File has {len(lines)} lines (max {max_file_lines}).",
                )
            )

        for i, line in enumerate(lines, start=1):
            if len(line) > max_line_len and not line.strip().startswith("http"):
                findings.append(
                    InvariantFinding(
                        rule="max-line-length",
                        severity="warn",
                        file=rel,
                        line=i,
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
                            line=i,
                            message="TODO/FIXME/XXX without ticket reference (e.g., ABC-123 or #123).",
                        )
                    )

            if path.suffix.lower() == ".py" and python_bare_except != "off" and bare_except_re.match(line):
                findings.append(
                    InvariantFinding(
                        rule="python-bare-except",
                        severity="fail" if python_bare_except == "fail" else "warn",
                        file=rel,
                        line=i,
                        message="Bare except detected; catch a specific exception type.",
                    )
                )

            if line.lstrip().startswith(("import ", "from ")):
                for pat in forbidden:
                    if not isinstance(pat, dict):
                        continue
                    pattern = pat.get("pattern", "")
                    mode = pat.get("mode", "substring")
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
                                severity="fail" if pat.get("severity") == "fail" else "warn",
                                file=rel,
                                line=i,
                                message=str(pat.get("message") or "Forbidden import pattern matched."),
                            )
                        )

        if len(findings) > 500:
            break

    return findings


def summarize_invariants(findings: list[InvariantFinding]) -> dict[str, int]:
    summary = {"total": len(findings), "warn": 0, "fail": 0}
    for f in findings:
        if f.severity == "fail":
            summary["fail"] += 1
        else:
            summary["warn"] += 1
    return summary


def run_package_checks(root: Path, pkgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for p in pkgs:
        path = str(p.get("path") or ".")
        kind = str(p.get("kind") or "other")
        name = str(p.get("name") or Path(path).name or path)
        cmds = p.get("commands") if isinstance(p.get("commands"), dict) else {}

        pkg_dir = (root / path).resolve()
        pkg_res: dict[str, Any] = {"name": name, "path": path, "kind": kind, "checks": []}

        for check_name in ["lint", "typecheck", "test"]:
            cmd = cmds.get(check_name)
            if not isinstance(cmd, str) or not cmd.strip():
                pkg_res["checks"].append({"name": check_name, "result": "skipped", "cmd": None})
                continue
            check_cwd = root if _command_prefers_repo_root(path, cmd) else pkg_dir
            rc, out = run_shell(cmd, cwd=check_cwd)
            pkg_res["checks"].append(
                {
                    "name": check_name,
                    "result": "pass" if rc == 0 else "fail",
                    "cmd": cmd,
                    "cwd": str(check_cwd.relative_to(root)) if check_cwd != root else ".",
                    "exitCode": rc,
                    "output": out[-2000:],  # keep tail for readability
                }
            )

        results.append(pkg_res)
    return results


def summarize_checksets(per_pkg: list[dict[str, Any]]) -> dict[str, str]:
    """
    Aggregate overall lint/tests/types results.
    """
    summary = {"lint": "skipped", "typecheck": "skipped", "tests": "skipped"}
    mapping = {"lint": "lint", "typecheck": "typecheck", "test": "tests"}

    for pkg in per_pkg:
        for c in pkg.get("checks", []):
            nm = c.get("name")
            res = c.get("result")
            if nm not in mapping:
                continue
            key = mapping[nm]
            if res == "fail":
                summary[key] = "fail"
            elif res == "pass" and summary[key] != "fail":
                summary[key] = "pass"
            elif summary[key] == "skipped" and res == "skipped":
                summary[key] = "skipped"
    return summary


def write_verify_ci(
    root: Path,
    feature: str,
    per_pkg: list[dict[str, Any]],
    invariant_findings: list[InvariantFinding],
) -> int:
    base = root / "docs" / "planning" / "work" / "features" / feature
    ts = now_iso()
    agg = summarize_checksets(per_pkg)
    inv = summarize_invariants(invariant_findings)

    contract = {
        "schemaVersion": 1,
        "feature": feature,
        "timestamp": ts,
        "checks": [
            {"name": "lint", "result": agg["lint"]},
            {"name": "types", "result": agg["typecheck"]},
            {"name": "tests", "result": agg["tests"]},
        ],
        "packages": per_pkg,
        "invariants": {
            "summary": inv,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                }
                for f in invariant_findings[:200]
            ],
        },
        "notes": [],
    }
    write_json(base / "VERIFICATION-CI.json", contract)

    md_lines = [
        f"# Verification (CI): {feature}",
        "",
        f"**Timestamp:** {ts}",
        "",
        "## Summary",
        "",
        f"- Lint: **{agg['lint']}**",
        f"- Types: **{agg['typecheck']}**",
        f"- Tests: **{agg['tests']}**",
        f"- Invariants: **{inv['fail']} fail / {inv['warn']} warn**",
        "",
        "## Per-Package Results",
        "",
    ]
    for pkg in per_pkg:
        md_lines.append(f"### {pkg['name']} (`{pkg['path']}`)")
        for c in pkg.get("checks", []):
            suffix = ""
            if c.get("cmd"):
                cwd = c.get("cwd")
                cwd_part = f", cwd `{cwd}`" if isinstance(cwd, str) and cwd else ""
                suffix = f" (`{c.get('cmd')}`{cwd_part})"
            md_lines.append(f"- {c.get('name')}: **{c.get('result')}**{suffix}")
        md_lines.append("")

    if invariant_findings:
        md_lines.append("## Invariant Findings")
        md_lines.append("")
        for f in invariant_findings[:50]:
            md_lines.append(f"- [{f.severity}] `{f.file}:{f.line}` {f.message} ({f.rule})")
        if len(invariant_findings) > 50:
            md_lines.append(f"- ... {len(invariant_findings) - 50} more")
        md_lines.append("")
    write_text(base / "VERIFICATION-CI.md", "\n".join(md_lines).strip() + "\n")

    # exit code: fail if any fail
    has_pkg_fail = any(c["result"] == "fail" for pkg in per_pkg for c in pkg.get("checks", []))
    return 1 if has_pkg_fail or inv["fail"] > 0 else 0


def write_review(
    root: Path,
    feature: str | None,
    per_pkg: list[dict[str, Any]],
    invariant_findings: list[InvariantFinding],
    principles: list[str],
) -> int:
    ts = now_iso()
    branch = git_branch(root)
    agg = summarize_checksets(per_pkg)
    inv = summarize_invariants(invariant_findings)

    verdict = "pass"
    if "fail" in agg.values() or inv["fail"] > 0:
        verdict = "fail"
    elif any(v == "skipped" for v in agg.values()) or inv["warn"] > 0:
        verdict = "warn"

    blockers = [
        {
            "file": f.file,
            "line": f.line,
            "issue": f.message,
            "severity": "high",
            "rule": f.rule,
        }
        for f in invariant_findings
        if f.severity == "fail"
    ]
    warnings = [
        {
            "file": f.file,
            "line": f.line,
            "issue": f.message,
            "severity": "medium",
            "rule": f.rule,
        }
        for f in invariant_findings
        if f.severity != "fail"
    ]

    contract = {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "timestamp": ts,
        "feature": feature,
        "branch": branch,
        "automated": [
            {"name": "lint", "result": agg["lint"]},
            {"name": "types", "result": agg["typecheck"]},
            {"name": "tests", "result": agg["tests"]},
        ],
        "packages": per_pkg,
        "invariants": {
            "summary": inv,
            "findings": [
                {
                    "rule": f.rule,
                    "severity": f.severity,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                }
                for f in invariant_findings[:200]
            ],
        },
        "principles": [
            {"name": p, "status": "todo", "notes": ""}
            for p in principles
        ],
        "verdict": verdict,
        "blockers": blockers[:100],
        "warnings": warnings[:200],
    }

    if feature:
        out_base = root / "docs" / "planning" / "work" / "features" / feature
        write_json(out_base / "REVIEW.json", contract)
        md_path = out_base / "REVIEW.md"
    else:
        out_base = root / "docs" / "planning" / "work" / "review"
        write_json(out_base / f"{ts}-REVIEW.json", contract)
        md_path = out_base / f"{ts}-REVIEW.md"

    md_lines = [
        "# Review Report",
        "",
        f"**Timestamp:** {ts}",
        f"**Branch:** {branch or '[unknown]'}",
        f"**Feature:** {feature or '[none]'}",
        "",
        "## Automated Checks (Package-Aware)",
        "",
        f"- Lint: **{agg['lint']}**",
        f"- Types: **{agg['typecheck']}**",
        f"- Tests: **{agg['tests']}**",
        f"- Invariants: **{inv['fail']} fail / {inv['warn']} warn**",
        "",
        "## Per-Package Results",
        "",
    ]
    for pkg in per_pkg:
        md_lines.append(f"### {pkg['name']} (`{pkg['path']}`)")
        for c in pkg.get("checks", []):
            suffix = ""
            if c.get("cmd"):
                cwd = c.get("cwd")
                cwd_part = f", cwd `{cwd}`" if isinstance(cwd, str) and cwd else ""
                suffix = f" (`{c.get('cmd')}`{cwd_part})"
            md_lines.append(f"- {c.get('name')}: **{c.get('result')}**{suffix}")
        md_lines.append("")

    if invariant_findings:
        md_lines.append("## Invariant Findings")
        md_lines.append("")
        for f in invariant_findings[:100]:
            md_lines.append(f"- [{f.severity}] `{f.file}:{f.line}` {f.message} ({f.rule})")
        if len(invariant_findings) > 100:
            md_lines.append(f"- ... {len(invariant_findings) - 100} more")
        md_lines.append("")
    md_lines.append(f"## Verdict\n\n**{verdict.upper()}**\n")

    # Enforced section (validator checks for presence)
    md_lines.append("## Karpathy Checklist")
    md_lines.append("")
    md_lines.append("| Principle | Status | Notes |")
    md_lines.append("|----------|--------|------|")
    for principle in principles:
        md_lines.append(f"| {principle} | ⬜ | |")
    md_lines.append("")

    write_text(md_path, "\n".join(md_lines).strip() + "\n")

    return 1 if verdict == "fail" else 0


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "cleanup"


def _entropy_candidates(
    findings: list[InvariantFinding],
    *,
    max_files_per_task: int,
    max_tasks: int,
) -> list[dict[str, Any]]:
    by_file: dict[str, list[InvariantFinding]] = {}
    for f in findings:
        by_file.setdefault(f.file, []).append(f)

    def score(item: tuple[str, list[InvariantFinding]]) -> tuple[int, int, str]:
        file, fs = item
        fail_count = sum(1 for f in fs if f.severity == "fail")
        return (-fail_count, -len(fs), file)

    ordered_files = [f for f, _ in sorted(by_file.items(), key=score)]
    chunks: list[list[str]] = []
    current: list[str] = []
    for fp in ordered_files:
        current.append(fp)
        if len(current) >= max_files_per_task:
            chunks.append(current)
            current = []
        if len(chunks) >= max_tasks:
            break
    if current and len(chunks) < max_tasks:
        chunks.append(current)

    tasks: list[dict[str, Any]] = []
    for idx, files in enumerate(chunks, start=1):
        task_findings = [f for f in findings if f.file in files]
        rules = sorted({f.rule for f in task_findings})
        tasks.append(
            {
                "name": f"Entropy cleanup #{idx}",
                "files": files,
                "rules": rules,
                "findingCount": len(task_findings),
                "action": (
                    "Apply tiny non-behavioral refactors for listed files only. "
                    "Keep each PR scoped and verify checks pass."
                ),
            }
        )
    return tasks


def write_entropy_task(
    root: Path,
    findings: list[InvariantFinding],
    *,
    max_files_per_task: int,
    max_tasks: int,
) -> Path:
    task_dir = root / "docs" / "planning" / "work" / "background"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    task_path = task_dir / f"{task_id}-entropy-cleanup-TASK.md"
    candidates = _entropy_candidates(
        findings,
        max_files_per_task=max_files_per_task,
        max_tasks=max_tasks,
    )

    lines = [
        f"# Background Task: {task_id}",
        "",
        "## Request",
        "Continuous entropy cleanup: open tiny refactor PR(s) for invariant drift/slop patterns.",
        "",
        "## Status",
        "🕒 Queued",
        "",
        "## Started",
        now_iso(),
        "",
        "## Constraints",
        f"- Max files per cleanup task: {max_files_per_task}",
        f"- Max tasks this run: {max_tasks}",
        "- Non-behavioral refactors only",
        "- Keep commits/PRs small and focused",
        "",
        "## Candidate Tasks",
        "",
    ]
    if not candidates:
        lines.extend(["- No candidates found.", ""])
    else:
        for t in candidates:
            lines.append(f"### {t['name']}")
            lines.append(f"- Files: {', '.join(f'`{f}`' for f in t['files'])}")
            lines.append(f"- Rules: {', '.join(f'`{r}`' for r in t['rules']) if t['rules'] else '[none]'}")
            lines.append(f"- Findings: {t['findingCount']}")
            lines.append(f"- Action: {t['action']}")
            lines.append("")

    lines.extend(
        [
            "## Log",
            "- Generated by `python3 scripts/workflow_checks.py entropy --write-task`",
            "",
        ]
    )
    write_text(task_path, "\n".join(lines))
    return task_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run package-aware workflow checks.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify-ci", help="Run CI verification checks and write VERIFICATION-CI artifacts.")
    v.add_argument("feature", help="Feature slug (docs/planning/work/features/<feature>/)")

    r = sub.add_parser("review", help="Run review checks and write REVIEW artifacts.")
    r.add_argument("--feature", help="Feature slug (overrides memory inference).")

    e = sub.add_parser(
        "entropy",
        help="Run invariant scan and optionally write a background entropy-cleanup task.",
    )
    e.add_argument("--write-task", action="store_true", help="Write docs/planning/work/background/*-entropy-cleanup-TASK.md")
    e.add_argument("--max-files", type=int, help="Override max files per entropy cleanup task.")
    e.add_argument("--max-tasks", type=int, help="Override max cleanup tasks generated per run.")

    args = parser.parse_args()
    root = repo_root()
    wf = load_workflow(root)
    invariant_findings = run_invariant_checks(root, wf)
    review_principles = _review_principles(wf)

    if args.cmd == "entropy":
        ecfg = _entropy_cfg(wf)
        if not ecfg.get("enabled", True):
            print("Entropy cleanup is disabled in WORKFLOW.json (entropy.enabled=false).")
            return 0
        max_files = args.max_files if isinstance(args.max_files, int) and args.max_files > 0 else int(ecfg.get("maxFilesPerTask", 3))
        max_tasks = args.max_tasks if isinstance(args.max_tasks, int) and args.max_tasks > 0 else int(ecfg.get("maxTasksPerRun", 3))
        summary = summarize_invariants(invariant_findings)
        print(
            json.dumps(
                {
                    "invariants": summary,
                    "candidates": _entropy_candidates(
                        invariant_findings,
                        max_files_per_task=max_files,
                        max_tasks=max_tasks,
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        if args.write_task:
            task_path = write_entropy_task(
                root,
                invariant_findings,
                max_files_per_task=max_files,
                max_tasks=max_tasks,
            )
            print(f"Wrote entropy background task: {task_path}")
        return 1 if summary["fail"] > 0 else 0

    pkgs = packages_from_workflow(wf)
    if not pkgs:
        print("⚠️ No packages configured in docs/planning/WORKFLOW.json (packages[]).")
        print("Proceeding with empty package set; checks will be recorded as skipped.")
        print("Optional setup: python3 scripts/workflow_detect.py --write-workflow")
        per_pkg: list[dict[str, Any]] = []
    else:
        per_pkg = run_package_checks(root, pkgs)

    if args.cmd == "verify-ci":
        return write_verify_ci(root, args.feature, per_pkg, invariant_findings)

    if args.cmd == "review":
        feature = args.feature or infer_feature_from_state(root)
        return write_review(root, feature, per_pkg, invariant_findings, review_principles)

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
