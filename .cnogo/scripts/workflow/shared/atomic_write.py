"""Atomic JSON file writes for crash-safe state persistence.

Uses write-to-temp-then-rename (os.replace) which is atomic on POSIX.
Prevents partial-write corruption if the process is killed mid-write.

Inspired by Erlang/OTP's "let it crash" philosophy: if a write is
interrupted, the previous valid state file remains intact rather than
leaving a half-written corrupt file.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, *, indent: int = 2, sort_keys: bool = True) -> None:
    """Write JSON data to a file atomically.

    1. Write to a temp file in the same directory (same filesystem)
    2. fsync to ensure data hits disk
    3. os.replace() to atomically swap the temp file into place

    On POSIX, os.replace() is atomic — the file is either the old
    version or the new version, never a partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, sort_keys=sort_keys)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        # Clean up temp file on any failure (including KeyboardInterrupt).
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
