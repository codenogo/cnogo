"""Tests for task closure enforcement through verify_and_close evidence gates."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.memory import (
    claim,
    close,
    create,
    init,
    release,
    report_done,
    show,
    stalled_tasks,
    takeover_task,
)


def _write_workflow(root: Path) -> None:
    cfg_path = root / "docs" / "planning" / "WORKFLOW.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        json.dumps(
            {
                "enforcement": {
                    "tddMode": "error",
                    "verificationBeforeCompletion": "error",
                    "taskOwnership": "error",
                },
                "agentTeams": {
                    "staleIndicatorMinutes": 10,
                    "maxTakeoversPerTask": 2,
                }
            }
        ),
        encoding="utf-8",
    )


def test_close_task_fails_without_required_completion_evidence(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create(
        "task without evidence",
        issue_type="task",
        metadata={
            "requiresCompletionEvidence": True,
            "tdd": {"required": True},
        },
        root=root,
    )
    claim(issue.id, actor="implementer", root=root)
    report_done(issue.id, actor="implementer", root=root)

    with pytest.raises(ValueError, match="Completion evidence policy violation"):
        close(issue.id, actor="leader", actor_role="leader", root=root)

    after = show(issue.id, root=root)
    assert after is not None
    assert after.state == "done_by_worker"


def test_close_task_passes_with_valid_completion_evidence(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create(
        "task with evidence",
        issue_type="task",
        metadata={
            "requiresCompletionEvidence": True,
            "tdd": {"required": True},
        },
        root=root,
    )
    claim(issue.id, actor="implementer", root=root)
    report_done(
        issue.id,
        actor="implementer",
        outputs={
            "verification": {
                "commands": ["pytest -q"],
                "timestamp": "2026-02-25T10:00:00Z",
            },
            "tdd": {
                "required": True,
                "failingVerify": ["pytest tests/test_x.py -k failing_case"],
                "passingVerify": ["pytest tests/test_x.py -k failing_case"],
            },
        },
        root=root,
    )

    closed = close(issue.id, actor="leader", actor_role="leader", root=root)
    assert closed.state == "closed"
    assert closed.status == "closed"


def test_report_done_fails_when_unclaimed(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("unclaimed", issue_type="task", root=root)
    with pytest.raises(ValueError, match="unclaimed task"):
        report_done(issue.id, actor="worker-a", root=root)


def test_report_done_fails_on_assignee_mismatch(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("ownership mismatch", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    with pytest.raises(ValueError, match="actor must match assignee"):
        report_done(issue.id, actor="worker-b", root=root)


def test_claim_idempotent_for_same_actor(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("idempotent claim", issue_type="task", root=root)
    first = claim(issue.id, actor="worker-a", root=root)
    second = claim(issue.id, actor="worker-a", root=root)
    assert first.assignee == "worker-a"
    assert second.assignee == "worker-a"


def test_claim_rejects_reopen_when_done_by_worker(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("done then claim", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    report_done(issue.id, actor="worker-a", root=root)
    with pytest.raises(ValueError, match="cannot re-claim"):
        claim(issue.id, actor="worker-a", root=root)


def test_takeover_reassigns_and_rejects_old_actor(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("takeover candidate", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    takeover = takeover_task(
        issue.id,
        to_actor="worker-b",
        reason="stalled for 15m",
        actor="leader",
        root=root,
    )
    assert takeover["to_actor"] == "worker-b"
    assert takeover["attempt"] == 1

    with pytest.raises(ValueError, match="actor must match assignee"):
        report_done(issue.id, actor="worker-a", root=root)
    report_done(issue.id, actor="worker-b", root=root)


def test_takeover_limit_enforced(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("takeover limit", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    takeover_task(issue.id, to_actor="worker-b", reason="stalled", actor="leader", root=root)
    takeover_task(issue.id, to_actor="worker-c", reason="stalled", actor="leader", root=root)
    with pytest.raises(ValueError, match="Takeover limit reached"):
        takeover_task(issue.id, to_actor="worker-d", reason="stalled", actor="leader", root=root)


def test_takeover_rejects_done_by_worker_state(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("takeover done state", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    report_done(issue.id, actor="worker-a", root=root)
    with pytest.raises(ValueError, match="active execution state"):
        takeover_task(
            issue.id,
            to_actor="worker-b",
            reason="stalled",
            actor="leader",
            root=root,
        )


def test_stalled_tasks_returns_overdue_in_progress_tasks(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    stale_issue = create("stale", issue_type="task", feature_slug="feat-x", root=root)
    claim(stale_issue.id, actor="worker-a", root=root)
    fresh_issue = create("fresh", issue_type="task", feature_slug="feat-x", root=root)
    claim(fresh_issue.id, actor="worker-b", root=root)

    db_path = root / ".cnogo" / "memory.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE issues SET updated_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00Z", stale_issue.id),
        )
        conn.commit()
    finally:
        conn.close()

    stale = stalled_tasks(feature_slug="feat-x", stale_minutes=10, root=root)
    ids = [item["id"] for item in stale]
    assert stale_issue.id in ids
    assert fresh_issue.id not in ids


def test_stalled_tasks_excludes_done_by_worker(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("done but stale", issue_type="task", feature_slug="feat-x", root=root)
    claim(issue.id, actor="worker-a", root=root)
    report_done(issue.id, actor="worker-a", root=root)

    db_path = root / ".cnogo" / "memory.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE issues SET updated_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00Z", issue.id),
        )
        conn.commit()
    finally:
        conn.close()

    stale = stalled_tasks(feature_slug="feat-x", stale_minutes=10, root=root)
    ids = [item["id"] for item in stale]
    assert issue.id not in ids


def test_release_requires_leader_role(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("release role", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    with pytest.raises(ValueError, match="Only leader can release"):
        release(issue.id, actor="worker-a", actor_role="worker", root=root)


def test_release_rejects_done_by_worker_state(tmp_path):
    root = tmp_path
    init(root)
    _write_workflow(root)

    issue = create("release done state", issue_type="task", root=root)
    claim(issue.id, actor="worker-a", root=root)
    report_done(issue.id, actor="worker-a", root=root)
    with pytest.raises(ValueError, match="active execution state"):
        release(issue.id, actor="leader", actor_role="leader", root=root)
