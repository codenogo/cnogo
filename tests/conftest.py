"""Pytest conftest: add .cnogo/ to sys.path for import resolution.

This ensures all test files that import from ``scripts.memory`` or
``scripts.context`` resolve to ``.cnogo/scripts/`` without needing
per-file path manipulation.
"""

import os
import sys

_cnogo_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".cnogo",
)
if _cnogo_dir not in sys.path:
    sys.path.insert(0, _cnogo_dir)
