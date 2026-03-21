"""Tests for initiative rollup orchestration helpers.

The module under test (initiative_rollup.py) is written by a teammate in
parallel. These tests may fail with ImportError until that module lands.
They document the expected API contract precisely so both sides can merge
cleanly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# conftest.py adds .cnogo to sys.path; import lazily so ImportError is
# surfaced per test rather than at collection time.
def _import_module():
    from scripts.workflow.orchestration.initiative_rollup import (  # noqa: E402
        build_initiative_rollup,
        list_initiatives,
        _derive_feature_status,
        _review_verdict,
        _collect_shape_feedback,
        _compute_next_initiative_action,
    )
    return (
        build_initiative_rollup,
        list_initiatives,
        _derive_feature_status,
        _review_verdict,
        _collect_shape_feedback,
        _compute_next_initiative_action,
    )


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

TIMESTAMP = "2026-03-21T12:00:00Z"


def _write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _shape_json(
    slug: str = "test-initiative",
    initiative: str = "Test Initiative",
    candidates: list[dict] | None = None,
    recommended_sequence: list[str] | None = None,
) -> dict:
    if candidates is None:
        candidates = [
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "not ready",
                "handoffSummary": "handoff",
            }
        ]
    if recommended_sequence is None:
        recommended_sequence = [c["slug"] for c in candidates]
    return {
        "schemaVersion": 1,
        "initiative": initiative,
        "slug": slug,
        "problem": "test problem",
        "constraints": [],
        "globalDecisions": [],
        "researchRefs": [],
        "openQuestions": [],
        "candidateFeatures": candidates,
        "recommendedSequence": recommended_sequence,
        "timestamp": TIMESTAMP,
    }


def _work_order_json(
    feature: str = "feature-a",
    status: str = "implementing",
    review_verdict: str = "pending",
    ship_status: str = "pending",
) -> dict:
    return {
        "schemaVersion": 1,
        "workOrderId": feature,
        "feature": feature,
        "status": status,
        "reviewSummary": {"status": "pending", "verdict": review_verdict},
        "shipSummary": {"status": ship_status},
        "createdAt": TIMESTAMP,
        "updatedAt": TIMESTAMP,
    }


def _context_json(
    feature: str = "feature-a",
    shape_feedback: list | None = None,
) -> dict:
    return {
        "schemaVersion": 3,
        "feature": feature,
        "displayName": "Feature A",
        "decisions": [],
        "constraints": [],
        "openQuestions": [],
        "relatedCode": [],
        "shapeFeedback": shape_feedback or [],
        "timestamp": TIMESTAMP,
    }


def _make_shape(tmp_path: Path, slug: str = "test-initiative", **kwargs) -> Path:
    shape_path = tmp_path / "docs" / "planning" / "work" / "ideas" / slug / "SHAPE.json"
    _write_json(shape_path, _shape_json(slug=slug, **kwargs))
    return shape_path


def _make_feature_stub(tmp_path: Path, feature: str) -> Path:
    p = tmp_path / "docs" / "planning" / "work" / "features" / feature / "FEATURE.json"
    _write_json(p, {"schemaVersion": 1, "feature": feature})
    return p


def _make_context(tmp_path: Path, feature: str, shape_feedback: list | None = None) -> Path:
    p = tmp_path / "docs" / "planning" / "work" / "features" / feature / "CONTEXT.json"
    _write_json(p, _context_json(feature=feature, shape_feedback=shape_feedback))
    return p


def _make_plan(tmp_path: Path, feature: str, plan_number: str = "01") -> Path:
    p = (
        tmp_path
        / "docs"
        / "planning"
        / "work"
        / "features"
        / feature
        / f"{plan_number}-PLAN.json"
    )
    _write_json(p, {"schemaVersion": 1, "feature": feature, "planNumber": plan_number})
    return p


def _make_work_order(tmp_path: Path, feature: str, **kwargs) -> Path:
    p = tmp_path / ".cnogo" / "work-orders" / f"{feature}.json"
    _write_json(p, _work_order_json(feature=feature, **kwargs))
    return p


# ---------------------------------------------------------------------------
# Status mapping tests  (D6)
# ---------------------------------------------------------------------------


class TestDeriveFeatureStatus:
    """Tests for _derive_feature_status(root, slug, shape_candidate_status)."""

    def test_no_feature_json_returns_shape_candidate_status_draft(self, tmp_path):
        """D6: No FEATURE.json stub → shape candidate status (draft)."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "draft"

    def test_no_feature_json_returns_shape_candidate_status_parked(self, tmp_path):
        """D6: No FEATURE.json and candidate status parked → parked."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        status = _derive_feature_status(tmp_path, "feature-a", "parked")
        assert status == "parked"

    def test_feature_json_only_returns_discuss_ready(self, tmp_path):
        """D6: FEATURE.json exists → discuss-ready."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "discuss-ready"

    def test_context_json_returns_discussing(self, tmp_path):
        """D6: CONTEXT.json exists → discussing."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_context(tmp_path, "feature-a")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "discussing"

    def test_plan_but_no_work_order_returns_planned(self, tmp_path):
        """D6: PLAN exists, no Work Order → planned."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_context(tmp_path, "feature-a")
        _make_plan(tmp_path, "feature-a")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "planned"

    def test_work_order_implementing_returns_implementing(self, tmp_path):
        """D6: Work Order status implementing → implementing."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_context(tmp_path, "feature-a")
        _make_plan(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="implementing")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "implementing"

    def test_work_order_reviewing_returns_reviewing(self, tmp_path):
        """D6: Work Order status reviewing → reviewing."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="reviewing")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "reviewing"

    def test_work_order_completed_returns_completed(self, tmp_path):
        """D6: Work Order status completed → completed."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="completed")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "completed"

    def test_work_order_cancelled_returns_cancelled_not_parked(self, tmp_path):
        """D2: cancelled Work Order stays cancelled, NOT remapped to parked."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="cancelled")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "cancelled"
        assert status != "parked"

    def test_work_order_blocked_returns_blocked(self, tmp_path):
        """D6: Work Order status blocked → blocked."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        _make_feature_stub(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="blocked")
        status = _derive_feature_status(tmp_path, "feature-a", "draft")
        assert status == "blocked"

    def test_shape_candidate_status_parked_with_no_feature_json(self, tmp_path):
        """D6: No FEATURE.json and shape candidate parked → parked."""
        (_, _, _derive_feature_status, _, _, _) = _import_module()
        status = _derive_feature_status(tmp_path, "feature-a", "parked")
        assert status == "parked"


# ---------------------------------------------------------------------------
# Review verdict tests  (D5)
# ---------------------------------------------------------------------------


class TestReviewVerdict:
    """Tests for _review_verdict(wo_data: dict) -> str."""

    def test_no_review_summary_returns_pending(self, tmp_path):
        """D5: Work Order with no review summary → pending."""
        (_, _, _, _review_verdict, _, _) = _import_module()
        wo_data = _work_order_json("feature-a", status="implementing")
        wo_data.pop("reviewSummary", None)
        assert _review_verdict(wo_data) == "pending"

    def test_review_verdict_pass(self, tmp_path):
        """D5: review verdict pass → pass."""
        (_, _, _, _review_verdict, _, _) = _import_module()
        wo_data = _work_order_json("feature-a", review_verdict="pass")
        assert _review_verdict(wo_data) == "pass"

    def test_review_verdict_fail(self, tmp_path):
        """D5: review verdict fail → fail."""
        (_, _, _, _review_verdict, _, _) = _import_module()
        wo_data = _work_order_json("feature-a", review_verdict="fail")
        assert _review_verdict(wo_data) == "fail"

    def test_review_verdict_warn(self, tmp_path):
        """D5: review verdict warn → warn."""
        (_, _, _, _review_verdict, _, _) = _import_module()
        wo_data = _work_order_json("feature-a", review_verdict="warn")
        assert _review_verdict(wo_data) == "warn"

    def test_empty_review_summary_returns_pending(self, tmp_path):
        """D5: empty reviewSummary dict → pending."""
        (_, _, _, _review_verdict, _, _) = _import_module()
        wo_data = _work_order_json("feature-a")
        wo_data["reviewSummary"] = {}
        assert _review_verdict(wo_data) == "pending"


# ---------------------------------------------------------------------------
# shapeFeedback collection tests
# ---------------------------------------------------------------------------


class TestCollectShapeFeedback:
    """Tests for _collect_shape_feedback(root, candidate_slugs) -> list[dict]."""

    def test_no_context_files_returns_empty_list(self, tmp_path):
        """No CONTEXT.json files → empty list."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        result = _collect_shape_feedback(tmp_path, ["feature-a"])
        assert result == []

    def test_context_with_string_feedback_is_collected(self, tmp_path):
        """CONTEXT.json with string feedback entries are collected."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        _make_context(tmp_path, "feature-a", shape_feedback=["Simple string feedback"])
        result = _collect_shape_feedback(tmp_path, ["feature-a"])
        assert len(result) >= 1
        # At least one entry should contain the feedback text
        texts = [str(r) for r in result]
        assert any("Simple string feedback" in t for t in texts)

    def test_context_with_object_feedback_is_collected(self, tmp_path):
        """CONTEXT.json with object feedback entries preserve full structure."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        feedback_obj = {
            "summary": "Object feedback",
            "suggestedAction": "do something",
            "affectedFeatures": ["feature-b"],
        }
        _make_context(tmp_path, "feature-a", shape_feedback=[feedback_obj])
        result = _collect_shape_feedback(tmp_path, ["feature-a"])
        assert len(result) >= 1
        # The object feedback should be present in some form
        result_str = json.dumps(result)
        assert "Object feedback" in result_str

    def test_multiple_features_feedback_is_aggregated(self, tmp_path):
        """Multiple features with shapeFeedback all appear in the result."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        _make_context(tmp_path, "feature-a", shape_feedback=["Feedback from A"])
        _make_context(tmp_path, "feature-b", shape_feedback=["Feedback from B"])
        result = _collect_shape_feedback(tmp_path, ["feature-a", "feature-b"])
        result_str = json.dumps(result)
        assert "Feedback from A" in result_str
        assert "Feedback from B" in result_str

    def test_empty_feedback_list_yields_no_entries(self, tmp_path):
        """CONTEXT.json with empty shapeFeedback list → no entries added."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        _make_context(tmp_path, "feature-a", shape_feedback=[])
        result = _collect_shape_feedback(tmp_path, ["feature-a"])
        assert result == []

    def test_mixed_string_and_object_feedback_both_collected(self, tmp_path):
        """Mixed feedback types (string + object) are all collected."""
        (_, _, _, _, _collect_shape_feedback, _) = _import_module()
        _make_context(
            tmp_path,
            "feature-a",
            shape_feedback=[
                "Simple string feedback",
                {"summary": "Object feedback", "suggestedAction": "do something", "affectedFeatures": ["feature-b"]},
            ],
        )
        result = _collect_shape_feedback(tmp_path, ["feature-a"])
        result_str = json.dumps(result)
        assert "Simple string feedback" in result_str
        assert "Object feedback" in result_str


