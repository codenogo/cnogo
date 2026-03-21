"""Tests for review lifecycle state on delivery runs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.orchestration.delivery_run import (  # noqa: E402
    create_delivery_run,
    save_delivery_run,
    update_delivery_task_status,
)
from scripts.workflow.orchestration.integration import record_plan_verification  # noqa: E402
from scripts.workflow.orchestration.review import (  # noqa: E402
    set_review_stage,
    set_review_verdict,
    start_review,
    sync_review_from_artifact,
)


def _task_desc(index: int) -> dict:
    return {
        "task_id": f"cn-review-{index}",
        "plan_task_index": index,
        "title": f"Task {index}",
        "action": "Do the work",
        "file_scope": {"paths": [f"app/{index}.py"], "forbidden": []},
        "commands": {"verify": [f"pytest -q -k task_{index}"], "package_verify": []},
        "micro_steps": ["write test", "implement", "verify"],
        "tdd": {"required": True},
    }


def test_review_state_progresses_from_ready_to_completed(tmp_path):
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
        run_id="demo-review-flow",
    )

    run = update_delivery_task_status(run, task_index=0, status="merged")
    run = record_plan_verification(run, passed=True, commands=["pytest -q"])
    assert run.review_readiness["status"] == "ready"
    assert run.review["status"] == "ready"

    run = start_review(
        run,
        reviewers=["code-reviewer", "security-scanner"],
        automated_verdict="warn",
        note="Automated review started",
    )
    assert run.review["status"] == "in_progress"
    assert run.review["reviewers"] == ["code-reviewer", "security-scanner"]

    run = set_review_stage(
        run,
        stage="spec-compliance",
        status="pass",
        findings=[],
        evidence=["checked against plan"],
        notes=["spec complete"],
    )
    run = set_review_stage(
        run,
        stage="code-quality",
        status="warn",
        findings=["needs follow-up"],
        evidence=["lint", "tests"],
        notes=["quality review complete"],
    )
    run = set_review_verdict(run, verdict="warn", note="Ready to discuss ship risk")

    assert run.review["status"] == "completed"
    assert run.review["finalVerdict"] == "warn"
    assert run.review["reviewCompletedAt"]


def test_review_sync_from_artifact_populates_run_review_state(tmp_path):
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    plan_path = feature_dir / "01-PLAN.json"
    plan_path.write_text("{}", encoding="utf-8")
    review_path = feature_dir / "REVIEW.json"
    review_path.write_text(
        json.dumps(
            {
                "schemaVersion": 4,
                "timestamp": "2026-03-21T10:00:00Z",
                "reviewers": ["code-reviewer", "perf-analyzer"],
                "automatedVerdict": "pass",
                "verdict": "pass",
                "stageReviews": [
                    {
                        "stage": "spec-compliance",
                        "status": "pass",
                        "findings": [],
                        "evidence": ["plan checked"],
                        "notes": "ok",
                    },
                    {
                        "stage": "code-quality",
                        "status": "pass",
                        "findings": [],
                        "evidence": ["tests"],
                        "notes": "ok",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    run = create_delivery_run(
        tmp_path,
        feature="demo",
        plan_number="01",
        plan_path=plan_path,
        task_descriptions=[_task_desc(0)],
        mode="serial",
        run_id="demo-review-sync",
    )
    run.review_readiness["status"] = "ready"
    run = sync_review_from_artifact(run, root=tmp_path)
    save_delivery_run(run, tmp_path)

    assert run.review["status"] == "completed"
    assert run.review["automatedVerdict"] == "pass"
    assert run.review["finalVerdict"] == "pass"
    assert run.review["reviewers"] == ["code-reviewer", "perf-analyzer"]
    assert run.review["stages"][0]["stage"] == "spec-compliance"
    assert run.review["stages"][1]["status"] == "pass"
