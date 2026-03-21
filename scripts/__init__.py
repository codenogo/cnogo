"""Repo-root import shim for cnogo runtime modules.

Allows `from scripts...` imports from the repository root without requiring
`PYTHONPATH=.cnogo`.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CNOGO_SCRIPTS = _ROOT / ".cnogo" / "scripts"

__path__ = [str(_CNOGO_SCRIPTS)]
