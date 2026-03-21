"""CLI tests for delivery-run subcommands on workflow_memory.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".cnogo" / "scripts" / "workflow_memory.py"


def _run_cli(*args: str, cwd: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _write_plan(root: Path, *, feature: str, plan_number: str, blocked_tail: bool) -> Path:
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    plan_path = feature_dir / f"{plan_number}-PLAN.json"
    second_task: dict[str, object] = {
        "name": "Task 1",
        "files": ["app/one.py"],
        "action": "Implement first slice",
        "verify": ["pytest -q -k one"],
    }
    third_task: dict[str, object] = {
        "name": "Task 2",
        "files": ["app/two.py"],
        "action": "Implement second slice",
        "verify": ["pytest -q -k two"],
    }
    if blocked_tail:
        third_task["blockedBy"] = [0]
    plan = {
        "feature": feature,
        "planNumber": plan_number,
        "goal": "Demo plan",
        "tasks": [second_task, third_task],
        "planVerify": ["pytest -q"],
        "commitMessage": "feat: demo",
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


def test_run_create_and_show_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    assert created.returncode == 0, created.stderr + created.stdout
    run = json.loads(created.stdout)
    assert run["feature"] == "demo"
    assert run["planNumber"] == "01"
    assert run["mode"] == "team"
    assert [task["status"] for task in run["tasks"]] == ["ready", "ready"]

    shown = _run_cli("run-show", "demo", "--json", cwd=tmp_path)
    assert shown.returncode == 0, shown.stderr + shown.stdout
    shown_run = json.loads(shown.stdout)
    assert shown_run["runId"] == run["runId"]


def test_run_task_set_promotes_blocked_tail(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=True)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)
    assert run["mode"] == "serial"
    assert [task["status"] for task in run["tasks"]] == ["ready", "pending"]

    updated = _run_cli(
        "run-task-set",
        "demo",
        "0",
        "done",
        "--assignee",
        "implementer",
        "--json",
        cwd=tmp_path,
    )
    assert updated.returncode == 0, updated.stderr + updated.stdout
    run = json.loads(updated.stdout)
    assert run["tasks"][0]["status"] == "done"
    assert run["tasks"][0]["assignee"] == "implementer"
    assert run["tasks"][1]["status"] == "ready"


def test_run_sync_session_updates_task_state_from_worktree_session(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    session_path = tmp_path / ".cnogo" / "worktree-session.json"
    session_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "demo",
                "planNumber": "01",
                "runId": run["runId"],
                "phase": "executing",
                "worktrees": [
                    {
                        "taskIndex": 0,
                        "name": "Task 0",
                        "branch": "agent/demo-0",
                        "path": "/tmp/demo-0",
                        "status": "executing",
                    },
                    {
                        "taskIndex": 1,
                        "name": "Task 1",
                        "branch": "agent/demo-1",
                        "path": "/tmp/demo-1",
                        "status": "completed",
                    },
                ],
                "mergeOrder": [0, 1],
                "mergedSoFar": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    synced = _run_cli("run-sync-session", "demo", "--json", cwd=tmp_path)
    assert synced.returncode == 0, synced.stderr + synced.stdout
    run = json.loads(synced.stdout)
    assert run["tasks"][0]["status"] == "in_progress"
    assert run["tasks"][0]["branch"] == "agent/demo-0"
    assert run["tasks"][1]["status"] == "done"


def test_session_status_json_includes_linked_delivery_run(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    session_path = tmp_path / ".cnogo" / "worktree-session.json"
    session_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "demo",
                "planNumber": "01",
                "runId": run["runId"],
                "baseCommit": "abc123",
                "baseBranch": "feature/demo",
                "phase": "executing",
                "worktrees": [],
                "mergeOrder": [],
                "mergedSoFar": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    status = _run_cli("session-status", "--json", cwd=tmp_path)
    assert status.returncode == 0, status.stderr + status.stdout
    payload = json.loads(status.stdout)
    assert payload["runId"] == run["runId"]
    assert payload["deliveryRun"]["runId"] == run["runId"]
    assert payload["deliveryRun"]["feature"] == "demo"


def test_run_plan_verify_records_review_readiness(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    _run_cli("run-task-set", "demo", "0", "merged", "--json", cwd=tmp_path)
    _run_cli("run-task-set", "demo", "1", "merged", "--json", cwd=tmp_path)

    verified = _run_cli(
        "run-plan-verify",
        "demo",
        "pass",
        "--command",
        "pytest -q",
        "--command",
        "ruff check .",
        "--note",
        "plan verify passed",
        "--json",
        cwd=tmp_path,
    )
    assert verified.returncode == 0, verified.stderr + verified.stdout
    payload = json.loads(verified.stdout)
    assert payload["reviewReadiness"]["status"] == "ready"
    assert payload["reviewReadiness"]["planVerifyPassed"] is True
    assert payload["integration"]["status"] == "merged"


def test_run_review_commands_update_delivery_run_review_state(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    feature = "demo"
    _write_plan(tmp_path, feature=feature, plan_number="01", blocked_tail=False)
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature

    created = _run_cli("run-create", feature, "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    _run_cli("run-task-set", feature, "0", "merged", "--json", cwd=tmp_path)
    _run_cli("run-task-set", feature, "1", "merged", "--json", cwd=tmp_path)
    _run_cli("run-plan-verify", feature, "pass", "--command", "pytest -q", "--json", cwd=tmp_path)

    started = _run_cli(
        "run-review-start",
        feature,
        "--reviewer",
        "code-reviewer",
        "--automated-verdict",
        "warn",
        "--json",
        cwd=tmp_path,
    )
    assert started.returncode == 0, started.stderr + started.stdout
    started_payload = json.loads(started.stdout)
    review_json = feature_dir / "REVIEW.json"
    review_md = feature_dir / "REVIEW.md"
    assert started_payload["review"]["status"] == "in_progress"
    assert review_json.exists()
    assert review_md.exists()
    review_contract = json.loads(review_json.read_text(encoding="utf-8"))
    assert review_contract["automatedVerdict"] == "warn"
    assert review_contract["stageReviews"][0]["status"] == "pending"

    stage_one = _run_cli(
        "run-review-stage-set",
        feature,
        "spec-compliance",
        "pass",
        "--evidence",
        "checked plan",
        "--json",
        cwd=tmp_path,
    )
    assert stage_one.returncode == 0, stage_one.stderr + stage_one.stdout
    review_contract = json.loads(review_json.read_text(encoding="utf-8"))
    assert review_contract["stageReviews"][0]["status"] == "pass"
    assert review_contract["stageReviews"][0]["evidence"] == ["checked plan"]

    stage_two = _run_cli(
        "run-review-stage-set",
        feature,
        "code-quality",
        "warn",
        "--finding",
        "minor issue",
        "--evidence",
        "pytest -q",
        "--json",
        cwd=tmp_path,
    )
    assert stage_two.returncode == 0, stage_two.stderr + stage_two.stdout

    verdict = _run_cli("run-review-verdict", feature, "warn", "--json", cwd=tmp_path)
    assert verdict.returncode == 0, verdict.stderr + verdict.stdout
    payload = json.loads(verdict.stdout)
    review_contract = json.loads(review_json.read_text(encoding="utf-8"))
    assert payload["review"]["status"] == "completed"
    assert payload["review"]["finalVerdict"] == "warn"
    assert review_contract["verdict"] == "warn"
    assert review_contract["stageReviews"][1]["status"] == "warn"
    assert "## Final Verdict" in review_md.read_text(encoding="utf-8")


def test_run_review_sync_reads_review_contract(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    feature = "demo"
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    _write_plan(tmp_path, feature=feature, plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", feature, "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    _run_cli("run-task-set", feature, "0", "merged", "--json", cwd=tmp_path)
    _run_cli("run-task-set", feature, "1", "merged", "--json", cwd=tmp_path)
    _run_cli("run-plan-verify", feature, "pass", "--command", "pytest -q", "--json", cwd=tmp_path)

    (feature_dir / "REVIEW.json").write_text(
        json.dumps(
            {
                "schemaVersion": 4,
                "timestamp": "2026-03-21T11:00:00Z",
                "reviewers": ["code-reviewer", "security-scanner"],
                "automatedVerdict": "pass",
                "verdict": "pass",
                "stageReviews": [
                    {
                        "stage": "spec-compliance",
                        "status": "pass",
                        "findings": [],
                        "evidence": ["plan"],
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

    synced = _run_cli("run-review-sync", feature, "--run-id", run["runId"], "--json", cwd=tmp_path)
    assert synced.returncode == 0, synced.stderr + synced.stdout
    payload = json.loads(synced.stdout)
    assert payload["review"]["status"] == "completed"
    assert payload["review"]["finalVerdict"] == "pass"
    assert payload["review"]["reviewers"] == ["code-reviewer", "security-scanner"]


def test_run_list_and_run_watch_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)

    run_list = _run_cli("run-list", "--json", cwd=tmp_path)
    assert run_list.returncode == 0, run_list.stderr + run_list.stdout
    listed = json.loads(run_list.stdout)
    assert listed[0]["runId"] == run["runId"]
    assert listed[0]["feature"] == "demo"
    assert listed[0]["reviewStatus"] == "pending"
    assert listed[0]["reviewVerdict"] == "pending"

    watch = _run_cli("run-watch", "--stale-minutes", "0", "--json", cwd=tmp_path)
    assert watch.returncode == 0, watch.stderr + watch.stdout
    report = json.loads(watch.stdout)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "team_run_missing_session" in kinds
