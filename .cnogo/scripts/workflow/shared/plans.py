"""Shared helpers for plan contracts."""

from __future__ import annotations

from typing import Any


def normalize_plan_number(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:02d}"
    text = str(value or "").strip()
    return text.zfill(2) if text.isdigit() and len(text) < 2 else text
