"""Shared artifact path and timestamp helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from scripts.workflow.shared.timestamps import parse_iso_timestamp


def resolve_contract_ref(root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def artifact_time(
    markdown_path: Path,
    contract_path: Path | None = None,
    *,
    load_json: Callable[[Path], Any],
) -> datetime | None:
    """Best-effort artifact timestamp from contract.timestamp, then file mtime."""
    if contract_path is not None and contract_path.exists():
        try:
            data = load_json(contract_path)
            if isinstance(data, dict):
                dt = parse_iso_timestamp(data.get("timestamp"))
                if dt is not None:
                    return dt
        except Exception:
            pass
    if markdown_path.exists():
        try:
            return datetime.fromtimestamp(markdown_path.stat().st_mtime, tz=timezone.utc)
        except Exception:
            return None
    return None


def linked_artifact_time(
    root: Path,
    raw_path: str,
    *,
    load_json: Callable[[Path], Any],
) -> datetime | None:
    resolved = resolve_contract_ref(root, raw_path)
    if resolved.suffix == ".json":
        markdown_path = resolved.with_suffix(".md")
        return artifact_time(markdown_path if markdown_path.exists() else resolved, resolved, load_json=load_json)
    if resolved.suffix == ".md":
        contract_path = resolved.with_suffix(".json")
        return artifact_time(resolved, contract_path if contract_path.exists() else None, load_json=load_json)
    return artifact_time(resolved, None, load_json=load_json)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def age_days(dt: datetime | None, *, now: Callable[[], datetime] = utc_now) -> int | None:
    if dt is None:
        return None
    delta = now() - dt
    return max(0, int(delta.total_seconds() // 86400))
