"""Helpers for separating tracked worktree files from shared runtime state."""

from __future__ import annotations

from pathlib import Path

_CNOGO_DIR = ".cnogo"
_CONTROL_PLANE_MARKER = "control-plane-root"


def runtime_root(root: Path) -> Path:
    """Return the control-plane root for runtime state.

    Feature and task worktrees keep their tracked files local, but runtime
    state such as lanes, runs, work orders, and the memory database should
    resolve back to the leader checkout when a marker is present.
    """

    marker = root / _CNOGO_DIR / _CONTROL_PLANE_MARKER
    if marker.exists():
        try:
            raw = marker.read_text(encoding="utf-8").strip()
        except Exception:
            raw = ""
        if raw:
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = (root / candidate).resolve()
            return candidate
    return root


def runtime_path(root: Path, *parts: str) -> Path:
    return runtime_root(root) / _CNOGO_DIR / Path(*parts)


def write_runtime_root_marker(worktree_root: Path, control_root: Path) -> Path:
    marker = worktree_root / _CNOGO_DIR / _CONTROL_PLANE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(control_root.resolve()) + "\n", encoding="utf-8")
    return marker
