"""Dispatch circuit breaker — prevents infinite re-lease of failing features.

Tracks dispatch failures per feature in a ledger file. The dispatcher consults
the ledger before leasing. The ledger auto-resets when feature artifacts change.

Single-writer assumption: only the dispatcher (or CLI via dispatch-reset) writes
to ledger files. Concurrent writes are not guarded with file locks.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.atomic_write import atomic_write_json
from scripts.workflow.shared.runtime_root import runtime_path

# Backoff schedule: consecutive failures → hold duration in minutes.
_BACKOFF_MINUTES = {
    1: 30,       # 30 min
    2: 120,      # 2 hours
    3: 480,      # 8 hours
}
_PERMANENT_HOLD_THRESHOLD = 4  # 4+ failures → hold until artifact change or manual reset
_PERMANENT_HOLD_MINUTES = 525_600  # ~1 year (effectively permanent)
_MAX_ATTEMPTS_KEPT = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ledger_dir(root: Path) -> Path:
    """Dispatch ledgers live in their own directory, separate from work orders."""
    return runtime_path(root, "dispatch-ledgers")


def _ledger_path(root: Path, feature: str) -> Path:
    return _ledger_dir(root) / f"{feature}.json"


def _artifact_fingerprint(root: Path, feature: str) -> str:
    """Compute a fingerprint from FEATURE.json and CONTEXT.json mtimes + sizes.

    Changes to either file indicate the user may have fixed the problem.
    """
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    parts: list[str] = []
    for name in ("FEATURE.json", "CONTEXT.json"):
        p = feature_dir / name
        if p.exists():
            st = p.stat()
            parts.append(f"{name}:{st.st_mtime_ns}:{st.st_size}")
        else:
            parts.append(f"{name}:missing")
    return "|".join(parts)


def _backoff_minutes(consecutive_failures: int) -> int:
    if consecutive_failures >= _PERMANENT_HOLD_THRESHOLD:
        return _PERMANENT_HOLD_MINUTES
    return _BACKOFF_MINUTES.get(consecutive_failures, 30)


def load_dispatch_ledger(root: Path, feature: str) -> dict[str, Any] | None:
    """Load the dispatch ledger for a feature, or None if absent."""
    path = _ledger_path(root, feature)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_dispatch_ledger(root: Path, feature: str, ledger: dict[str, Any]) -> Path:
    """Persist a dispatch ledger."""
    path = _ledger_path(root, feature)
    atomic_write_json(path, ledger, sort_keys=False)
    return path


def record_dispatch_failure(
    root: Path,
    feature: str,
    *,
    phase: str,
    error: str,
    lane_id: str = "",
) -> dict[str, Any]:
    """Record a dispatch failure and compute the hold.

    Returns the updated ledger.
    """
    ledger = load_dispatch_ledger(root, feature) or {
        "feature": feature,
        "consecutiveFailures": 0,
        "holdUntil": "",
        "artifactFingerprint": "",
        "attempts": [],
    }
    ledger["consecutiveFailures"] = ledger.get("consecutiveFailures", 0) + 1
    attempts = ledger.get("attempts", [])
    attempts.append({
        "phase": phase,
        "timestamp": _now_iso(),
        "error": (error[:997] + "...") if len(error) > 1000 else error,
        "laneId": lane_id,
    })
    ledger["attempts"] = attempts[-_MAX_ATTEMPTS_KEPT:]
    ledger["artifactFingerprint"] = _artifact_fingerprint(root, feature)

    hold_mins = _backoff_minutes(ledger["consecutiveFailures"])
    hold_until = datetime.now(timezone.utc) + timedelta(minutes=hold_mins)
    ledger["holdUntil"] = hold_until.strftime("%Y-%m-%dT%H:%M:%SZ")

    save_dispatch_ledger(root, feature, ledger)
    return ledger


def check_dispatch_hold(root: Path, feature: str) -> dict[str, Any] | None:
    """Check if a feature is held by the circuit breaker.

    Returns None if the feature can be dispatched.
    Returns a dict with hold details if the feature should be skipped:
        {"held": True, "reason": str, "holdUntil": str, "consecutiveFailures": int}

    Auto-resets the ledger if feature artifacts have changed since the last failure.
    """
    ledger = load_dispatch_ledger(root, feature)
    if ledger is None:
        return None

    consecutive = ledger.get("consecutiveFailures", 0)
    if consecutive == 0:
        return None

    # Auto-reset: if artifacts changed, the user likely fixed the problem.
    current_fp = _artifact_fingerprint(root, feature)
    stored_fp = ledger.get("artifactFingerprint", "")
    if stored_fp and current_fp != stored_fp:
        reset_dispatch_hold(root, feature, reason="artifact_changed")
        return None

    hold_until_str = ledger.get("holdUntil", "")
    if not hold_until_str:
        return None

    try:
        hold_until = datetime.fromisoformat(hold_until_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None

    now = datetime.now(timezone.utc)
    if now >= hold_until:
        # Hold expired — allow half-open probe (don't reset yet; reset on success)
        return None

    last_error = ""
    attempts = ledger.get("attempts", [])
    if attempts:
        last_error = attempts[-1].get("error", "")

    return {
        "held": True,
        "reason": f"circuit_breaker: {consecutive} consecutive {attempts[-1].get('phase', 'dispatch') if attempts else 'dispatch'} failure(s)",
        "holdUntil": hold_until_str,
        "consecutiveFailures": consecutive,
        "lastError": last_error,
    }


def reset_dispatch_hold(
    root: Path,
    feature: str,
    *,
    reason: str = "manual_reset",
) -> bool:
    """Reset the circuit breaker for a feature.

    Returns True if a ledger existed and was reset, False otherwise.
    """
    ledger = load_dispatch_ledger(root, feature)
    if ledger is None:
        return False
    ledger["consecutiveFailures"] = 0
    ledger["holdUntil"] = ""
    attempts = ledger.get("attempts", [])
    attempts.append({
        "phase": "reset",
        "timestamp": _now_iso(),
        "error": "",
        "laneId": "",
        "resetReason": reason,
    })
    ledger["attempts"] = attempts[-_MAX_ATTEMPTS_KEPT:]
    ledger["artifactFingerprint"] = _artifact_fingerprint(root, feature)
    save_dispatch_ledger(root, feature, ledger)
    return True


def clear_dispatch_hold_on_success(root: Path, feature: str) -> None:
    """Clear the circuit breaker after a successful dispatch (half-open → closed)."""
    ledger = load_dispatch_ledger(root, feature)
    if ledger is None or ledger.get("consecutiveFailures", 0) == 0:
        return
    reset_dispatch_hold(root, feature, reason="dispatch_success")


def list_dispatch_holds(root: Path) -> list[dict[str, Any]]:
    """List all features currently held by the circuit breaker."""
    ledger_dir = _ledger_dir(root)
    if not ledger_dir.exists():
        return []
    holds: list[dict[str, Any]] = []
    for path in sorted(ledger_dir.glob("*.json")):
        feature = path.stem
        hold = check_dispatch_hold(root, feature)
        if hold is not None:
            holds.append({"feature": feature, **hold})
    return holds
