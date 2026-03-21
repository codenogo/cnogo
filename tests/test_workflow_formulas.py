"""Tests for workflow profile resolution and legacy formula compatibility helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory.bridge import recommend_team_mode  # noqa: E402
from scripts.workflow.shared.profiles import (  # noqa: E402
    formula_required_reviewers,
    is_formula_name,
    is_profile_name,
    profile_auto_spawn_configured_reviewers,
    profile_required_reviewers,
    resolve_formula,
    resolve_profile,
    scaffold_formula_contract,
    scaffold_profile_contract,
    suggest_formula,
    suggest_profile,
)


def _write_workflow(root: Path, *, default_profile: str = "feature-delivery") -> None:
    planning_dir = root / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps(
            {
                "version": 1,
                "repoShape": "single",
                "profiles": {
                    "default": default_profile,
                    "catalogPath": ".cnogo/profiles",
                    "allowPlanOverride": True,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _task(index: int, *, path: str, blocked_by: list[int] | None = None) -> dict[str, object]:
    return {
        "plan_task_index": index,
        "title": f"Task {index}",
        "file_scope": {"paths": [path], "forbidden": []},
        "blockedBy": blocked_by or [],
    }


def test_resolve_profile_uses_workflow_default(tmp_path):
    _write_workflow(tmp_path, default_profile="migration-rollout")

    resolved = resolve_profile(tmp_path)

    assert resolved["name"] == "migration-rollout"
    assert resolved["resolvedPolicy"]["execution"]["modePreference"] == "serial"


def test_resolve_profile_allows_plan_override(tmp_path):
    _write_workflow(tmp_path, default_profile="feature-delivery")
    profiles_dir = tmp_path / ".cnogo" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "custom.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "custom-profile",
                "version": "2.0.0",
                "defaults": {
                    "execution": {"modePreference": "team"},
                    "review": {"requiredReviewers": ["code-reviewer", "qa-reviewer"]},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    resolved = resolve_profile(tmp_path, plan_contract={"profile": "custom-profile"})

    assert resolved["name"] == "custom-profile"
    assert resolved["version"] == "2.0.0"
    assert resolved["resolvedPolicy"]["execution"]["modePreference"] == "team"
    assert profile_required_reviewers(resolved) == ["code-reviewer", "qa-reviewer"]


def test_recommend_team_mode_respects_formula_serial_preference():
    tasks = [_task(0, path="a.py"), _task(1, path="b.py")]

    recommendation = recommend_team_mode(
        tasks,
        formula={
            "name": "migration-rollout",
            "resolvedPolicy": {"execution": {"modePreference": "serial"}},
        },
    )

    assert recommendation["recommended"] is False
    assert recommendation["reason"] == "Formula prefers serial execution for this kind of work."
    assert recommendation["formulaModePreference"] == "serial"


def test_profile_auto_spawn_defaults_true_and_can_disable():
    assert profile_auto_spawn_configured_reviewers(None) is True
    assert (
        profile_auto_spawn_configured_reviewers(
            {"resolvedPolicy": {"review": {"autoSpawnConfiguredReviewers": False}}}
        )
        is False
    )


def test_suggest_profile_prefers_migration_signals(tmp_path):
    _write_workflow(tmp_path)

    suggestion = suggest_profile(
        tmp_path,
        feature_slug="account-ledger-rollout",
        plan_contract={
            "goal": "Apply schema migration and backfill historical ledger data",
            "tasks": [{"name": "Add SQL migration", "action": "Backfill the new column"}],
        },
    )

    assert suggestion["name"] == "migration-rollout"
    assert "migration" in suggestion["matchedTerms"]


def test_suggest_profile_falls_back_to_repo_default(tmp_path):
    _write_workflow(tmp_path, default_profile="feature-delivery")

    suggestion = suggest_profile(
        tmp_path,
        feature_slug="profile-avatar",
        plan_contract={"goal": "Add avatar upload to the profile page"},
    )

    assert suggestion["name"] == "feature-delivery"
    assert suggestion["matchedTerms"] == []


def test_is_formula_name_requires_lowercase_slug():
    assert is_formula_name("feature-delivery") is True
    assert is_formula_name("debug-fix") is True
    assert is_formula_name("FeatureDelivery") is False
    assert is_formula_name("debug_fix") is False
    assert is_formula_name("bad space") is False


def test_is_profile_name_requires_lowercase_slug():
    assert is_profile_name("feature-delivery") is True
    assert is_profile_name("release-cut") is True
    assert is_profile_name("ReleaseCut") is False


def test_scaffold_profile_contract_uses_base_policy_copy():
    scaffold = scaffold_profile_contract(
        "incident-debug",
        base_profile={
            "resolvedPolicy": {
                "execution": {"modePreference": "serial", "preferTeamWhenSafe": False},
                "review": {"requiredReviewers": ["code-reviewer"]},
            }
        },
        description="Incident response policy.",
    )

    assert scaffold["name"] == "incident-debug"
    assert scaffold["description"] == "Incident response policy."
    assert scaffold["defaults"]["execution"]["modePreference"] == "serial"
    assert scaffold["defaults"]["review"]["requiredReviewers"] == ["code-reviewer"]


def test_legacy_formula_config_and_plan_override_still_load(tmp_path):
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps(
            {
                "version": 1,
                "repoShape": "single",
                "formulas": {
                    "default": "migration-rollout",
                    "catalogPath": ".cnogo/formulas",
                    "allowPlanOverride": True,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    resolved = resolve_profile(tmp_path, plan_contract={"formula": "debug-fix"})
    legacy = resolve_formula(tmp_path, plan_contract={"formula": "debug-fix"})

    assert resolved["name"] == "debug-fix"
    assert legacy["name"] == "debug-fix"
    assert formula_required_reviewers(legacy) == profile_required_reviewers(resolved)
