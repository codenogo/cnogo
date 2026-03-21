"""Phase helpers for the memory engine façade."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import storage as _st
from .runtime import auto_export as _auto_export
from .runtime import conn as _conn
from .storage import with_retry as _with_retry

_PHASE_STATE_PATH = Path(".cnogo") / "feature-phases.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _phase_state_path(root: Path) -> Path:
    return root / _PHASE_STATE_PATH


def _load_phase_state(root: Path) -> dict[str, Any]:
    path = _phase_state_path(root)
    if not path.exists():
        return {"schemaVersion": 1, "features": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schemaVersion": 1, "features": {}}
    if not isinstance(payload, dict):
        return {"schemaVersion": 1, "features": {}}
    features = payload.get("features")
    if not isinstance(features, dict):
        features = {}
    return {
        "schemaVersion": 1,
        "features": features,
    }


def _save_phase_state(root: Path, payload: dict[str, Any]) -> None:
    path = _phase_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_feature_phase(root: Path, feature_slug: str) -> str:
    phase_state = _load_phase_state(root)
    features = phase_state.get("features", {})
    if isinstance(features, dict):
        entry = features.get(feature_slug)
        if isinstance(entry, dict):
            phase = entry.get("phase")
            if isinstance(phase, str) and phase.strip():
                return _st.normalize_phase(phase)

    conn = _conn(root)
    try:
        return _st.get_feature_phase(conn, feature_slug)
    finally:
        conn.close()


def set_feature_phase(root: Path, feature_slug: str, phase: str) -> int:
    normalized = _st.normalize_phase(phase)

    def _do_set() -> int:
        conn = _conn(root)
        try:
            conn.execute("BEGIN IMMEDIATE")
            count = _st.set_feature_phase(conn, feature_slug, normalized)
            conn.commit()
            return count
        finally:
            conn.close()

    count = _with_retry(_do_set)
    if feature_slug:
        payload = _load_phase_state(root)
        features = payload.setdefault("features", {})
        if isinstance(features, dict):
            features[feature_slug] = {"phase": normalized, "updatedAt": _now_iso()}
            _save_phase_state(root, payload)
    _auto_export(root)
    return count or (1 if feature_slug else 0)
