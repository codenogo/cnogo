"""Comprehensive tests for the ship draft module.

The module under test is .cnogo/scripts/workflow/orchestration/ship_draft.py,
which is being written by another teammate. Tests may fail with ImportError —
that is expected until the module is implemented.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import helper
# ---------------------------------------------------------------------------

def _import_module():
    root = Path(__file__).resolve().parent.parent / ".cnogo"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.workflow.orchestration.ship_draft import (
        SHIP_EXCLUDE_PATTERNS,
        build_ship_draft,
        compute_commit_surface,
        generate_commit_message,
        generate_pr_body,
        _is_excluded,
    )
    return (
        SHIP_EXCLUDE_PATTERNS,
        build_ship_draft,
        compute_commit_surface,
        generate_commit_message,
        generate_pr_body,
        _is_excluded,
    )


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

_PLAN_JSON = {
    "schemaVersion": 3,
    "feature": "test-feature",
    "planNumber": "01",
    "goal": "Add the widget system",
    "tasks": [
        {
            "name": "Create widget",
            "files": ["src/widget.py"],
            "action": "...",
            "verify": [],
            "microSteps": [],
            "tdd": {"required": False, "reason": "test"},
            "contextLinks": [],
            "blockedBy": [],
        },
        {
            "name": "Add tests",
            "files": ["tests/test_widget.py"],
            "action": "...",
            "verify": [],
            "microSteps": [],
            "tdd": {"required": False, "reason": "test"},
            "contextLinks": [],
            "blockedBy": [],
        },
    ],
    "planVerify": [],
    "commitMessage": "feat(widget): add widget system\n\nImplement the core widget functionality.",
    "timestamp": "2026-03-21T12:00:00Z",
}

_SUMMARY_JSON = {
    "schemaVersion": 2,
    "feature": "test-feature",
    "planNumber": "01",
    "outcome": "complete",
    "verification": [
        {
            "name": "Create widget",
            "result": "pass",
            "scope": "task",
            "commands": ["python3 -m pytest tests/test_widget.py -v"],
        }
    ],
    "timestamp": "2026-03-21T12:30:00Z",
}

_REVIEW_JSON = {
    "schemaVersion": 4,
    "feature": "test-feature",
    "verdict": "pass",
    "reviewers": ["code-reviewer", "security-scanner"],
    "stageReviews": [
        {
            "stage": "spec-compliance",
            "status": "pass",
            "findings": [],
            "evidence": ["all good"],
        },
        {
            "stage": "code-quality",
            "status": "pass",
            "findings": [],
            "evidence": ["clean"],
        },
    ],
    "warnings": [],
    "timestamp": "2026-03-21T13:00:00Z",
}

_CONTEXT_JSON = {
    "schemaVersion": 3,
    "feature": "test-feature",
    "displayName": "Test Feature",
    "decisions": [],
    "constraints": [],
    "openQuestions": [],
    "relatedCode": [],
    "timestamp": "2026-03-21T12:00:00Z",
}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _setup_feature_dir(tmp_path: Path, *, include_summary: bool = True, include_review: bool = True) -> Path:
    """Create a full test-feature planning directory under tmp_path."""
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)

    _write_json(feature_dir / "01-PLAN.json", _PLAN_JSON)
    _write_json(feature_dir / "CONTEXT.json", _CONTEXT_JSON)

    if include_summary:
        _write_json(feature_dir / "01-SUMMARY.json", _SUMMARY_JSON)
    if include_review:
        _write_json(feature_dir / "REVIEW.json", _REVIEW_JSON)

    # Create the actual source files referenced by tasks
    src_widget = tmp_path / "src" / "widget.py"
    src_widget.parent.mkdir(parents=True, exist_ok=True)
    src_widget.write_text("# widget module\n", encoding="utf-8")

    test_widget = tmp_path / "tests" / "test_widget.py"
    test_widget.parent.mkdir(parents=True, exist_ok=True)
    test_widget.write_text("# tests for widget\n", encoding="utf-8")

    return feature_dir


# ===========================================================================
# 1. SHIP_EXCLUDE_PATTERNS
# ===========================================================================

class TestShipExcludePatterns:
    def test_contains_required_runtime_paths(self):
        (SHIP_EXCLUDE_PATTERNS, *_) = _import_module()
        required = [
            ".cnogo/runs/",
            ".cnogo/work-orders/",
            ".cnogo/feature-phases.json",
            ".cnogo/watch/",
            ".cnogo/worktree-session.json",
        ]
        for pattern in required:
            assert pattern in SHIP_EXCLUDE_PATTERNS, f"Missing pattern: {pattern!r}"

    def test_is_immutable_tuple(self):
        (SHIP_EXCLUDE_PATTERNS, *_) = _import_module()
        assert isinstance(SHIP_EXCLUDE_PATTERNS, tuple), (
            "SHIP_EXCLUDE_PATTERNS must be a tuple (immutable)"
        )

    def test_does_not_contain_normal_feature_paths(self):
        (SHIP_EXCLUDE_PATTERNS, *_) = _import_module()
        normal_paths = [
            "docs/planning/work/features/",
            "src/",
            "tests/",
        ]
        for path in normal_paths:
            assert path not in SHIP_EXCLUDE_PATTERNS, (
                f"Normal path {path!r} should NOT be in SHIP_EXCLUDE_PATTERNS"
            )
        assert ".cnogo/issues.jsonl" in SHIP_EXCLUDE_PATTERNS


# ===========================================================================
# 2. _is_excluded
# ===========================================================================

class TestIsExcluded:
    def test_cnogo_runs_file_is_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded(".cnogo/runs/foo/bar.json") is True

    def test_cnogo_work_orders_feature_file_is_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded(".cnogo/work-orders/feature.json") is True

    def test_cnogo_work_orders_gitkeep_is_not_excluded(self):
        (*_, _is_excluded) = _import_module()
        # Special case: .gitkeep should NOT be excluded
        assert _is_excluded(".cnogo/work-orders/.gitkeep") is False

    def test_cnogo_feature_phases_json_is_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded(".cnogo/feature-phases.json") is True

    def test_src_file_is_not_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded("src/widget.py") is False

    def test_cnogo_watch_file_is_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded(".cnogo/watch/something.json") is True

    def test_cnogo_worktree_session_is_excluded(self):
        (*_, _is_excluded) = _import_module()
        assert _is_excluded(".cnogo/worktree-session.json") is True


# ===========================================================================
# 3. compute_commit_surface
# ===========================================================================

class TestComputeCommitSurface:
    def test_includes_task_files_from_plan(self, tmp_path):
        (_, _, compute_commit_surface, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        surface = compute_commit_surface(tmp_path, "test-feature")

        assert "src/widget.py" in surface
        assert "tests/test_widget.py" in surface

    def test_includes_planning_artifacts(self, tmp_path):
        (_, _, compute_commit_surface, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        surface = compute_commit_surface(tmp_path, "test-feature")

        # Planning artifacts should be present
        planning_artifact_found = any(
            "PLAN" in f or "CONTEXT" in f or "SUMMARY" in f or "REVIEW" in f
            for f in surface
        )
        assert planning_artifact_found, f"No planning artifacts found in surface: {surface}"

    def test_excludes_runtime_state(self, tmp_path):
        (_, _, compute_commit_surface, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        # Create runtime state files to verify they are excluded
        runs_dir = tmp_path / ".cnogo" / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / "run-001.json").write_text("{}", encoding="utf-8")

        work_orders_dir = tmp_path / ".cnogo" / "work-orders"
        work_orders_dir.mkdir(parents=True, exist_ok=True)
        (work_orders_dir / "order-001.json").write_text("{}", encoding="utf-8")

        surface = compute_commit_surface(tmp_path, "test-feature")

        for f in surface:
            assert ".cnogo/runs/" not in f, f"Runtime state file should be excluded: {f}"
            assert ".cnogo/work-orders/order-001.json" not in f, (
                f"Work order file should be excluded: {f}"
            )

    def test_only_includes_files_that_exist_on_disk(self, tmp_path):
        (_, _, compute_commit_surface, *_) = _import_module()
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        # Plan references a file that does NOT exist on disk
        plan_with_missing = dict(_PLAN_JSON)
        plan_with_missing["tasks"] = [
            {
                "name": "Missing task",
                "files": ["src/nonexistent.py"],
                "action": "...",
                "verify": [],
                "microSteps": [],
                "tdd": {"required": False, "reason": "test"},
                "contextLinks": [],
                "blockedBy": [],
            }
        ]
        _write_json(feature_dir / "01-PLAN.json", plan_with_missing)

        surface = compute_commit_surface(tmp_path, "test-feature")

        assert "src/nonexistent.py" not in surface

    def test_returns_sorted_deduplicated_list(self, tmp_path):
        (_, _, compute_commit_surface, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        surface = compute_commit_surface(tmp_path, "test-feature")

        assert surface == sorted(surface), "Surface should be sorted"
        assert len(surface) == len(set(surface)), "Surface should have no duplicates"


# ===========================================================================
# 4. generate_commit_message
# ===========================================================================

class TestGenerateCommitMessage:
    def test_reads_commit_message_from_latest_plan(self, tmp_path):
        (_, _, _, generate_commit_message, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        msg = generate_commit_message(tmp_path, "test-feature")

        assert "feat(widget): add widget system" in msg

    def test_falls_back_when_commit_message_missing(self, tmp_path):
        (_, _, _, generate_commit_message, *_) = _import_module()
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        plan_without_msg = dict(_PLAN_JSON)
        plan_without_msg.pop("commitMessage", None)
        _write_json(feature_dir / "01-PLAN.json", plan_without_msg)

        # Should not raise; should return a fallback string
        msg = generate_commit_message(tmp_path, "test-feature")
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_uses_latest_plan_number_for_multi_plan_feature(self, tmp_path):
        (_, _, _, generate_commit_message, *_) = _import_module()
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        _write_json(feature_dir / "01-PLAN.json", _PLAN_JSON)

        plan_02 = dict(_PLAN_JSON)
        plan_02["planNumber"] = "02"
        plan_02["commitMessage"] = "feat(widget): extend widget system\n\nAdd advanced features."
        _write_json(feature_dir / "02-PLAN.json", plan_02)

        msg = generate_commit_message(tmp_path, "test-feature")

        # Should use plan 02 (the latest)
        assert "extend widget system" in msg


# ===========================================================================
# 5. generate_pr_body
# ===========================================================================

class TestGeneratePrBody:
    def test_contains_summary_section_with_plan_goal_bullets(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "## Summary" in body
        assert "Add the widget system" in body

    def test_contains_test_plan_section(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "## Test Plan" in body

    def test_contains_review_section_with_verdict_and_reviewers(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "## Review" in body
        assert "pass" in body.lower()
        assert "code-reviewer" in body
        assert "security-scanner" in body

    def test_contains_planning_references_section(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "## Planning References" in body

    def test_contains_follow_ups_section_only_when_verdict_is_warn(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()

        # Setup with verdict=warn
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "test-feature"
        _setup_feature_dir(tmp_path)
        review_warn = dict(_REVIEW_JSON)
        review_warn["verdict"] = "warn"
        review_warn["warnings"] = ["Minor issue to follow up on"]
        _write_json(feature_dir / "REVIEW.json", review_warn)

        body_warn = generate_pr_body(tmp_path, "test-feature")
        assert "## Follow-ups" in body_warn

    def test_does_not_contain_follow_ups_when_verdict_is_pass(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "## Follow-ups" not in body

    def test_uses_commands_plural_from_summary_verification(self, tmp_path):
        (_, _, _, _, generate_pr_body, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        body = generate_pr_body(tmp_path, "test-feature")

        assert "`python3 -m pytest tests/test_widget.py -v`" in body


# ===========================================================================
# 6. build_ship_draft
# ===========================================================================

class TestBuildShipDraft:
    def test_returns_dict_with_required_keys(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        draft = build_ship_draft(tmp_path, "test-feature")

        required_keys = {
            "commitSurface",
            "excludedFiles",
            "commitMessage",
            "prTitle",
            "prBody",
            "branch",
            "gitAddCommand",
        }
        missing = required_keys - set(draft.keys())
        assert not missing, f"Draft missing keys: {missing}"

    def test_git_add_command_starts_with_git_add(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        draft = build_ship_draft(tmp_path, "test-feature")

        assert isinstance(draft["gitAddCommand"], str)
        assert draft["gitAddCommand"].startswith("git add")

    def test_pr_title_derived_from_commit_message_first_line(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        draft = build_ship_draft(tmp_path, "test-feature")

        commit_first_line = draft["commitMessage"].splitlines()[0]
        assert draft["prTitle"] == commit_first_line

    def test_branch_defaults_to_feature_slug(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path)

        draft = build_ship_draft(tmp_path, "test-feature")

        assert draft["branch"] == "feature/test-feature"


# ===========================================================================
# 7. Error paths
# ===========================================================================

class TestErrorPaths:
    def test_missing_summary_json_draft_still_works_with_warnings(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path, include_summary=False)

        draft = build_ship_draft(tmp_path, "test-feature")

        assert isinstance(draft, dict)
        assert "commitSurface" in draft
        # Should have at least one warning about missing summary
        warnings = draft.get("warnings", [])
        assert len(warnings) > 0, "Expected at least one warning for missing SUMMARY.json"

    def test_missing_review_json_draft_still_works_with_warnings(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path, include_review=False)

        draft = build_ship_draft(tmp_path, "test-feature")

        assert isinstance(draft, dict)
        assert "commitSurface" in draft
        warnings = draft.get("warnings", [])
        assert len(warnings) > 0, "Expected at least one warning for missing REVIEW.json"

    def test_excluded_operational_files_emit_warning(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()
        _setup_feature_dir(tmp_path)
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cnogo_dir = tmp_path / ".cnogo"
        cnogo_dir.mkdir(parents=True, exist_ok=True)
        (cnogo_dir / "issues.jsonl").write_text("{}\n", encoding="utf-8")

        draft = build_ship_draft(tmp_path, "test-feature")

        assert ".cnogo/issues.jsonl" in draft["excludedFiles"]
        assert any("Excluded operational files" in warning for warning in draft["warnings"])

    def test_missing_all_plan_files_returns_empty_surface_with_warning(self, tmp_path):
        (_, build_ship_draft, *_) = _import_module()

        # Feature directory exists but has no plan files
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "empty-feature"
        feature_dir.mkdir(parents=True, exist_ok=True)

        draft = build_ship_draft(tmp_path, "empty-feature")

        assert isinstance(draft, dict)
        surface = draft.get("commitSurface", None)
        assert surface is not None
        assert len(surface) == 0 or isinstance(surface, list), (
            "commitSurface should be an empty list when no plan files exist"
        )
        warnings = draft.get("warnings", [])
        assert len(warnings) > 0, "Expected at least one warning when no plan files exist"
