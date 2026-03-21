"""Common validator primitives and iterators."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

FEATURE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
QUICK_DIR_RE = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")
PLAN_MD_RE = re.compile(r"^(?P<num>[0-9]{2})-PLAN\.md$")
SUMMARY_MD_RE = re.compile(r"^(?P<num>[0-9]{2})-SUMMARY\.md$")
SHAPE_CANDIDATE_STATUSES = {"draft", "discuss-ready", "blocked", "parked"}


def is_positive_int(val: Any, *, allow_zero: bool = False) -> bool:
    """Check val is a real int (not bool) and positive (or >= 0 if allow_zero)."""
    return isinstance(val, int) and not isinstance(val, bool) and (val >= 0 if allow_zero else val > 0)


def require(path: Path, findings: list[Any], msg: str, *, finding_type: Any) -> None:
    if not path.exists():
        findings.append(finding_type("ERROR", msg, str(path)))


def validate_memory_runtime(root: Path, findings: list[Any], *, finding_type: Any) -> None:
    """Treat tracked memory sync data as sufficient for source validation."""
    memory_db = root / ".cnogo" / "memory.db"
    issues_jsonl = root / ".cnogo" / "issues.jsonl"
    if memory_db.exists() or issues_jsonl.exists():
        return
    findings.append(
        finding_type(
            "WARN",
            (
                "Memory runtime is not initialized locally. "
                "Run: python3 .cnogo/scripts/workflow_memory.py init "
                "to enable memory commands."
            ),
            str(memory_db),
        )
    )


def validate_feature_slug(name: str, findings: list[Any], path: Path, *, finding_type: Any) -> None:
    if not FEATURE_SLUG_RE.match(name):
        findings.append(
            finding_type(
                "ERROR",
                "Feature directory must be kebab-case slug (lowercase letters/numbers/hyphens). Example: 'websocket-notifications'.",
                str(path),
            )
        )


def is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def word_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").split())
    except Exception:
        return 0


def iter_feature_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "features"
    if not base.is_dir():
        return []
    return [path for path in base.iterdir() if path.is_dir()]


def iter_quick_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "quick"
    if not base.is_dir():
        return []
    return [path for path in base.iterdir() if path.is_dir()]


def iter_research_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "research"
    if not base.is_dir():
        return []
    return [path for path in base.iterdir() if path.is_dir()]


def iter_ideas_dirs(root: Path) -> Iterable[Path]:
    base = root / "docs" / "planning" / "work" / "ideas"
    if not base.is_dir():
        return []
    return [path for path in base.iterdir() if path.is_dir()]
