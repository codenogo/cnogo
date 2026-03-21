"""Focused tests for workflow_checks_core summary and entropy entrypoints."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_cmd_summarize_prints_json_contract(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        checks,
        "write_summary",
        lambda root, feature, plan_number, outcome="auto", notes=None: {
            "feature": feature,
            "planNumber": plan_number,
            "outcome": outcome,
            "notes": notes or [],
        },
    )

    rc = checks._cmd_summarize(
        tmp_path,
        "demo",
        "1",
        outcome="complete",
        notes=["auto"],
        json_output=True,
    )

    out = capsys.readouterr().out
    assert rc == 0
    rendered = json.loads(out)
    assert rendered["feature"] == "demo"
    assert rendered["planNumber"] == "1"
    assert rendered["outcome"] == "complete"


def test_write_entropy_task_writes_candidate_markdown(tmp_path):
    findings = [
        checks.InvariantFinding(
            rule="max-file-lines",
            severity="fail",
            file="app.py",
            line=1,
            message="too long",
        ),
        checks.InvariantFinding(
            rule="todo-requires-ticket",
            severity="warn",
            file="lib.py",
            line=2,
            message="missing ticket",
        ),
    ]

    task_path = checks.write_entropy_task(
        tmp_path,
        findings,
        max_files_per_task=1,
        max_tasks=2,
    )

    rendered = task_path.read_text(encoding="utf-8")
    assert task_path.exists()
    assert "Entropy cleanup #1" in rendered
    assert "`app.py`" in rendered


def test_autobootstrap_packages_if_empty_refreshes_workflow(monkeypatch, tmp_path, capsys):
    detect_script = tmp_path / ".cnogo" / "scripts" / "workflow_detect.py"
    detect_script.parent.mkdir(parents=True, exist_ok=True)
    detect_script.write_text("# stub\n", encoding="utf-8")

    refreshed = {
        "packages": [
            {
                "name": "demo",
                "path": "apps/demo",
                "kind": "node",
                "commands": {"test": "npm test"},
            }
        ]
    }

    monkeypatch.setattr(checks, "run_shell", lambda *args, **kwargs: (0, "ok"))
    monkeypatch.setattr(checks, "load_workflow", lambda root=None: refreshed)

    result = checks._autobootstrap_packages_if_empty(
        tmp_path,
        {"packages": []},
        cmd="review",
        timeout_sec=30,
    )

    assert result == refreshed
    assert "Detected 1 package(s)" in capsys.readouterr().out
