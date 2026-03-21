"""Focused tests for workflow_checks_core invariants helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_run_invariant_checks_reports_todo_and_bare_except(tmp_path):
    source = tmp_path / "app.py"
    source.write_text(
        "\n".join(
            [
                "# TODO fix this path",
                "try:",
                "    pass",
                "except:",
                "    pass",
            ]
        ),
        encoding="utf-8",
    )

    findings = checks.run_invariant_checks(
        tmp_path,
        {
            "invariants": {
                "scanScope": "repo",
                "pythonBareExcept": "fail",
            }
        },
    )

    rules = {finding.rule for finding in findings}
    assert "todo-requires-ticket" in rules
    assert "python-bare-except" in rules


def test_changed_relpaths_uses_head_fallback_when_tree_is_clean(monkeypatch, tmp_path):
    def fake_run_shell(cmd, cwd, *, timeout_sec=30):
        del cwd, timeout_sec
        if "git show --name-only" in cmd:
            return 0, "docs/planning/PROJECT.md\n"
        return 0, ""

    monkeypatch.setattr(checks, "run_shell", fake_run_shell)

    changed = checks._changed_relpaths(tmp_path, fallback="head")

    assert changed == {"docs/planning/PROJECT.md"}
