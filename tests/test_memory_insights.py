"""Tests for derived-memory observations, contradictions, and cards."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory import create, init, sync_feature_memory, sync_work_order  # noqa: E402
from scripts.memory.context import checkpoint, prime  # noqa: E402
from scripts.memory.runtime import conn as memory_conn  # noqa: E402
from scripts.memory.storage import list_cards, list_contradictions, list_observations  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _seed_feature(root: Path) -> None:
    _write_json(
        root / "docs" / "planning" / "WORKFLOW.json",
        {
            "version": 1,
            "repoShape": "single",
            "profiles": {"default": "feature-delivery", "catalogPath": ".cnogo/profiles", "allowPlanOverride": True},
            "dispatcher": {"enabled": True, "defaultWipLimit": 2, "overlapPolicy": "allow", "autonomy": "high"},
        },
    )
    _write_json(
        root / "docs" / "planning" / "work" / "ideas" / "demo-shape" / "SHAPE.json",
        {
            "schemaVersion": 1,
            "initiative": "Demo Shape",
            "slug": "demo-shape",
            "problem": "Derived memory test.",
            "constraints": [],
            "globalDecisions": [],
            "researchRefs": [],
            "openQuestions": [],
            "candidateFeatures": [
                {
                    "slug": "demo",
                    "displayName": "Demo",
                    "userOutcome": "Outcome",
                    "scopeSummary": "Scope",
                    "dependencies": [],
                    "risks": ["Schema churn"],
                    "priority": 1,
                    "status": "ready",
                    "readinessReason": "Ready",
                    "handoffSummary": "Ready for the line.",
                }
            ],
            "recommendedSequence": ["demo"],
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )
    _write_json(
        root / "docs" / "planning" / "work" / "features" / "demo" / "FEATURE.json",
        {
            "schemaVersion": 1,
            "feature": "demo",
            "displayName": "Demo",
            "userOutcome": "Outcome",
            "scopeSummary": "Scope",
            "dependencies": [],
            "risks": ["Schema churn"],
            "priority": 1,
            "status": "ready",
            "readinessReason": "Ready",
            "handoffSummary": "Ready for the line.",
            "parentShape": {
                "path": "docs/planning/work/ideas/demo-shape/SHAPE.json",
                "timestamp": "2026-03-21T12:00:00Z",
                "schemaVersion": 1,
            },
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )
    _write_json(
        root / "docs" / "planning" / "work" / "features" / "demo" / "CONTEXT.json",
        {
            "schemaVersion": 3,
            "feature": "demo",
            "displayName": "Demo",
            "decisions": [
                {
                    "area": "storage",
                    "decision": "Use SQLite for local-first state.",
                    "rationale": "Offline-first by default.",
                }
            ],
            "constraints": ["No hosted service dependency."],
            "openQuestions": [],
            "relatedCode": ["app/demo.py"],
            "parentShape": {
                "path": "docs/planning/work/ideas/demo-shape/SHAPE.json",
                "timestamp": "2026-03-21T12:00:00Z",
                "schemaVersion": 1,
            },
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )
    _write_json(
        root / "docs" / "planning" / "work" / "features" / "demo" / "REVIEW.json",
        {
            "schemaVersion": 4,
            "feature": "demo",
            "verdict": "fail",
            "timestamp": "2026-03-21T12:05:00Z",
        },
    )


def test_sync_feature_memory_persists_observations_contradictions_and_cards(tmp_path):
    init(tmp_path)
    _seed_feature(tmp_path)
    create("Demo epic", issue_type="epic", feature_slug="demo", root=tmp_path)

    result = sync_feature_memory(
        "demo",
        root=tmp_path,
        trigger="test",
        work_order={
            "workOrderId": "demo",
            "feature": "demo",
            "status": "completed",
            "currentPhase": "ship",
            "attentionSummary": {"itemCount": 1, "highestSeverity": "fail"},
            "reviewSummary": {"status": "completed", "finalVerdict": "fail"},
        },
        run={
            "run_id": "demo-1",
            "review_readiness": {"planVerifyPassed": False},
        },
    )

    assert result["observations"] >= 5
    assert result["contradictions"] >= 2

    conn = memory_conn(tmp_path)
    try:
        observations = list_observations(conn, feature_slug="demo", statuses={"active"}, limit=20)
        assert {item["kind"] for item in observations} >= {
            "status_claim",
            "decision",
            "assumption",
            "risk",
            "handoff",
            "review_finding",
            "verification",
        }

        contradictions = list_contradictions(conn, feature_slug="demo", status="open", limit=10)
        contradiction_kinds = {item["kind"] for item in contradictions}
        assert "review_failed_but_progressed" in contradiction_kinds
        assert "completed_but_blocked" in contradiction_kinds

        cards = list_cards(conn, limit=10)
        scopes = {(item["scope"], item["cardKind"]) for item in cards}
        assert ("repo", "workflow") in scopes
        assert ("feature", "summary") in scopes
        assert ("initiative", "summary") in scopes
        assert ("user", "preferences") in scopes
    finally:
        conn.close()

    prime_text = prime(root=tmp_path)
    checkpoint_text = checkpoint(feature_slug="demo", root=tmp_path)
    assert "Repo Card" in prime_text
    assert "Feature Card (`demo`)" in prime_text
    assert "Open Contradictions" in prime_text
    assert "Feature Card:" in checkpoint_text
    assert "Contradictions:" in checkpoint_text


def test_decision_conflicts_are_detected_when_same_area_has_multiple_active_decisions(tmp_path):
    init(tmp_path)
    _seed_feature(tmp_path)
    context_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "CONTEXT.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["decisions"].append(
        {
            "area": "storage",
            "decision": "Move state to JSON files.",
            "rationale": "Alternative direction for portability.",
        }
    )
    context_path.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")

    result = sync_feature_memory(
        "demo",
        root=tmp_path,
        trigger="test",
        work_order={"workOrderId": "demo", "feature": "demo", "status": "queued", "currentPhase": "plan"},
    )

    assert result["contradictions"] >= 1
    conn = memory_conn(tmp_path)
    try:
        contradictions = list_contradictions(conn, feature_slug="demo", status="open", limit=10)
        contradiction_kinds = {item["kind"] for item in contradictions}
        assert "decision_conflict" in contradiction_kinds
    finally:
        conn.close()


def test_prime_uses_work_order_focus_when_no_issue_memory_exists(tmp_path):
    init(tmp_path)
    _seed_feature(tmp_path)
    sync_work_order("demo", root=tmp_path)

    result = sync_feature_memory(
        "demo",
        root=tmp_path,
        trigger="test",
        work_order={"workOrderId": "demo", "feature": "demo", "status": "queued", "currentPhase": "plan"},
    )
    assert result["cards"] >= 1

    prime_text = prime(root=tmp_path)
    assert "Feature Card (`demo`)" in prime_text
