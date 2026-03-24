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
    import os
    import tempfile
    marker = worktree_root / _CNOGO_DIR / _CONTROL_PLANE_MARKER
    marker.parent.mkdir(parents=True, exist_ok=True)
    content = str(control_root.resolve()) + "\n"
    # Atomic write: temp file + os.replace to prevent partial-write corruption.
    fd, tmp = tempfile.mkstemp(dir=str(marker.parent), suffix=".tmp")
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
        os.close(fd)
        os.replace(tmp, str(marker))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return marker
