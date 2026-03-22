"""Tests for the dispatch circuit breaker (dispatch_ledger.py)."""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".cnogo"))

from scripts.workflow.orchestration.dispatch_ledger import (
    _artifact_fingerprint,
    _backoff_minutes,
    _PERMANENT_HOLD_THRESHOLD,
    check_dispatch_hold,
    clear_dispatch_hold_on_success,
    list_dispatch_holds,
    load_dispatch_ledger,
    record_dispatch_failure,
    reset_dispatch_hold,
    save_dispatch_ledger,
)


@pytest.fixture
def tmp_root(tmp_path):
    """Create a minimal project root with work-orders dir."""
    wo_dir = tmp_path / ".cnogo" / "work-orders"
    wo_dir.mkdir(parents=True)
    feat_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
    feat_dir.mkdir(parents=True)
    (feat_dir / "FEATURE.json").write_text('{"schemaVersion": 1}')
    (feat_dir / "CONTEXT.json").write_text('{"schemaVersion": 1}')
    return tmp_path


class TestRecordAndLoad:
    def test_record_creates_ledger(self, tmp_root):
        ledger = record_dispatch_failure(
            tmp_root, "test-feature", phase="plan", error="missing relatedCode"
        )
        assert ledger["feature"] == "test-feature"
        assert ledger["consecutiveFailures"] == 1
        assert len(ledger["attempts"]) == 1
        assert ledger["attempts"][0]["phase"] == "plan"
        assert ledger["attempts"][0]["error"] == "missing relatedCode"
        assert ledger["holdUntil"]  # non-empty

    def test_record_increments_failures(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err1")
        ledger = record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err2")
        assert ledger["consecutiveFailures"] == 2
        assert len(ledger["attempts"]) == 2

    def test_load_returns_none_if_missing(self, tmp_root):
        assert load_dispatch_ledger(tmp_root, "nonexistent") is None

    def test_save_and_load_roundtrip(self, tmp_root):
        ledger = {"feature": "test-feature", "consecutiveFailures": 3, "holdUntil": "", "attempts": []}
        save_dispatch_ledger(tmp_root, "test-feature", ledger)
        loaded = load_dispatch_ledger(tmp_root, "test-feature")
        assert loaded["consecutiveFailures"] == 3

    def test_attempts_capped_at_10(self, tmp_root):
        for i in range(15):
            record_dispatch_failure(tmp_root, "test-feature", phase="plan", error=f"err{i}")
        ledger = load_dispatch_ledger(tmp_root, "test-feature")
        assert len(ledger["attempts"]) == 10
        assert ledger["consecutiveFailures"] == 15


class TestCheckHold:
    def test_no_ledger_means_no_hold(self, tmp_root):
        assert check_dispatch_hold(tmp_root, "test-feature") is None

    def test_hold_active_within_window(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        hold = check_dispatch_hold(tmp_root, "test-feature")
        assert hold is not None
        assert hold["held"] is True
        assert "circuit_breaker" in hold["reason"]
        assert hold["consecutiveFailures"] == 1

    def test_hold_expired_allows_dispatch(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        # Manually set holdUntil to the past
        ledger = load_dispatch_ledger(tmp_root, "test-feature")
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        ledger["holdUntil"] = past
        save_dispatch_ledger(tmp_root, "test-feature", ledger)
        assert check_dispatch_hold(tmp_root, "test-feature") is None

    def test_artifact_change_auto_resets(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        # Confirm hold is active
        assert check_dispatch_hold(tmp_root, "test-feature") is not None
        # Modify CONTEXT.json to simulate user fix
        ctx = tmp_root / "docs" / "planning" / "work" / "features" / "test-feature" / "CONTEXT.json"
        ctx.write_text('{"schemaVersion": 1, "relatedCode": ["foo.py"]}')
        # Fingerprint changed → hold should auto-reset
        assert check_dispatch_hold(tmp_root, "test-feature") is None


class TestReset:
    def test_manual_reset_clears_hold(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        assert check_dispatch_hold(tmp_root, "test-feature") is not None
        reset_dispatch_hold(tmp_root, "test-feature", reason="user_fixed_it")
        assert check_dispatch_hold(tmp_root, "test-feature") is None

    def test_reset_returns_false_if_no_ledger(self, tmp_root):
        assert reset_dispatch_hold(tmp_root, "nonexistent") is False

    def test_clear_on_success(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        clear_dispatch_hold_on_success(tmp_root, "test-feature")
        assert check_dispatch_hold(tmp_root, "test-feature") is None

    def test_clear_on_success_noop_without_ledger(self, tmp_root):
        # Should not raise
        clear_dispatch_hold_on_success(tmp_root, "nonexistent")


class TestBackoff:
    def test_backoff_schedule(self):
        assert _backoff_minutes(1) == 30
        assert _backoff_minutes(2) == 120
        assert _backoff_minutes(3) == 480
        assert _backoff_minutes(4) >= 525_600  # permanent

    def test_escalating_hold_duration(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err1")
        ledger1 = load_dispatch_ledger(tmp_root, "test-feature")
        hold1 = datetime.fromisoformat(ledger1["holdUntil"].replace("Z", "+00:00"))

        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err2")
        ledger2 = load_dispatch_ledger(tmp_root, "test-feature")
        hold2 = datetime.fromisoformat(ledger2["holdUntil"].replace("Z", "+00:00"))

        # Second hold should be further in the future than first
        assert hold2 > hold1


class TestFingerprint:
    def test_fingerprint_changes_on_file_edit(self, tmp_root):
        fp1 = _artifact_fingerprint(tmp_root, "test-feature")
        ctx = tmp_root / "docs" / "planning" / "work" / "features" / "test-feature" / "CONTEXT.json"
        time.sleep(0.01)  # Ensure mtime changes
        ctx.write_text('{"schemaVersion": 1, "updated": true}')
        fp2 = _artifact_fingerprint(tmp_root, "test-feature")
        assert fp1 != fp2

    def test_fingerprint_handles_missing_files(self, tmp_root):
        fp = _artifact_fingerprint(tmp_root, "nonexistent-feature")
        assert "missing" in fp


class TestListHolds:
    def test_list_holds_empty(self, tmp_root):
        assert list_dispatch_holds(tmp_root) == []

    def test_list_holds_returns_active_holds(self, tmp_root):
        record_dispatch_failure(tmp_root, "test-feature", phase="plan", error="err")
        holds = list_dispatch_holds(tmp_root)
        assert len(holds) == 1
        assert holds[0]["feature"] == "test-feature"
