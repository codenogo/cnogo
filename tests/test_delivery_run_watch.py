"""Tests for delivery-run watch and queue helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.orchestration.delivery_run import (  # noqa: E402
    create_delivery_run,
    delivery_run_path,
    save_delivery_run,
    sync_run_with_worktree_session,
    update_delivery_task_status,
)
from scripts.workflow.orchestration.integration import record_plan_verification  # noqa: E402
from scripts.workflow.orchestration.review import (  # noqa: E402
    set_review_stage,
    set_review_verdict,
    start_review,
)
from scripts.workflow.orchestration.ship import (  # noqa: E402
    fail_ship,
    start_ship,
)
from scripts.workflow.orchestration.review_artifacts import (  # noqa: E402
    persist_review_artifact_from_run,
)
from scripts.workflow.orchestration.watch import (  # noqa: E402
    list_delivery_runs,
    watch_delivery_runs,
)
from scripts.workflow.orchestration.watch_artifacts import (  # noqa: E402
    attention_queue_path,
    load_attention_queue,
    load_watch_report,
    persist_watch_report,
    watch_report_path,
)


def _task_desc(index: int, *, blocked_by: list[int] | None = None) -> dict:
    return {
        "task_id": f"cn-watch-{index}",
        "plan_task_index": index,
        "title": f"Task {index}",
        "action": "Do the work",
        "file_scope": {"paths": [f"app/{index}.py"], "forbidden": []},
        "commands": {"verify": [f"pytest -q -k task_{index}"], "package_verify": []},
        "blockedBy": blocked_by or [],
        "micro_steps": ["write test", "implement", "verify"],
        "tdd": {"required": True},
    }


def _write_plan(root: Path, feature: str, plan: str) -> Path:
    plan_path = root / "docs" / "planning" / "work" / "features" / feature / f"{plan}-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")
    return plan_path


def _force_updated_at(root: Path, feature: str, run_id: str, timestamp: str) -> None:
    run_path = delivery_run_path(root, feature, run_id)
    contract = json.loads(run_path.read_text(encoding="utf-8"))
    contract["updatedAt"] = timestamp
    run_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_list_delivery_runs_filters_terminal_status_by_default(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")

    active = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-active",
    )
    completed = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-complete",
    )
    completed = update_delivery_task_status(completed, task_index=0, status="merged")
    save_delivery_run(completed, tmp_path)

    listed = list_delivery_runs(tmp_path)
    assert [run.run_id for run in listed] == ["demo-active"]

    all_runs = list_delivery_runs(tmp_path, include_terminal=True)
    assert {run.run_id for run in all_runs} == {"demo-active", "demo-complete"}


def test_watch_delivery_runs_detects_stale_active_team_run_without_session(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0), _task_desc(1, blocked_by=[0])],
        mode="team",
        run_id="demo-team",
    )
    _force_updated_at(tmp_path, "demo", "demo-team", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=60)
    kinds = {finding["kind"] for finding in report["findings"]}

    assert "team_run_missing_session" in kinds
    assert "stale_active_run" in kinds


def test_watch_delivery_runs_detects_ready_for_review_staleness(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-review",
    )
    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merged",
            "mergedSoFar": [0],
            "worktrees": [{"taskIndex": 0, "status": "merged"}],
        },
    )
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    save_delivery_run(run, tmp_path)
    _force_updated_at(tmp_path, "demo", "demo-review", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    ready_findings = [finding for finding in report["findings"] if finding["kind"] == "ready_for_review_stale"]

    assert ready_findings
    assert ready_findings[0]["runId"] == "demo-review"


def test_watch_delivery_runs_uses_formula_thresholds(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-formula-watch",
        formula={
            "name": "migration-rollout",
            "version": "1.0.0",
            "source": "builtin",
            "resolvedPolicy": {"watch": {"staleMinutes": 5, "reviewStaleMinutes": 15}},
        },
    )
    _force_updated_at(tmp_path, "demo", "demo-formula-watch", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=120, review_stale_minutes=120)
    findings = [finding for finding in report["findings"] if finding["runId"] == "demo-formula-watch"]

    assert any(finding["kind"] == "team_run_missing_session" for finding in findings)
    assert any(finding["kind"] == "stale_active_run" for finding in findings)


def test_watch_delivery_runs_detects_review_in_progress_and_failed_followup(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-review-progress",
    )
    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merged",
            "mergedSoFar": [0],
            "worktrees": [{"taskIndex": 0, "status": "merged"}],
        },
    )
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    run = start_review(run, reviewers=["code-reviewer"], automated_verdict="warn")
    save_delivery_run(run, tmp_path)
    _force_updated_at(tmp_path, "demo", "demo-review-progress", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "review_in_progress_stale" in kinds

    run = set_review_stage(
        run,
        stage="spec-compliance",
        status="pass",
        findings=[],
        evidence=["plan"],
        notes=["ok"],
    )
    run = set_review_stage(
        run,
        stage="code-quality",
        status="fail",
        findings=["blocker"],
        evidence=["tests"],
        notes=["fix needed"],
    )
    run = set_review_verdict(run, verdict="fail")
    save_delivery_run(run, tmp_path)
    _force_updated_at(tmp_path, "demo", "demo-review-progress", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "review_failed_followup_stale" in kinds


def test_watch_delivery_runs_detects_session_missing_run(tmp_path):
    cnogo_dir = tmp_path / ".cnogo"
    cnogo_dir.mkdir(parents=True, exist_ok=True)
    (cnogo_dir / "worktree-session.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "demo",
                "planNumber": "01",
                "runId": "missing-run",
                "baseCommit": "abc123",
                "baseBranch": "feature/demo",
                "phase": "executing",
                "worktrees": [],
                "mergeOrder": [],
                "mergedSoFar": [],
            }
        ),
        encoding="utf-8",
    )

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=60)
    kinds = {finding["kind"] for finding in report["findings"]}

    assert "session_missing_run" in kinds


def test_persist_watch_report_writes_latest_and_attention_queue(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-watch-persist",
    )
    _force_updated_at(tmp_path, "demo", "demo-watch-persist", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=60)
    persisted = persist_watch_report(tmp_path, report)

    assert watch_report_path(tmp_path).is_file()
    assert attention_queue_path(tmp_path).is_file()
    latest = load_watch_report(tmp_path)
    attention = load_attention_queue(tmp_path)
    assert latest is not None
    assert attention is not None
    assert latest["paths"]["attention"] == str(attention_queue_path(tmp_path))
    assert attention["sourceReportPath"] == str(watch_report_path(tmp_path))
    assert attention["summary"]["totalItems"] == len(attention["items"])
    assert persisted["attention"]["summary"]["totalItems"] == len(persisted["attention"]["items"])


def test_watch_delivery_runs_detects_review_artifact_drift(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-review-drift",
    )
    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merged",
            "mergedSoFar": [0],
            "worktrees": [{"taskIndex": 0, "status": "merged"}],
        },
    )
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    run = start_review(run, reviewers=["code-reviewer"], automated_verdict="pass")
    run = set_review_stage(
        run,
        stage="spec-compliance",
        status="pass",
        findings=[],
        evidence=["plan"],
        notes=["ok"],
    )
    run = set_review_stage(
        run,
        stage="code-quality",
        status="pass",
        findings=[],
        evidence=["tests"],
        notes=["ok"],
    )
    run = set_review_verdict(run, verdict="pass")
    persist_review_artifact_from_run(tmp_path, run)
    save_delivery_run(run, tmp_path)

    review_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "REVIEW.json"
    review_data = json.loads(review_path.read_text(encoding="utf-8"))
    review_data["verdict"] = "warn"
    review_path.write_text(json.dumps(review_data), encoding="utf-8")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "review_artifact_drift" in kinds


def test_watch_delivery_runs_detects_ready_and_failed_ship_staleness(tmp_path):
    plan_path = _write_plan(tmp_path, "demo", "01")
    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-ship-watch",
    )
    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merged",
            "mergedSoFar": [0],
            "worktrees": [{"taskIndex": 0, "status": "merged"}],
        },
    )
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    run = start_review(run, reviewers=["code-reviewer"], automated_verdict="pass")
    run = set_review_stage(
        run,
        stage="spec-compliance",
        status="pass",
        findings=[],
        evidence=["plan"],
        notes=["ok"],
    )
    run = set_review_stage(
        run,
        stage="code-quality",
        status="pass",
        findings=[],
        evidence=["tests"],
        notes=["ok"],
    )
    run = set_review_verdict(run, verdict="pass")
    save_delivery_run(run, tmp_path)
    _force_updated_at(tmp_path, "demo", "demo-ship-watch", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "ready_to_ship_stale" in kinds

    run = start_ship(run)
    run = fail_ship(run, error="push failed")
    save_delivery_run(run, tmp_path)
    _force_updated_at(tmp_path, "demo", "demo-ship-watch", "2020-01-01T00:00:00Z")

    report = watch_delivery_runs(tmp_path, stale_minutes=10, review_stale_minutes=30)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "ship_failed_stale" in kinds
