"""Tests for workflow delivery-run orchestration helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.orchestration.delivery_run import (  # noqa: E402
    create_delivery_run,
    delivery_run_path,
    latest_delivery_run,
    load_delivery_run,
    save_delivery_run,
    sync_run_with_worktree_session,
    update_delivery_task_status,
)
from scripts.workflow.orchestration.integration import record_plan_verification  # noqa: E402
from scripts.workflow.orchestration.ship import (  # noqa: E402
    complete_ship,
    fail_ship,
    start_ship,
)


def _task_desc(
    index: int,
    *,
    title: str | None = None,
    blocked_by: list[int] | None = None,
    skipped: bool = False,
) -> dict:
    return {
        "task_id": f"cn-task-{index}",
        "plan_task_index": index,
        "title": title or f"Task {index}",
        "action": "Do the work",
        "file_scope": {"paths": [f"file-{index}.py"], "forbidden": []},
        "commands": {
            "verify": [f"pytest -q -k task_{index}"],
            "package_verify": [f"ruff check file-{index}.py"],
        },
        "completion_footer": f"TASK_DONE: [cn-task-{index}]",
        "blockedBy": blocked_by or [],
        "micro_steps": ["write test", "implement", "verify"],
        "tdd": {"required": True},
        "skipped": skipped,
    }


def test_create_delivery_run_persists_and_sets_initial_frontier(tmp_path):
    plan_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[
            _task_desc(0),
            _task_desc(1, blocked_by=[0]),
            _task_desc(2, skipped=True),
        ],
        mode="team",
        run_id="demo-100",
        recommendation={"recommended": True, "reason": "independent frontier"},
    )

    assert delivery_run_path(tmp_path, "demo", "demo-100").exists()
    assert run.status == "active"
    assert [task.status for task in run.tasks] == ["ready", "pending", "skipped"]

    loaded = load_delivery_run(tmp_path, "demo", "demo-100")
    assert loaded is not None
    assert loaded.run_id == "demo-100"
    assert loaded.mode == "team"
    assert loaded.plan_path.endswith("01-PLAN.json")
    assert loaded.summary_path.endswith("01-SUMMARY.json")
    assert loaded.review_path.endswith("REVIEW.json")


def test_create_delivery_run_persists_formula(tmp_path):
    plan_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-formula",
        formula={
            "name": "migration-rollout",
            "version": "1.0.0",
            "source": "builtin",
            "resolvedPolicy": {"execution": {"modePreference": "serial"}},
        },
    )

    assert run.formula["name"] == "migration-rollout"
    loaded = load_delivery_run(tmp_path, "demo", "demo-formula")
    assert loaded is not None
    assert loaded.formula["name"] == "migration-rollout"


def test_update_delivery_task_status_promotes_blocked_tasks_and_advances_run(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0), _task_desc(1, blocked_by=[0])],
        mode="serial",
        run_id="demo-200",
    )

    run = update_delivery_task_status(run, task_index=0, status="in_progress", assignee="impl-a")
    assert run.tasks[0].status == "in_progress"
    assert run.tasks[0].assignee == "impl-a"
    assert run.tasks[1].status == "pending"

    run = update_delivery_task_status(run, task_index=0, status="done")
    assert run.tasks[0].status == "done"
    assert run.tasks[1].status == "ready"
    assert run.status == "active"

    run = update_delivery_task_status(run, task_index=1, status="done")
    assert run.status == "ready_for_review"

    run = update_delivery_task_status(run, task_index=0, status="merged")
    run = update_delivery_task_status(run, task_index=1, status="merged")
    assert run.status == "active"
    assert run.review_readiness["status"] == "awaiting_verification"


def test_sync_run_with_worktree_session_applies_branch_path_and_status_mapping(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0), _task_desc(1)],
        mode="team",
        run_id="demo-300",
    )

    synced = sync_run_with_worktree_session(
        run,
        {
            "worktrees": [
                {
                    "taskIndex": 0,
                    "status": "executing",
                    "branch": "agent/demo-0",
                    "path": "/tmp/demo-0",
                    "memoryId": "cn-task-0",
                },
                {
                    "taskIndex": 1,
                    "status": "completed",
                    "branch": "agent/demo-1",
                    "path": "/tmp/demo-1",
                },
            ]
        },
    )

    assert synced.tasks[0].status == "in_progress"
    assert synced.tasks[0].branch == "agent/demo-0"
    assert synced.tasks[0].worktree_path == "/tmp/demo-0"
    assert synced.tasks[1].status == "done"
    assert synced.tasks[1].branch == "agent/demo-1"


def test_latest_delivery_run_returns_newest_saved_run(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    older = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-older",
    )
    older_path = save_delivery_run(older, tmp_path)
    os.utime(older_path, (1, 1))

    newer = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-newer",
    )
    save_delivery_run(newer, tmp_path)

    latest = latest_delivery_run(tmp_path, "demo")
    assert latest is not None
    assert latest.run_id == "demo-newer"


def test_integration_and_review_readiness_progress_with_merge_and_plan_verification(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0), _task_desc(1)],
        mode="team",
        run_id="demo-400",
    )

    run = update_delivery_task_status(run, task_index=0, status="done")
    run = update_delivery_task_status(run, task_index=1, status="done")
    assert run.integration["status"] == "awaiting_merge"
    assert run.review_readiness["status"] == "pending"

    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merged",
            "mergedSoFar": [0, 1],
            "worktrees": [
                {"taskIndex": 0, "status": "merged"},
                {"taskIndex": 1, "status": "merged"},
            ],
        },
    )
    assert run.integration["status"] == "merged"
    assert run.review_readiness["status"] == "awaiting_verification"

    run = record_plan_verification(
        run,
        passed=True,
        commands=["pytest -q", "ruff check ."],
        note="plan verify passed",
    )
    assert run.review_readiness["status"] == "ready"
    assert run.review_readiness["planVerifyPassed"] is True
    assert run.status == "ready_for_review"


def test_conflicts_block_review_readiness(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-401",
    )

    run = sync_run_with_worktree_session(
        run,
        {
            "phase": "merging",
            "worktrees": [
                {
                    "taskIndex": 0,
                    "status": "conflict",
                    "conflictFiles": ["app/conflict.py"],
                }
            ],
        },
    )

    assert run.integration["status"] == "conflicted"
    assert run.integration["conflictTaskIndex"] == 0
    assert run.review_readiness["status"] == "blocked"


def test_ship_state_progresses_from_ready_to_completed_and_failed(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-ship-1",
    )

    run = update_delivery_task_status(run, task_index=0, status="merged")
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    run.review["status"] = "completed"
    run.review["finalVerdict"] = "pass"

    run = start_ship(run, note="shipping started")
    assert run.ship["status"] == "in_progress"
    assert run.ship["attempts"] == 1

    run = fail_ship(run, error="push failed", note="retry needed")
    assert run.ship["status"] == "failed"
    assert run.ship["lastError"] == "push failed"

    run = start_ship(run, note="retry")
    run = complete_ship(
        run,
        commit="abc123",
        branch="feature/demo",
        pr_url="https://example.test/pr/1",
        note="shipped",
    )
    assert run.ship["status"] == "completed"
    assert run.ship["commit"] == "abc123"
    assert run.ship["prUrl"] == "https://example.test/pr/1"


def test_complete_ship_requires_pr_metadata_when_formula_demands_it(tmp_path):
    plan_path = tmp_path / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-ship-policy",
        formula={
            "name": "feature-delivery",
            "version": "1.0.0",
            "source": "builtin",
            "resolvedPolicy": {"ship": {"requireTracking": True, "requirePullRequest": True}},
        },
    )

    run = update_delivery_task_status(run, task_index=0, status="merged")
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    run.review["status"] = "completed"
    run.review["finalVerdict"] = "pass"

    run = start_ship(run)
    try:
        complete_ship(run, commit="abc123", branch="feature/demo")
    except ValueError as exc:
        assert "PR URL" in str(exc)
    else:
        raise AssertionError("expected formula PR requirement to block completion")