# ---------------------------------------------------------------------------
# Next action computation tests
# ---------------------------------------------------------------------------


class TestComputeNextInitiativeAction:
    """Tests for _compute_next_initiative_action(features_rollup, recommended_sequence)."""

    def _feature(self, slug: str, status: str) -> dict:
        return {"slug": slug, "status": status, "displayName": slug.replace("-", " ").title()}

    def test_all_completed_returns_complete_action(self, tmp_path):
        """All features completed → action kind is 'complete'."""
        (_, _, _, _, _, _compute_next_initiative_action) = _import_module()
        features = [
            self._feature("feature-a", "completed"),
            self._feature("feature-b", "completed"),
        ]
        action = _compute_next_initiative_action(features, ["feature-a", "feature-b"])
        assert action.get("kind") == "complete" or "complete" in str(action).lower()

    def test_some_blocked_returns_unblock_action(self, tmp_path):
        """Some features blocked → action kind is 'unblock' or similar."""
        (_, _, _, _, _, _compute_next_initiative_action) = _import_module()
        features = [
            self._feature("feature-a", "blocked"),
            self._feature("feature-b", "draft"),
        ]
        action = _compute_next_initiative_action(features, ["feature-a", "feature-b"])
        action_str = str(action).lower()
        assert "unblock" in action_str or action.get("kind") == "unblock"

    def test_next_in_sequence_is_draft_returns_shape_action(self, tmp_path):
        """Next feature in sequence is draft → action suggests shaping."""
        (_, _, _, _, _, _compute_next_initiative_action) = _import_module()
        features = [
            self._feature("feature-a", "completed"),
            self._feature("feature-b", "draft"),
        ]
        action = _compute_next_initiative_action(features, ["feature-a", "feature-b"])
        action_str = str(action).lower()
        assert "shape" in action_str or action.get("kind") == "shape"

    def test_next_in_sequence_is_discuss_ready_returns_discuss_action(self, tmp_path):
        """Next feature in sequence is discuss-ready → action suggests discussing."""
        (_, _, _, _, _, _compute_next_initiative_action) = _import_module()
        features = [
            self._feature("feature-a", "completed"),
            self._feature("feature-b", "discuss-ready"),
        ]
        action = _compute_next_initiative_action(features, ["feature-a", "feature-b"])
        action_str = str(action).lower()
        assert "discuss" in action_str or action.get("kind") == "discuss"

    def test_features_with_pending_feedback_mentions_count(self, tmp_path):
        """When pendingFeedback is provided, next action references feedback count."""
        (_, _, _, _, _, _compute_next_initiative_action) = _import_module()
        features = [
            self._feature("feature-a", "discussing"),
        ]
        pending_feedback = [
            {"feature": "feature-a", "summary": "feedback 1"},
            {"feature": "feature-a", "summary": "feedback 2"},
        ]
        action = _compute_next_initiative_action(
            features, ["feature-a"], pending_feedback=pending_feedback
        )
        # The action summary / metadata should mention there is pending feedback
        action_str = str(action).lower()
        assert "feedback" in action_str or action.get("pendingFeedbackCount", 0) >= 1


