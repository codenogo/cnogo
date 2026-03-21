"""Tests for implementation-lifecycle delivery-run helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.orchestration.delivery_run import create_delivery_run, update_delivery_task_status  # noqa: E402
from scripts.workflow.orchestration.implement import (  # noqa: E402
    complete_task_execution,
    next_delivery_run_action,
    record_plan_verification_for_execution,
)
from scripts.workflow.orchestration.review import set_review_stage, set_review_verdict, start_review  # noqa: E402
from scripts.workflow.orchestration.ship import sync_ship_state  # noqa: E402


def _task_desc(index: int, *, blocked_by: list[int] | None = None) -> dict:
    return {
        "task_id": f"cn-impl-{index}",
        "plan_task_index": index,
        "title": f"Task {index}",
        "action": "Do the work",
        "file_scope": {"paths": [f"app/{index}.py"], "forbidden": []},
        "commands": {"verify": [f"pytest -q -k task_{index}"], "package_verify": []},
        "blockedBy": blocked_by or [],
        "micro_steps": ["write test", "implement", "verify"],
        "tdd": {"required": True},
    }


def test_record_plan_verification_for_execution_merges_serial_tasks(tmp_path):
    plan_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0), _task_desc(1)],
        mode="serial",
        run_id="demo-serial-verify",
    )
    run = complete_task_execution(run, task_index=0, actor="implementer", verify_commands=["pytest -q -k task_0"])
    run = complete_task_execution(run, task_index=1, actor="implementer", verify_commands=["pytest -q -k task_1"])

    assert run.integration["status"] == "awaiting_merge"
    assert run.review_readiness["status"] == "pending"

    run = record_plan_verification_for_execution(
        run,
        passed=True,
        commands=["pytest -q", "ruff check ."],
        note="serial verify passed",
    )

    assert [task.status for task in run.tasks] == ["merged", "merged"]
    assert run.integration["status"] == "merged"
    assert run.review_readiness["status"] == "ready"
    assert run.status == "ready_for_review"


def test_next_delivery_run_action_guides_serial_verify_and_team_merge(tmp_path):
    plan_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "01-PLAN.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text("{}", encoding="utf-8")

    serial_run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-serial-next",
    )
    serial_run = complete_task_execution(serial_run, task_index=0, actor="implementer")
    serial_next = next_delivery_run_action(serial_run)

    assert serial_next["kind"] == "run_plan_verify"
    assert "run-plan-verify demo pass" in serial_next["command"]

    team_run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="team",
        run_id="demo-team-next",
    )
    team_run = update_delivery_task_status(team_run, task_index=0, status="done")
    team_next = next_delivery_run_action(team_run)

    assert team_next["kind"] == "merge_team_session"
    assert "session-merge" in team_next["command"]


def test_next_delivery_run_action_guides_review_and_ship(tmp_path):
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
        run_id="demo-review-ship-next",
    )
    run = complete_task_execution(run, task_index=0, actor="implementer")
    run = record_plan_verification_for_execution(run, passed=True, commands=["pytest -q"])

    review_next = next_delivery_run_action(run)
    assert review_next["kind"] == "start_review"
    assert review_next["command"] == "/review demo"

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
    run = sync_ship_state(run)

    ship_next = next_delivery_run_action(run)
    assert ship_next["kind"] == "start_ship"
    assert ship_next["command"] == "/ship demo"
