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
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps({"version": 1, "repoShape": "single", "profiles": {"default": "migration-rollout"}}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    assert created.returncode == 0, created.stderr + created.stdout
    run = json.loads(created.stdout)
    assert run["feature"] == "demo"
    assert run["planNumber"] == "01"
    assert run["mode"] == "serial"
    assert run["profile"]["name"] == "migration-rollout"
    assert [task["status"] for task in run["tasks"]] == ["ready", "ready"]
    phase = _run_cli("phase-get", "demo", "--json", cwd=tmp_path)
    assert phase.returncode == 0, phase.stderr + phase.stdout
    assert json.loads(phase.stdout)["phase"] == "implement"

    shown = _run_cli("run-show", "demo", "--json", cwd=tmp_path)
    assert shown.returncode == 0, shown.stderr + shown.stdout
    shown_run = json.loads(shown.stdout)
    assert shown_run["runId"] == run["runId"]
    assert shown_run["profile"]["name"] == "migration-rollout"


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
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps(
            {
                "version": 1,
                "repoShape": "single",
                "agentTeams": {
                    "enabled": True,
                    "defaultCompositions": {"review": ["code-reviewer", "perf-analyzer"]},
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    profiles_dir = tmp_path / ".cnogo" / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    (profiles_dir / "custom.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "custom-review",
                "defaults": {"review": {"requiredReviewers": ["security-scanner"]}},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_plan(tmp_path, feature=feature, plan_number="01", blocked_tail=False)
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / feature
    plan_path = feature_dir / "01-PLAN.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["profile"] = "custom-review"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    created = _run_cli("run-create", feature, "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)
    assert run["profile"]["name"] == "custom-review"

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
    assert review_contract["reviewers"] == ["code-reviewer", "perf-analyzer", "security-scanner"]
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


def test_run_ship_commands_update_delivery_run_ship_state(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    feature = "demo"
    _write_plan(tmp_path, feature=feature, plan_number="01", blocked_tail=False)

    _run_cli("run-create", feature, "01", "--json", cwd=tmp_path)
    _run_cli("run-task-set", feature, "0", "merged", "--json", cwd=tmp_path)
    _run_cli("run-task-set", feature, "1", "merged", "--json", cwd=tmp_path)
    _run_cli("run-plan-verify", feature, "pass", "--command", "pytest -q", "--json", cwd=tmp_path)
    _run_cli("run-review-start", feature, "--reviewer", "code-reviewer", "--json", cwd=tmp_path)
    _run_cli(
        "run-review-stage-set",
        feature,
        "spec-compliance",
        "pass",
        "--evidence",
        "plan",
        "--json",
        cwd=tmp_path,
    )
    _run_cli(
        "run-review-stage-set",
        feature,
        "code-quality",
        "warn",
        "--evidence",
        "tests",
        "--json",
        cwd=tmp_path,
    )
    _run_cli("run-review-verdict", feature, "warn", "--json", cwd=tmp_path)

    started = _run_cli("run-ship-start", feature, "--json", cwd=tmp_path)
    assert started.returncode == 0, started.stderr + started.stdout
    started_payload = json.loads(started.stdout)
    assert started_payload["ship"]["status"] == "in_progress"

    failed = _run_cli("run-ship-fail", feature, "--error", "push failed", "--json", cwd=tmp_path)
    assert failed.returncode == 0, failed.stderr + failed.stdout
    failed_payload = json.loads(failed.stdout)
    assert failed_payload["ship"]["status"] == "failed"

    completed = _run_cli(
        "run-ship-complete",
        feature,
        "abc123",
        "--branch",
        "feature/demo",
        "--pr-url",
        "https://example.test/pr/1",
        "--json",
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ship"]["status"] == "completed"
    assert payload["ship"]["commit"] == "abc123"
    assert payload["ship"]["prUrl"] == "https://example.test/pr/1"


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
    assert listed[0]["profileName"] == "feature-delivery"
    assert listed[0]["reviewStatus"] == "pending"
    assert listed[0]["reviewVerdict"] == "pending"

    watch = _run_cli("run-watch", "--stale-minutes", "0", "--json", cwd=tmp_path)
    assert watch.returncode == 0, watch.stderr + watch.stdout
    report = json.loads(watch.stdout)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert "team_run_missing_session" in kinds
    assert (tmp_path / ".cnogo" / "watch" / "latest.json").is_file()
    assert (tmp_path / ".cnogo" / "watch" / "attention.json").is_file()

    attention = _run_cli("run-attention", "--json", cwd=tmp_path)
    assert attention.returncode == 0, attention.stderr + attention.stdout
    queue = json.loads(attention.stdout)
    assert queue["summary"]["totalItems"] >= 1
    assert any(item["kind"] == "team_run_missing_session" for item in queue["items"])


def test_run_watch_status_and_tick_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)
    _run_cli("run-create", "demo", "01", "--mode", "team", "--json", cwd=tmp_path)

    status_before = _run_cli("run-watch-status", "--json", cwd=tmp_path)
    assert status_before.returncode == 0, status_before.stderr + status_before.stdout
    before_payload = json.loads(status_before.stdout)
    assert before_payload["due"] is True

    first_tick = _run_cli("run-watch-tick", "--json", cwd=tmp_path)
    assert first_tick.returncode == 0, first_tick.stderr + first_tick.stdout
    first_payload = json.loads(first_tick.stdout)
    assert first_payload["executed"] is True
    assert first_payload["schedule"]["lastPatrolAt"]
    assert (tmp_path / ".cnogo" / "watch" / "state.json").is_file()

    second_tick = _run_cli("run-watch-tick", "--json", cwd=tmp_path)
    assert second_tick.returncode == 0, second_tick.stderr + second_tick.stdout
    second_payload = json.loads(second_tick.stdout)
    assert second_payload["executed"] is False
    assert second_payload["schedule"]["due"] is False


def test_run_attention_filters_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)
    _run_cli("run-create", "demo", "01", "--mode", "team", "--json", cwd=tmp_path)
    patrol = _run_cli("run-watch-patrol", "--json", cwd=tmp_path)
    assert patrol.returncode == 0, patrol.stderr + patrol.stdout

    filtered = _run_cli(
        "run-attention",
        "--kind",
        "team_run_missing_session",
        "--severity",
        "warn",
        "--limit",
        "1",
        "--json",
        cwd=tmp_path,
    )
    assert filtered.returncode == 0, filtered.stderr + filtered.stdout
    payload = json.loads(filtered.stdout)
    assert payload["summary"]["matchedItems"] >= 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["kind"] == "team_run_missing_session"


def test_run_watch_patrol_history_and_attention_filter_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)
    _write_plan(tmp_path, feature="quiet", plan_number="01", blocked_tail=False)

    noisy = json.loads(_run_cli("run-create", "demo", "01", "--mode", "team", "--json", cwd=tmp_path).stdout)
    quiet = json.loads(_run_cli("run-create", "quiet", "01", "--mode", "serial", "--json", cwd=tmp_path).stdout)
    assert noisy["runId"] != quiet["runId"]

    patrol = _run_cli("run-watch-patrol", "--json", cwd=tmp_path)
    assert patrol.returncode == 0, patrol.stderr + patrol.stdout
    payload = json.loads(patrol.stdout)
    assert payload["delta"]["summary"]["new"] >= 1
    assert payload["snapshot"]["paths"]["report"].endswith(".cnogo/watch/latest.json")

    attention_only = _run_cli("run-list", "--needs-attention", "--json", cwd=tmp_path)
    assert attention_only.returncode == 0, attention_only.stderr + attention_only.stdout
    listed = json.loads(attention_only.stdout)
    assert [entry["feature"] for entry in listed] == ["demo"]
    assert "team_run_missing_session" in listed[0]["attentionKinds"]

    history = _run_cli("run-watch-history", "--json", cwd=tmp_path)
    assert history.returncode == 0, history.stderr + history.stdout
    history_payload = json.loads(history.stdout)
    assert len(history_payload) >= 1
    assert history_payload[0]["path"].endswith(".json")


def test_run_next_and_task_lifecycle_cli(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=True)

    created = _run_cli("run-create", "demo", "01", "--json", cwd=tmp_path)
    run = json.loads(created.stdout)
    run_id = run["runId"]

    next_ready = _run_cli("run-next", "demo", "--run-id", run_id, "--json", cwd=tmp_path)
    assert next_ready.returncode == 0, next_ready.stderr + next_ready.stdout
    next_payload = json.loads(next_ready.stdout)
    assert next_payload["readyCount"] == 1
    assert next_payload["readyTasks"][0]["taskIndex"] == 0
    assert "run-task-begin demo 0" in next_payload["readyTasks"][0]["beginCommand"]
    assert next_payload["nextAction"]["kind"] == "begin_task"

    begun = _run_cli(
        "run-task-begin",
        "demo",
        "0",
        "--run-id",
        run_id,
        "--actor",
        "implementer",
        "--skip-memory",
        "--json",
        cwd=tmp_path,
    )
    assert begun.returncode == 0, begun.stderr + begun.stdout
    begun_payload = json.loads(begun.stdout)
    assert begun_payload["tasks"][0]["status"] == "in_progress"
    assert begun_payload["tasks"][0]["assignee"] == "implementer"

    completed = _run_cli(
        "run-task-complete",
        "demo",
        "0",
        "--run-id",
        run_id,
        "--actor",
        "implementer",
        "--skip-memory",
        "--command",
        "pytest -q -k one",
        "--json",
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    completed_payload = json.loads(completed.stdout)
    assert completed_payload["tasks"][0]["status"] == "done"
    assert completed_payload["tasks"][1]["status"] == "ready"
    assert any("verify: pytest -q -k one" in note for note in completed_payload["tasks"][0]["notes"])

    second_done = _run_cli(
        "run-task-begin",
        "demo",
        "1",
        "--run-id",
        run_id,
        "--actor",
        "implementer",
        "--skip-memory",
        "--json",
        cwd=tmp_path,
    )
    assert second_done.returncode == 0, second_done.stderr + second_done.stdout
    second_done = _run_cli(
        "run-task-complete",
        "demo",
        "1",
        "--run-id",
        run_id,
        "--actor",
        "implementer",
        "--skip-memory",
        "--command",
        "pytest -q -k two",
        "--json",
        cwd=tmp_path,
    )
    assert second_done.returncode == 0, second_done.stderr + second_done.stdout

    verify_next = _run_cli("run-next", "demo", "--run-id", run_id, "--json", cwd=tmp_path)
    assert verify_next.returncode == 0, verify_next.stderr + verify_next.stdout
    verify_payload = json.loads(verify_next.stdout)
    assert verify_payload["readyCount"] == 0
    assert verify_payload["nextAction"]["kind"] == "run_plan_verify"
    assert "run-plan-verify demo pass" in verify_payload["nextAction"]["command"]

    plan_verify = _run_cli(
        "run-plan-verify",
        "demo",
        "pass",
        "--run-id",
        run_id,
        "--command",
        "pytest -q",
        "--json",
        cwd=tmp_path,
    )
    assert plan_verify.returncode == 0, plan_verify.stderr + plan_verify.stdout
    verified_payload = json.loads(plan_verify.stdout)
    assert [task["status"] for task in verified_payload["tasks"]] == ["merged", "merged"]
    assert verified_payload["reviewReadiness"]["status"] == "ready"
    phase = _run_cli("phase-get", "demo", "--json", cwd=tmp_path)
    assert phase.returncode == 0, phase.stderr + phase.stdout
    assert json.loads(phase.stdout)["phase"] == "review"

    failed = _run_cli(
        "run-task-fail",
        "demo",
        "1",
        "--run-id",
        run_id,
        "--error",
        "fixture broke",
        "--json",
        cwd=tmp_path,
    )
    assert failed.returncode == 0, failed.stderr + failed.stdout
    failed_payload = json.loads(failed.stdout)
    assert failed_payload["tasks"][1]["status"] == "failed"
    assert any("fixture broke" in note for note in failed_payload["tasks"][1]["notes"])


def test_profile_suggest_and_stamp_cli(tmp_path):
    feature = "ledger-rollout"
    plan_path = _write_plan(tmp_path, feature=feature, plan_number="01", blocked_tail=False)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["goal"] = "Apply schema migration and backfill ledger data"
    plan["tasks"][0]["action"] = "Write SQL migration and data backfill"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    suggestion = _run_cli("profile-suggest", feature, "--plan", "01", "--json", cwd=tmp_path)
    assert suggestion.returncode == 0, suggestion.stderr + suggestion.stdout
    suggestion_payload = json.loads(suggestion.stdout)
    assert suggestion_payload["name"] == "migration-rollout"

    stamped = _run_cli("profile-stamp", feature, "01", "--json", cwd=tmp_path)
    assert stamped.returncode == 0, stamped.stderr + stamped.stdout
    stamped_payload = json.loads(stamped.stdout)
    assert stamped_payload["profile"] == "migration-rollout"

    updated_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated_plan["profile"] == "migration-rollout"
    assert "formula" not in updated_plan
    plan_md = plan_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "## Profile" in plan_md
    assert "`migration-rollout`" in plan_md


def test_profile_list_and_init_cli(tmp_path):
    listed = _run_cli("profile-list", "--json", cwd=tmp_path)
    assert listed.returncode == 0, listed.stderr + listed.stdout
    catalog = json.loads(listed.stdout)
    assert any(entry["name"] == "feature-delivery" for entry in catalog)

    created = _run_cli(
        "profile-init",
        "incident-debug",
        "--base",
        "debug-fix",
        "--description",
        "Operational incident response policy.",
        "--json",
        cwd=tmp_path,
    )
    assert created.returncode == 0, created.stderr + created.stdout
    payload = json.loads(created.stdout)
    assert payload["name"] == "incident-debug"
    assert payload["base"] == "debug-fix"
    assert payload["contract"]["defaults"]["review"]["requiredReviewers"] == ["code-reviewer"]
    profile_path = tmp_path / ".cnogo" / "profiles" / "incident-debug.json"
    assert profile_path.is_file()

    listed = _run_cli("profile-list", "--json", cwd=tmp_path)
    assert listed.returncode == 0, listed.stderr + listed.stdout
    catalog = json.loads(listed.stdout)
    assert any(entry["name"] == "incident-debug" and "Operational incident response" in entry["description"] for entry in catalog)


def test_phase_set_backfills_work_order_without_runs(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0

    updated = _run_cli("phase-set", "demo", "plan", "--json", cwd=tmp_path)
    assert updated.returncode == 0, updated.stderr + updated.stdout
    payload = json.loads(updated.stdout)
    assert payload["phase"] == "plan"

    work = _run_cli("work-show", "demo", "--json", cwd=tmp_path)
    assert work.returncode == 0, work.stderr + work.stdout
    order = json.loads(work.stdout)
    assert order["feature"] == "demo"
    assert order["currentPhase"] == "plan"
    assert order["status"] == "planned"


def test_work_order_cli_rolls_up_runs_and_attention(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)
    _run_cli("run-create", "demo", "01", "--mode", "team", "--json", cwd=tmp_path)
    _run_cli("run-watch-patrol", "--json", cwd=tmp_path)

    work_show = _run_cli("work-show", "demo", "--json", cwd=tmp_path)
    assert work_show.returncode == 0, work_show.stderr + work_show.stdout
    order = json.loads(work_show.stdout)
    assert order["workOrderId"] == "demo"
    assert order["currentRunId"]
    assert order["attentionSummary"]["itemCount"] >= 1
    assert order["nextAction"]["kind"] in {"attention", "implement", "begin_task"}

    work_list = _run_cli("work-list", "--needs-attention", "--json", cwd=tmp_path)
    assert work_list.returncode == 0, work_list.stderr + work_list.stdout
    listed = json.loads(work_list.stdout)
    assert listed[0]["feature"] == "demo"

    work_next = _run_cli("work-next", "demo", "--json", cwd=tmp_path)
    assert work_next.returncode == 0, work_next.stderr + work_next.stdout
    next_payload = json.loads(work_next.stdout)
    assert next_payload["workOrder"]["feature"] == "demo"
    assert next_payload["nextAction"]["kind"]


def test_scheduler_cli_runs_once_and_reports_status(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, feature="demo", plan_number="01", blocked_tail=False)
    _run_cli("run-create", "demo", "01", "--mode", "team", "--json", cwd=tmp_path)

    status_before = _run_cli("scheduler-status", "--json", cwd=tmp_path)
    assert status_before.returncode == 0, status_before.stderr + status_before.stdout
    before_payload = json.loads(status_before.stdout)
    assert before_payload["enabled"] is True
    assert before_payload["due"] is True

    ran = _run_cli("scheduler-run-once", "--json", cwd=tmp_path)
    assert ran.returncode == 0, ran.stderr + ran.stdout
    ran_payload = json.loads(ran.stdout)
    assert ran_payload["executed"] is True
    assert sorted(ran_payload["jobs"].keys()) == ["watch_patrol", "work_order_sync"]

    status_after = _run_cli("scheduler-status", "--json", cwd=tmp_path)
    assert status_after.returncode == 0, status_after.stderr + status_after.stdout
    after_payload = json.loads(status_after.stdout)
    assert after_payload["lastRunAt"]
    assert (tmp_path / ".cnogo" / "scheduler" / "state.json").is_file()
