"""Tests for ship-ready staged review and freshness gate."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_ship_ready_fails_when_review_missing(tmp_path):
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(feature_dir / "01-SUMMARY.json", {"timestamp": "2026-02-25T10:00:00Z"})
    rc = checks._cmd_ship_ready(tmp_path, feature, json_output=True)
    assert rc == 1


def test_ship_ready_fails_when_review_is_stale(tmp_path):
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(feature_dir / "01-SUMMARY.json", {"timestamp": "2026-02-25T10:00:00Z"})
    _write_json(
        feature_dir / "REVIEW.json",
        {
            "schemaVersion": 4,
            "timestamp": "2026-02-25T09:00:00Z",
            "stageReviews": [
                {"stage": "spec-compliance", "status": "pass", "findings": [], "evidence": ["cmd"]},
                {"stage": "code-quality", "status": "pass", "findings": [], "evidence": ["cmd"]},
            ],
        },
    )
    rc = checks._cmd_ship_ready(tmp_path, feature, json_output=True)
    assert rc == 1


def test_ship_ready_fails_when_stage_reviews_incomplete(tmp_path):
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(feature_dir / "01-SUMMARY.json", {"timestamp": "2026-02-25T09:00:00Z"})
    _write_json(
        feature_dir / "REVIEW.json",
        {
            "schemaVersion": 4,
            "timestamp": "2026-02-25T10:00:00Z",
            "stageReviews": [
                {"stage": "spec-compliance", "status": "pass", "findings": [], "evidence": ["cmd"]},
                {"stage": "code-quality", "status": "pending", "findings": [], "evidence": []},
            ],
        },
    )
    rc = checks._cmd_ship_ready(tmp_path, feature, json_output=True)
    assert rc == 1


def test_ship_ready_fails_when_any_stage_is_fail(tmp_path):
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(feature_dir / "01-SUMMARY.json", {"timestamp": "2026-02-25T09:00:00Z"})
    _write_json(
        feature_dir / "REVIEW.json",
        {
            "schemaVersion": 4,
            "timestamp": "2026-02-25T10:00:00Z",
            "stageReviews": [
                {"stage": "spec-compliance", "status": "pass", "findings": [], "evidence": ["cmd"]},
                {"stage": "code-quality", "status": "fail", "findings": ["blocker"], "evidence": ["cmd"]},
            ],
        },
    )
    rc = checks._cmd_ship_ready(tmp_path, feature, json_output=True)
    assert rc == 1


def test_ship_ready_passes_when_stages_complete_and_fresh(tmp_path):
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(feature_dir / "01-SUMMARY.json", {"timestamp": "2026-02-25T09:00:00Z"})
    _write_json(
        feature_dir / "REVIEW.json",
        {
            "schemaVersion": 4,
            "timestamp": "2026-02-25T10:00:00Z",
            "stageReviews": [
                {"stage": "spec-compliance", "status": "pass", "findings": [], "evidence": ["cmd"]},
                {"stage": "code-quality", "status": "warn", "findings": [], "evidence": ["cmd"]},
            ],
        },
    )
    rc = checks._cmd_ship_ready(tmp_path, feature, json_output=True)
    assert rc == 0


def test_write_review_starts_pending_final_verdict_but_preserves_automated_failure(tmp_path):
    feature = "demo"
    workflow_path = tmp_path / "docs" / "planning" / "WORKFLOW.json"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(
        json.dumps(
            {
                "version": 1,
                "packages": [],
                "agentTeams": {
                    "enabled": True,
                    "defaultCompositions": {
                        "review": ["code-reviewer", "security-scanner", "perf-analyzer"]
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    rc = checks.write_review(
        tmp_path,
        feature,
        per_pkg=[
            {
                "name": "api",
                "path": ".",
                "checks": [
                    {"name": "lint", "result": "fail"},
                    {"name": "test", "result": "pass"},
                ],
            }
        ],
        invariant_findings=[],
    )

    review_path = tmp_path / "docs" / "planning" / "work" / "features" / feature / "REVIEW.json"
    review_data = json.loads(review_path.read_text(encoding="utf-8"))
    assert review_data["automatedVerdict"] == "fail"
    assert review_data["verdict"] == "pending"
    assert review_data["reviewers"] == ["code-reviewer", "security-scanner", "perf-analyzer"]
    assert rc == 1
