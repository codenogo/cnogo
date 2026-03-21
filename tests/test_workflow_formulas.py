"""Tests for workflow formula resolution and policy helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory.bridge import recommend_team_mode  # noqa: E402
from scripts.workflow.shared.formulas import (  # noqa: E402
    formula_auto_spawn_configured_reviewers,
    formula_required_reviewers,
    resolve_formula,
)


def _write_workflow(root: Path, *, default_formula: str = "feature-delivery") -> None:
    planning_dir = root / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps(
            {
                "version": 1,
                "repoShape": "single",
                "formulas": {
                    "default": default_formula,
                    "catalogPath": ".cnogo/formulas",
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


def test_resolve_formula_uses_workflow_default(tmp_path):
    _write_workflow(tmp_path, default_formula="migration-rollout")

    resolved = resolve_formula(tmp_path)

    assert resolved["name"] == "migration-rollout"
    assert resolved["resolvedPolicy"]["execution"]["modePreference"] == "serial"


def test_resolve_formula_allows_plan_override(tmp_path):
    _write_workflow(tmp_path, default_formula="feature-delivery")
    formulas_dir = tmp_path / ".cnogo" / "formulas"
    formulas_dir.mkdir(parents=True, exist_ok=True)
    (formulas_dir / "custom.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "custom-formula",
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

    resolved = resolve_formula(tmp_path, plan_contract={"formula": "custom-formula"})

    assert resolved["name"] == "custom-formula"
    assert resolved["version"] == "2.0.0"
    assert resolved["resolvedPolicy"]["execution"]["modePreference"] == "team"
    assert formula_required_reviewers(resolved) == ["code-reviewer", "qa-reviewer"]


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


def test_formula_auto_spawn_defaults_true_and_can_disable():
    assert formula_auto_spawn_configured_reviewers(None) is True
    assert (
        formula_auto_spawn_configured_reviewers(
            {"resolvedPolicy": {"review": {"autoSpawnConfiguredReviewers": False}}}
        )
        is False
    )
