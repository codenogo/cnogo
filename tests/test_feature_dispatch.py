"""Tests for ready-feature queueing, lanes, and dispatch."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory import (  # noqa: E402
    dispatch_ready_features,
    ensure_delivery_run,
    init,
    list_feature_lanes,
    load_work_order,
    sync_all_work_orders,
    sync_shape_feedback,
    sync_work_order,
    watch_delivery_runs,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _workflow(root: Path, *, overlap_policy: str = "allow", lease_timeout_minutes: int = 45, wip_limit: int = 2) -> None:
    _write_json(
        root / "docs" / "planning" / "WORKFLOW.json",
        {
            "version": 1,
            "repoShape": "single",
            "profiles": {"default": "feature-delivery", "catalogPath": ".cnogo/profiles", "allowPlanOverride": True},
            "dispatcher": {
                "enabled": True,
                "defaultWipLimit": wip_limit,
                "overlapPolicy": overlap_policy,
                "autonomy": "high",
                "leaseTimeoutMinutes": lease_timeout_minutes,
            },
        },
    )


def _git_init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True, text=True)
    (root / "README.md").write_text("demo\n", encoding="utf-8")
    (root / ".cnogo" / "scripts").mkdir(parents=True, exist_ok=True)
    (root / ".cnogo" / "scripts" / "workflow_memory.py").write_text("print('demo')\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", ".cnogo/scripts/workflow_memory.py"], cwd=root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, text=True)


def _shape(root: Path, *, features: list[dict]) -> None:
    _write_json(
        root / "docs" / "planning" / "work" / "ideas" / "demo-shape" / "SHAPE.json",
        {
            "schemaVersion": 1,
            "initiative": "Demo Shape",
            "slug": "demo-shape",
            "problem": "Test the queue.",
            "constraints": [],
            "globalDecisions": [],
            "researchRefs": [],
            "openQuestions": [],
            "candidateFeatures": features,
            "recommendedSequence": [feature["slug"] for feature in features],
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )


def _ready_feature(root: Path, slug: str, *, priority: int, related_code: list[str] | None = None) -> None:
    feature_dir = root / "docs" / "planning" / "work" / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        feature_dir / "FEATURE.json",
        {
            "schemaVersion": 1,
            "feature": slug,
            "displayName": slug.replace("-", " ").title(),
            "userOutcome": "Outcome",
            "scopeSummary": "Scope",
            "dependencies": [],
            "risks": [],
            "priority": priority,
            "status": "ready",
            "readinessReason": "Ready now",
            "handoffSummary": "Queued for planning.",
            "parentShape": {
                "path": "docs/planning/work/ideas/demo-shape/SHAPE.json",
                "timestamp": "2026-03-21T12:00:00Z",
                "schemaVersion": 1,
            },
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )
    _write_json(
        feature_dir / "CONTEXT.json",
        {
            "schemaVersion": 3,
            "feature": slug,
            "displayName": slug.replace("-", " ").title(),
            "decisions": [],
            "constraints": [],
            "openQuestions": [],
            "relatedCode": related_code or [],
            "parentShape": {
                "path": "docs/planning/work/ideas/demo-shape/SHAPE.json",
                "timestamp": "2026-03-21T12:00:00Z",
                "schemaVersion": 1,
            },
            "timestamp": "2026-03-21T12:00:00Z",
        },
    )


def _lane_json(root: Path, slug: str) -> Path:
    return root / ".cnogo" / "lanes" / f"{slug}.json"


def test_ready_features_sync_into_queued_work_orders_and_dispatch_into_lanes(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            },
            {
                "slug": "feature-b",
                "displayName": "Feature B",
                "userOutcome": "B",
                "scopeSummary": "B scope",
                "dependencies": [],
                "risks": [],
                "priority": 2,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue B",
            },
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _ready_feature(tmp_path, "feature-b", priority=2, related_code=["app/b.py"])

    orders = sync_all_work_orders(root=tmp_path)
    assert [order.feature for order in orders[:2]] == ["feature-a", "feature-b"]
    assert [order.status for order in orders[:2]] == ["queued", "queued"]
    assert [order.queue_position for order in orders[:2]] == [1, 2]

    payload = dispatch_ready_features(root=tmp_path)
    assert [entry["feature"] for entry in payload["leased"]] == ["feature-a", "feature-b"]
    assert [entry["feature"] for entry in payload["autoPlanned"]] == ["feature-a", "feature-b"]

    lanes = list_feature_lanes(root=tmp_path)
    assert len(lanes) == 2
    assert {lane.status for lane in lanes} == {"implementing"}

    updated_orders = sync_all_work_orders(root=tmp_path)
    by_feature = {order.feature: order for order in updated_orders}
    assert by_feature["feature-a"].status == "implementing"
    assert by_feature["feature-a"].lane["status"] == "implementing"
    assert by_feature["feature-a"].queue_position == 0
    plan_roots = {lane.feature: Path(lane.worktree_path) for lane in lanes}
    assert (plan_roots["feature-a"] / "docs" / "planning" / "work" / "features" / "feature-a" / "01-PLAN.json").exists()
    assert (plan_roots["feature-b"] / "docs" / "planning" / "work" / "features" / "feature-b" / "01-PLAN.json").exists()


def test_dispatch_respects_overlap_block_policy(tmp_path):
    init(tmp_path)
    _workflow(tmp_path, overlap_policy="block")
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            },
            {
                "slug": "feature-b",
                "displayName": "Feature B",
                "userOutcome": "B",
                "scopeSummary": "B scope",
                "dependencies": [],
                "risks": [],
                "priority": 1,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue B",
            },
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["shared/hotspot.py"])
    _ready_feature(tmp_path, "feature-b", priority=1, related_code=["shared/hotspot.py"])

    sync_all_work_orders(root=tmp_path)
    payload = dispatch_ready_features(root=tmp_path)

    assert [entry["feature"] for entry in payload["leased"]] == ["feature-a"]
    assert payload["skipped"][0]["feature"] == "feature-b"
    assert payload["skipped"][0]["reason"] == "overlap_blocked"


def test_dispatch_writes_control_plane_marker_for_git_worktrees(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    init(repo)
    _git_init_repo(repo)
    _workflow(repo)
    _shape(
        repo,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(repo, "feature-a", priority=0, related_code=["app/a.py"])

    sync_all_work_orders(root=repo)
    payload = dispatch_ready_features(root=repo)

    assert [entry["feature"] for entry in payload["leased"]] == ["feature-a"]
    assert [entry["feature"] for entry in payload["autoPlanned"]] == ["feature-a"]
    lane = list_feature_lanes(root=repo)[0]
    worktree_root = Path(lane.worktree_path)
    marker = worktree_root / ".cnogo" / "control-plane-root"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip() == str(repo.resolve())
    assert (worktree_root / ".cnogo" / "scripts" / "workflow_memory.py").exists()
    assert (worktree_root / "docs" / "planning" / "work" / "features" / "feature-a" / "01-PLAN.json").exists()
    assert not (repo / "docs" / "planning" / "work" / "features" / "feature-a" / "01-PLAN.json").exists()


def test_sync_work_order_records_memory_sync_errors_instead_of_swallowing(tmp_path, monkeypatch):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])

    def _boom(*_args, **_kwargs):
        raise RuntimeError("sync exploded")

    monkeypatch.setattr("scripts.memory.insights.sync_feature_memory", _boom)

    order = sync_work_order("feature-a", root=tmp_path)
    persisted = load_work_order("feature-a", root=tmp_path)

    assert order.memory_sync["status"] == "error"
    assert "sync exploded" in order.memory_sync["error"]
    assert persisted is not None
    assert persisted.memory_sync["status"] == "error"


def test_feedback_sync_collects_attention_and_contradictions(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "feature-a"
    (feature_dir / "REVIEW.json").write_text(
        json.dumps({"schemaVersion": 1, "feature": "feature-a", "verdict": "fail"}, indent=2) + "\n",
        encoding="utf-8",
    )
    sync_work_order("feature-a", root=tmp_path)

    attention_dir = tmp_path / ".cnogo" / "watch"
    attention_dir.mkdir(parents=True, exist_ok=True)
    (attention_dir / "attention.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "feature": "feature-a",
                        "severity": "warn",
                        "message": "Patrol noticed stalled review follow-up.",
                        "nextAction": "resume",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = sync_shape_feedback(root=tmp_path)

    assert payload["itemsAdded"] >= 2
    shape = json.loads(
        (tmp_path / "docs" / "planning" / "work" / "ideas" / "demo-shape" / "SHAPE.json").read_text(encoding="utf-8")
    )
    summaries = {item["summary"] for item in shape["feedbackInbox"] if isinstance(item, dict)}
    assert "Review verdict for feature-a is fail." in summaries
    assert "Patrol noticed stalled review follow-up." in summaries


def test_dispatch_reclaims_stale_lane_before_leasing_new_feature(tmp_path):
    init(tmp_path)
    _workflow(tmp_path, lease_timeout_minutes=1, wip_limit=1)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            },
            {
                "slug": "feature-b",
                "displayName": "Feature B",
                "userOutcome": "B",
                "scopeSummary": "B scope",
                "dependencies": [],
                "risks": [],
                "priority": 1,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue B",
            },
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _ready_feature(tmp_path, "feature-b", priority=1, related_code=["app/b.py"])

    sync_all_work_orders(root=tmp_path)
    first = dispatch_ready_features(root=tmp_path)
    assert [entry["feature"] for entry in first["leased"]] == ["feature-a"]

    lane_path = _lane_json(tmp_path, "feature-a")
    lane_payload = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_payload["currentRunId"] = ""
    lane_payload["currentPlanNumber"] = ""
    lane_payload["status"] = "leased"
    lane_payload["heartbeatAt"] = "2026-03-20T10:00:00Z"
    lane_payload["leaseExpiresAt"] = "2026-03-20T10:01:00Z"
    lane_path.write_text(json.dumps(lane_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    second = dispatch_ready_features(feature_slug="feature-b", root=tmp_path)

    assert [entry["feature"] for entry in second["reclaimed"]] == ["feature-a"]
    assert [entry["feature"] for entry in second["leased"]] == ["feature-b"]
    assert second["activeLaneCount"] == 1


def test_work_order_includes_lane_health_and_automation_state(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])

    sync_all_work_orders(root=tmp_path)
    dispatch_ready_features(root=tmp_path)
    order = sync_work_order("feature-a", root=tmp_path)

    assert order.status == "implementing"
    assert order.automation_state["state"] == "waiting_for_execution"
    assert order.lane["health"]["stale"] is False
    assert order.automation_state["laneHealth"]["stale"] is False


def test_delivery_run_sync_updates_lane_with_run_identity(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    sync_all_work_orders(root=tmp_path)
    dispatch_ready_features(root=tmp_path)

    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "feature-a"
    plan_path = feature_dir / "01-PLAN.json"
    _write_json(plan_path, {"schemaVersion": 1, "feature": "feature-a", "planNumber": "01"})
    run = ensure_delivery_run(
        feature="feature-a",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[
            {
                "plan_task_index": 0,
                "title": "Implement feature A",
                "file_scope": {"paths": ["app/a.py"], "forbidden": []},
                "commands": {"verify": ["pytest -q"], "package_verify": []},
                "blockedBy": [],
            }
        ],
        mode="serial",
        root=tmp_path,
    )

    lane = list_feature_lanes(root=tmp_path)[0]
    assert lane.current_run_id == run.run_id
    assert lane.current_plan_number == "01"
    assert lane.status == "implementing"
    assert lane.heartbeat_at


def test_watch_reports_stale_feature_lane_without_run(tmp_path):
    init(tmp_path)
    _workflow(tmp_path, lease_timeout_minutes=1)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    sync_all_work_orders(root=tmp_path)
    dispatch_ready_features(root=tmp_path)

    lane_path = _lane_json(tmp_path, "feature-a")
    lane_payload = json.loads(lane_path.read_text(encoding="utf-8"))
    lane_payload["currentRunId"] = ""
    lane_payload["currentPlanNumber"] = ""
    lane_payload["status"] = "leased"
    lane_payload["heartbeatAt"] = "2026-03-20T10:00:00Z"
    lane_payload["leaseExpiresAt"] = "2026-03-20T10:01:00Z"
    lane_path.write_text(json.dumps(lane_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = watch_delivery_runs(root=tmp_path)
    kinds = {item["kind"] for item in report["findings"]}
    assert "stale_feature_lane" in kinds


def _setup_lane_with_review_ready_run(root: Path, slug: str) -> None:
    """Set up a lane with a delivery run where review_readiness=ready, review pending."""
    from scripts.workflow.orchestration.delivery_run import (
        DeliveryRun,
        save_delivery_run,
    )
    from scripts.workflow.orchestration.review import ensure_run_review_state, sync_review_state
    from scripts.workflow.orchestration.integration import ensure_run_coordination_state
    from scripts.workflow.orchestration.ship import ensure_run_ship_state, sync_ship_state

    # First dispatch to create lane + plan.
    sync_all_work_orders(root=root)
    dispatch_ready_features(root=root)

    # Get the latest run and manipulate it to be review-ready.
    from scripts.workflow.orchestration.delivery_run import latest_delivery_run
    run = latest_delivery_run(root, slug)
    if run is None:
        run = DeliveryRun(
            run_id=f"run-{slug}-001",
            feature=slug,
            plan_number="01",
            plan_path=str(root / "docs" / "planning" / "work" / "features" / slug / "01-PLAN.json"),
            mode="serial",
            status="implementing",
            tasks=[],
        )
    # Set review readiness to ready.
    run.review_readiness = {
        "status": "ready",
        "planVerifyPassed": True,
        "planVerifyCommands": ["pytest -q"],
        "updatedAt": "2026-03-22T10:00:00Z",
    }
    run.integration = {"status": "merged", "updatedAt": "2026-03-22T10:00:00Z"}
    ensure_run_review_state(run)
    sync_review_state(run)
    ensure_run_ship_state(run)
    sync_ship_state(run)
    run.status = "implementing"
    save_delivery_run(run, root)

    # Update lane to implementing status.
    from scripts.workflow.orchestration.lane import heartbeat_feature_lane
    heartbeat_feature_lane(root, slug, status="implementing", lease_owner="dispatcher")
    # Overwrite planVerify with a command that succeeds in the test tmp_path,
    # since pytest from tmp_path exits non-zero (no test files).
    # The plan is in the feature worktree, not the main root.
    plan_path = Path(run.plan_path) if run else None
    if plan_path and plan_path.exists():
        plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
        plan_data["planVerify"] = ["true"]
        plan_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    sync_work_order(slug, root=root)


def test_dispatch_auto_reviews_lane_when_profile_allows(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _setup_lane_with_review_ready_run(tmp_path, "feature-a")

    # Dispatch again — should auto-review.
    payload = dispatch_ready_features(root=tmp_path)
    assert len(payload["autoReviewed"]) == 1
    assert payload["autoReviewed"][0]["feature"] == "feature-a"
    assert payload["autoReviewed"][0]["finalVerdict"] == "pass"

    # Verify review state on the work order.
    order = sync_work_order("feature-a", root=tmp_path)
    assert order.review_summary["finalVerdict"] == "pass"
    assert order.review_summary["status"] == "completed"


def test_dispatch_skips_auto_review_when_profile_disallows(tmp_path, monkeypatch):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _setup_lane_with_review_ready_run(tmp_path, "feature-a")

    # Patch profile_auto_review to return False at the source module.
    monkeypatch.setattr(
        "scripts.workflow.shared.profiles.profile_auto_review",
        lambda profile: False,
    )

    payload = dispatch_ready_features(root=tmp_path)
    assert len(payload["autoReviewed"]) == 0
    assert len(payload["autoReviewSkipped"]) == 1
    assert payload["autoReviewSkipped"][0]["reason"] == "profile_auto_review_disabled"


def _setup_lane_with_ship_ready_run(root: Path, slug: str) -> None:
    """Set up a lane with a delivery run where ship.status=ready (review completed, pass verdict)."""
    from scripts.workflow.orchestration.delivery_run import (
        DeliveryRun,
        latest_delivery_run,
        save_delivery_run,
    )
    from scripts.workflow.orchestration.review import (
        ensure_run_review_state,
        set_review_stage,
        set_review_verdict,
        start_review,
        sync_review_state,
    )
    from scripts.workflow.orchestration.ship import ensure_run_ship_state, sync_ship_state
    from scripts.workflow.orchestration.integration import ensure_run_coordination_state
    from scripts.workflow.orchestration.lane import heartbeat_feature_lane

    # First dispatch to create lane + plan.
    sync_all_work_orders(root=root)
    dispatch_ready_features(root=root)

    # Get the latest run and set it to review-completed with pass verdict.
    run = latest_delivery_run(root, slug)
    if run is None:
        raise RuntimeError(f"No delivery run found for {slug}")
    run.review_readiness = {
        "status": "ready",
        "planVerifyPassed": True,
        "planVerifyCommands": ["pytest -q"],
        "updatedAt": "2026-03-22T10:00:00Z",
    }
    run.integration = {"status": "merged", "updatedAt": "2026-03-22T10:00:00Z"}
    ensure_run_review_state(run)
    start_review(run, automated_verdict="pass")
    for stage_name in ("spec-compliance", "code-quality"):
        set_review_stage(run, stage=stage_name, status="pass", findings=[], evidence=["pass"])
    set_review_verdict(run, verdict="pass")
    ensure_run_ship_state(run)
    sync_ship_state(run)
    run.status = "implementing"
    save_delivery_run(run, root)
    heartbeat_feature_lane(root, slug, status="reviewing", lease_owner="dispatcher")
    sync_work_order(slug, root=root)


def test_dispatch_auto_starts_ship_when_profile_allows(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _setup_lane_with_ship_ready_run(tmp_path, "feature-a")

    # Dispatch again — should auto-ship.
    payload = dispatch_ready_features(root=tmp_path)
    assert len(payload["autoShipStarted"]) == 1
    assert payload["autoShipStarted"][0]["feature"] == "feature-a"
    assert payload["autoShipStarted"][0]["shipStatus"] == "in_progress"


def test_dispatch_skips_auto_ship_when_profile_disallows(tmp_path, monkeypatch):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    _setup_lane_with_ship_ready_run(tmp_path, "feature-a")

    monkeypatch.setattr(
        "scripts.workflow.shared.profiles.profile_auto_ship",
        lambda profile: False,
    )

    payload = dispatch_ready_features(root=tmp_path)
    assert len(payload["autoShipStarted"]) == 0
    assert len(payload["autoShipSkipped"]) == 1
    assert payload["autoShipSkipped"][0]["reason"] == "profile_auto_ship_disabled"


def test_work_order_automation_state_includes_profile_policy(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])
    sync_all_work_orders(root=tmp_path)
    dispatch_ready_features(root=tmp_path)
    order = sync_work_order("feature-a", root=tmp_path)

    config = order.automation_state["config"]
    assert "profilePolicy" in config
    assert "requiresTracking" in config["profilePolicy"]
    assert "requiresPullRequest" in config["profilePolicy"]
    assert isinstance(config["profilePolicy"]["requiresTracking"], bool)
    assert isinstance(config["profilePolicy"]["requiresPullRequest"], bool)


def test_watch_patrol_reports_post_ship_cleanup(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=["app/a.py"])

    # Set up a lane with a completed ship.
    from scripts.workflow.orchestration.delivery_run import (
        latest_delivery_run,
        save_delivery_run,
    )
    from scripts.workflow.orchestration.review import (
        ensure_run_review_state,
        set_review_stage,
        set_review_verdict,
        start_review,
    )
    from scripts.workflow.orchestration.ship import (
        complete_ship,
        ensure_run_ship_state,
        start_ship,
        sync_ship_state,
    )
    from scripts.workflow.orchestration.lane import heartbeat_feature_lane

    sync_all_work_orders(root=tmp_path)
    dispatch_ready_features(root=tmp_path)

    run = latest_delivery_run(tmp_path, "feature-a")
    assert run is not None
    # Set up review completed + ship completed.
    run.review_readiness = {"status": "ready", "planVerifyPassed": True, "updatedAt": "2026-03-22T10:00:00Z"}
    run.integration = {"status": "merged", "updatedAt": "2026-03-22T10:00:00Z"}
    ensure_run_review_state(run)
    start_review(run, automated_verdict="pass")
    for stage in ("spec-compliance", "code-quality"):
        set_review_stage(run, stage=stage, status="pass", findings=[], evidence=["pass"])
    set_review_verdict(run, verdict="pass")
    ensure_run_ship_state(run)
    sync_ship_state(run)
    start_ship(run)
    complete_ship(run, commit="abc123", branch="feature/feature-a", pr_url="https://example.com/pr/1")
    save_delivery_run(run, tmp_path)
    heartbeat_feature_lane(tmp_path, "feature-a", status="shipping", lease_owner="dispatcher")
    sync_work_order("feature-a", root=tmp_path)

    report = watch_delivery_runs(root=tmp_path, include_terminal=True)
    kinds = {item["kind"] for item in report["findings"]}
    assert "post_ship_cleanup" in kinds


def test_dispatch_reports_auto_plan_errors_and_blocks_invalid_ready_feature(tmp_path):
    init(tmp_path)
    _workflow(tmp_path)
    _shape(
        tmp_path,
        features=[
            {
                "slug": "feature-a",
                "displayName": "Feature A",
                "userOutcome": "A",
                "scopeSummary": "A scope",
                "dependencies": [],
                "risks": [],
                "priority": 0,
                "status": "ready",
                "readinessReason": "Ready",
                "handoffSummary": "Queue A",
            }
        ],
    )
    _ready_feature(tmp_path, "feature-a", priority=0, related_code=[])

    sync_all_work_orders(root=tmp_path)
    payload = dispatch_ready_features(root=tmp_path)

    assert [entry["feature"] for entry in payload["leased"]] == ["feature-a"]
    assert [entry["feature"] for entry in payload["planErrors"]] == ["feature-a"]
    order = sync_work_order("feature-a", root=tmp_path)
    assert order.status == "blocked"
    assert order.next_action["kind"] == "attention"
