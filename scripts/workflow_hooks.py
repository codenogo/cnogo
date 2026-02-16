#!/usr/bin/env python3
"""
Workflow hooks runner to reduce latency.

Used by .claude/settings.json PostToolUse hooks to format only edited files when possible.
No external dependencies.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from workflow_utils import load_workflow, repo_root


def _iter_possible_paths(obj: Any) -> Iterable[str]:
    """
    Heuristically extract file paths from CLAUDE_TOOL_INPUT. Claude Code tool input is typically JSON-ish.
    We try a few known key names and also fall back to scanning for strings that look like paths.
    """
    if obj is None:
        return
    if isinstance(obj, dict):
        for k in ["target_file", "path", "file", "filename"]:
            v = obj.get(k)
            if isinstance(v, str):
                yield v
        # Recurse into dict values
        for v in obj.values():
            yield from _iter_possible_paths(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from _iter_possible_paths(it)
    elif isinstance(obj, str):
        # Sometimes the whole input is a string path
        yield obj


PATH_LIKE_RE = re.compile(r"""(?x)
(
  (?:\./|/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+
)
""")


def extract_edited_files(raw_input: str, root: Path) -> list[Path]:
    candidates: set[Path] = set()
    raw_input = raw_input.strip()
    if not raw_input:
        return []

    # Attempt JSON parse first
    parsed: Any = None
    try:
        parsed = json.loads(raw_input)
    except Exception:
        parsed = None

    if parsed is not None:
        for s in _iter_possible_paths(parsed):
            s = s.strip()
            if not s:
                continue
            p = Path(s)
            if not p.is_absolute():
                p = (root / p).resolve()
            candidates.add(p)

    # Fallback: regex scan for path-like strings
    for m in PATH_LIKE_RE.finditer(raw_input):
        s = m.group(1)
        if not s:
            continue
        p = Path(s)
        if not p.is_absolute():
            p = (root / p).resolve()
        candidates.add(p)

    # Filter to files within repo
    filtered: list[Path] = []
    root_res = root.resolve()
    for p in candidates:
        try:
            pr = p.resolve()
            if root_res in pr.parents or pr == root_res:
                if pr.is_file():
                    filtered.append(pr)
        except Exception:
            continue
    return sorted(set(filtered))


def which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(cmd: list[str], *, cwd: Path) -> int:
    try:
        subprocess.check_call(cmd, cwd=cwd)
        return 0
    except subprocess.CalledProcessError as e:
        return int(e.returncode or 1)
    except Exception:
        return 1


def post_edit() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not raw.strip():
        return 0

    root = repo_root()
    cfg = load_workflow()
    perf = cfg.get("performance") if isinstance(cfg.get("performance"), dict) else {}
    enabled = perf.get("postEditFormat", "auto")
    scope = perf.get("postEditFormatScope", "changed")

    if enabled in {"off", False, "false"}:
        return 0
    edited = extract_edited_files(raw, root)

    # If we couldn't identify files, fall back (auto) to repo-wide formatter command.
    if not edited or scope == "repo":
        return run_repo_formatters(root)

    return run_changed_formatters(root, edited)


def run_repo_formatters(root: Path) -> int:
    # Mirror the old behavior, but keep it best-effort and fast.
    # Prefer a project-provided formatter if it exists.
    if (root / "pom.xml").exists():
        return run(["mvn", "spotless:apply", "-q"], cwd=root)
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        return run(["./gradlew", "spotlessApply", "-q"], cwd=root)
    if (root / "package.json").exists():
        # Only run npm format when the script exists; otherwise best-effort no-op.
        try:
            pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {}) if isinstance(pkg, dict) else {}
            if isinstance(scripts, dict):
                fmt = scripts.get("format")
                if isinstance(fmt, str) and fmt.strip():
                    return run(["npm", "run", "format", "--silent"], cwd=root)
        except Exception:
            pass
        return 0
    if (root / "pyproject.toml").exists():
        rc1 = run(["python3", "-m", "black", ".", "-q"], cwd=root) if which("black") else 0
        rc2 = run(["python3", "-m", "isort", ".", "-q"], cwd=root) if which("isort") else 0
        return 0 if (rc1 == 0 and rc2 == 0) else 1
    if (root / "setup.py").exists():
        return run(["python3", "-m", "black", ".", "-q"], cwd=root) if which("black") else 0
    if (root / "go.mod").exists():
        # repo-wide gofmt is expensive; avoid by preferring changed-file mode.
        return 0
    if (root / "Cargo.toml").exists():
        return run(["cargo", "fmt"], cwd=root)
    return 0


def run_changed_formatters(root: Path, files: list[Path]) -> int:
    # Group by extension
    py = [f for f in files if f.suffix == ".py"]
    go = [f for f in files if f.suffix == ".go"]
    js = [f for f in files if f.suffix in {".js", ".jsx", ".ts", ".tsx", ".json", ".md", ".yml", ".yaml"}]
    rs = [f for f in files if f.suffix == ".rs"]

    ok = True

    if py:
        if which("black"):
            ok = ok and (run(["python3", "-m", "black", "-q", *map(str, py)], cwd=root) == 0)
        if which("isort"):
            ok = ok and (run(["python3", "-m", "isort", "-q", *map(str, py)], cwd=root) == 0)

    if go:
        if which("gofmt"):
            ok = ok and (run(["gofmt", "-w", *map(str, go)], cwd=root) == 0)
        if which("goimports"):
            ok = ok and (run(["goimports", "-w", *map(str, go)], cwd=root) == 0)

    if rs:
        # cargo fmt isn't file-scoped; keep best-effort.
        if (root / "Cargo.toml").exists():
            ok = ok and (run(["cargo", "fmt"], cwd=root) == 0)

    if js and (root / "package.json").exists():
        # Prefer prettier on specific files when available; fallback to npm run format.
        prettier = root / "node_modules" / ".bin" / "prettier"
        if prettier.exists():
            ok = ok and (run([str(prettier), "--write", *map(str, js)], cwd=root) == 0)
        else:
            # If the repo defines a fast "format" script, this may still be expensive.
            ok = ok and (run(["npm", "run", "format", "--silent"], cwd=root) == 0)

    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: workflow_hooks.py post_edit", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd == "post_edit":
        return post_edit()
    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
