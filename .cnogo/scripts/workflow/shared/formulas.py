"""Compatibility wrapper for legacy formula imports.

Canonical product language is now ``profile``. This module remains as a thin
alias layer so existing imports keep working during the migration window.
"""

from __future__ import annotations

from .profiles import *  # noqa: F401,F403
