"""Tests for plan/review policy enforcement in workflow_validate_core."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_validate_core as core


def _messages(findings):
    return [f.message for f in findings]


def test_plan_v1_is_backward_compatible_without_microsteps():
    findings = []
    contract = {
        "schemaVersion": 1,
        "feature": "demo",
        "planNumber": "01",
        "goal": "legacy",
        "tasks": [
            {
                "name": "legacy task",
                "files": ["a.py"],
                "action": "change a.py",
                "verify": ["pytest -q"],
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert not any("microSteps" in m for m in msgs)
    assert not any("schemaVersion>=2 requires 'tdd' object" in m for m in msgs)


def test_plan_v2_requires_microsteps_and_tdd():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "new policy",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "action": "change a.py",
                "verify": ["pytest -q"],
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("requires non-empty 'microSteps' array" in m for m in msgs)
    assert any("requires 'tdd' object" in m for m in msgs)


def test_plan_v2_tdd_required_needs_failing_and_passing_verify():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "tdd strict",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "microSteps": ["write failing test", "implement", "run passing tests"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {"required": True},
            }
        ],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("requires non-empty failingVerify[] commands" in m for m in msgs)
    assert any("requires non-empty passingVerify[] commands" in m for m in msgs)


def test_plan_v2_rationalized_tdd_exemption_is_rejected():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "tdd strict",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "microSteps": ["tiny edit"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {"required": False, "reason": "too small, probably fine"},
            }
        ],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("appears rationalized" in m for m in msgs)


def test_review_v4_requires_stage_reviews_when_enabled(tmp_path):
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "REVIEW.md").write_text("# Review\n", encoding="utf-8")
    (feature_dir / "REVIEW.json").write_text(
        '{"schemaVersion":4,"verdict":"pass","securityFindings":[],"performanceFindings":[],"patternCompliance":[]}',
        encoding="utf-8",
    )
    findings = []
    core._validate_ci_verification(
        feature_dir,
        findings,
        "warn",
        "error",
        "error",
    )
    msgs = _messages(findings)
    assert any("requires stageReviews[spec-compliance, code-quality]" in m for m in msgs)


def test_review_requires_schema_v4_when_two_stage_policy_enabled(tmp_path):
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "REVIEW.md").write_text("# Review\n", encoding="utf-8")
    (feature_dir / "REVIEW.json").write_text(
        '{"schemaVersion":3,"verdict":"pass","securityFindings":[],"performanceFindings":[],"patternCompliance":[]}',
        encoding="utf-8",
    )
    findings = []
    core._validate_ci_verification(
        feature_dir,
        findings,
        "warn",
        "error",
        "error",
    )
    msgs = _messages(findings)
    assert any("must set schemaVersion>=4" in m for m in msgs)


def test_workflow_config_accepts_task_ownership_and_max_takeovers(tmp_path):
    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "enforcement": {
            "taskOwnership": "error",
        },
        "agentTeams": {
            "staleIndicatorMinutes": 10,
            "maxTakeoversPerTask": 2,
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert not any("enforcement.taskOwnership should be off|warn|error" in m for m in msgs)
    assert not any("agentTeams.maxTakeoversPerTask should be an integer >= 0" in m for m in msgs)


def test_workflow_config_rejects_invalid_task_ownership_and_max_takeovers(tmp_path):
    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "enforcement": {
            "taskOwnership": "hard",
        },
        "agentTeams": {
            "maxTakeoversPerTask": -1,
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert any("enforcement.taskOwnership should be off|warn|error" in m for m in msgs)
    assert any("agentTeams.maxTakeoversPerTask should be an integer >= 0" in m for m in msgs)