# ---------------------------------------------------------------------------
# build_initiative_rollup integration tests
# ---------------------------------------------------------------------------


class TestBuildInitiativeRollup:
    """End-to-end integration tests for build_initiative_rollup."""

    def test_returns_expected_keys(self, tmp_path):
        """Rollup dict contains the full set of expected top-level keys."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path)
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "error" not in result
        for key in ("initiative", "slug", "shapePath", "totalFeatures", "completedFeatures", "features", "timestamp"):
            assert key in result, f"missing key: {key}"

    def test_total_and_completed_features_count(self, tmp_path):
        """totalFeatures and completedFeatures are computed correctly."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        candidates = [
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "",
                "handoffSummary": "",
            },
            {
                "slug": "feature-b",
                "displayName": "Feature B",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "",
                "handoffSummary": "",
            },
        ]
        shape_path = _make_shape(tmp_path, candidates=candidates, recommended_sequence=["feature-a", "feature-b"])
        # Mark feature-b as completed via work order
        _make_feature_stub(tmp_path, "feature-b")
        _make_work_order(tmp_path, "feature-b", status="completed")
        result = build_initiative_rollup(tmp_path, shape_path)
        assert result["totalFeatures"] == 2
        assert result["completedFeatures"] == 1

    def test_mixed_feature_states_reflected_in_features_list(self, tmp_path):
        """Features list entries reflect actual artifact-derived status."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        candidates = [
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "",
                "handoffSummary": "",
            },
            {
                "slug": "feature-b",
                "displayName": "Feature B",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "",
                "handoffSummary": "",
            },
        ]
        shape_path = _make_shape(tmp_path, candidates=candidates, recommended_sequence=["feature-a", "feature-b"])
        _make_feature_stub(tmp_path, "feature-a")
        _make_work_order(tmp_path, "feature-a", status="implementing")
        result = build_initiative_rollup(tmp_path, shape_path)
        statuses = {f["slug"]: f["status"] for f in result["features"]}
        assert statuses.get("feature-a") == "implementing"
        assert statuses.get("feature-b") == "draft"

    def test_initiative_and_slug_match_shape(self, tmp_path):
        """initiative and slug fields match values from SHAPE.json."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(
            tmp_path, slug="my-initiative", initiative="My Initiative"
        )
        result = build_initiative_rollup(tmp_path, shape_path)
        assert result["initiative"] == "My Initiative"
        assert result["slug"] == "my-initiative"

    def test_pending_feedback_collected_from_context_files(self, tmp_path):
        """pendingFeedback is populated from CONTEXT.json shapeFeedback entries."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path)
        _make_feature_stub(tmp_path, "feature-a")
        _make_context(tmp_path, "feature-a", shape_feedback=["Important feedback item"])
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "error" not in result
        pending = result.get("pendingFeedback", [])
        assert isinstance(pending, list)
        feedback_str = json.dumps(pending)
        assert "Important feedback item" in feedback_str

    def test_next_action_is_present(self, tmp_path):
        """nextAction is always present in rollup result."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path)
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "nextAction" in result
        assert isinstance(result["nextAction"], dict)

    def test_timestamp_is_present_in_result(self, tmp_path):
        """timestamp key is present in rollup result."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path)
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "timestamp" in result
        assert result["timestamp"]  # non-empty


# ---------------------------------------------------------------------------
# list_initiatives tests
# ---------------------------------------------------------------------------


class TestListInitiatives:
    """Tests for list_initiatives(root) -> list[dict]."""

    def test_no_shape_files_returns_empty_list(self, tmp_path):
        """No SHAPE.json files → empty list."""
        (_, list_initiatives, _, _, _, _) = _import_module()
        result = list_initiatives(tmp_path)
        assert result == []

    def test_one_shape_file_returns_one_entry(self, tmp_path):
        """One SHAPE.json → returns list with one entry."""
        (_, list_initiatives, _, _, _, _) = _import_module()
        _make_shape(tmp_path, slug="initiative-alpha")
        result = list_initiatives(tmp_path)
        assert len(result) == 1
        assert result[0]["slug"] == "initiative-alpha"

    def test_multiple_shape_files_returns_all(self, tmp_path):
        """Multiple SHAPE.json files → all returned."""
        (_, list_initiatives, _, _, _, _) = _import_module()
        _make_shape(tmp_path, slug="initiative-alpha")
        # Second shape — different ideas subfolder
        shape2 = tmp_path / "docs" / "planning" / "work" / "ideas" / "initiative-beta" / "SHAPE.json"
        _write_json(
            shape2,
            _shape_json(slug="initiative-beta", initiative="Beta Initiative"),
        )
        result = list_initiatives(tmp_path)
        slugs = {e["slug"] for e in result}
        assert "initiative-alpha" in slugs
        assert "initiative-beta" in slugs

    def test_entry_has_required_keys(self, tmp_path):
        """Each list entry has slug, initiative, shapePath, candidateCount."""
        (_, list_initiatives, _, _, _, _) = _import_module()
        _make_shape(tmp_path, slug="initiative-alpha")
        result = list_initiatives(tmp_path)
        entry = result[0]
        for key in ("slug", "initiative", "shapePath", "candidateCount"):
            assert key in entry, f"missing key: {key}"

    def test_candidate_count_matches_shape(self, tmp_path):
        """candidateCount reflects number of candidateFeatures in SHAPE.json."""
        (_, list_initiatives, _, _, _, _) = _import_module()
        candidates = [
            {
                "slug": f"feature-{i}",
                "displayName": f"Feature {i}",
                "userOutcome": "outcome",
                "scopeSummary": "scope",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "",
                "handoffSummary": "",
            }
            for i in range(3)
        ]
        _make_shape(tmp_path, slug="initiative-alpha", candidates=candidates)
        result = list_initiatives(tmp_path)
        assert result[0]["candidateCount"] == 3


# ---------------------------------------------------------------------------
# Error path tests
# ---------------------------------------------------------------------------


class TestErrorPaths:
    """Tests for error handling in build_initiative_rollup and related helpers."""

    def test_corrupt_shape_json_returns_error_dict(self, tmp_path):
        """Corrupt SHAPE.json (invalid JSON) → returns dict with 'error' key."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = tmp_path / "docs" / "planning" / "work" / "ideas" / "broken" / "SHAPE.json"
        shape_path.parent.mkdir(parents=True, exist_ok=True)
        shape_path.write_text("NOT VALID JSON {{{", encoding="utf-8")
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "error" in result

    def test_missing_work_order_directory_defaults_to_artifact_based_status(self, tmp_path):
        """Missing Work Order directory → status derived from artifacts only."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path)
        # FEATURE.json exists but no work order dir / file
        _make_feature_stub(tmp_path, "feature-a")
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "error" not in result
        statuses = {f["slug"]: f["status"] for f in result["features"]}
        # With only FEATURE.json and no work order, expect discuss-ready
        assert statuses.get("feature-a") == "discuss-ready"

    def test_missing_shape_file_returns_error_dict(self, tmp_path):
        """Non-existent SHAPE.json path → returns dict with 'error' key."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        missing_path = tmp_path / "docs" / "planning" / "work" / "ideas" / "ghost" / "SHAPE.json"
        result = build_initiative_rollup(tmp_path, missing_path)
        assert "error" in result

    def test_shape_json_with_empty_candidates_list(self, tmp_path):
        """SHAPE.json with empty candidateFeatures → rollup with zero features."""
        (build_initiative_rollup, _, _, _, _, _) = _import_module()
        shape_path = _make_shape(tmp_path, candidates=[], recommended_sequence=[])
        result = build_initiative_rollup(tmp_path, shape_path)
        assert "error" not in result
        assert result["totalFeatures"] == 0
        assert result["completedFeatures"] == 0
        assert result["features"] == []
