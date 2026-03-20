"""Tests for workflow doctor diagnostics."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_doctor_uses_repo_validator_entrypoint(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if args[:2] == [sys.executable, ".cnogo/scripts/workflow_validate.py"]:
            return SimpleNamespace(returncode=0, stdout="[]", stderr="")
        if args[:3] == ["git", "worktree", "list"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError(f"Unexpected subprocess.run call: {args!r}")

    def fake_run_shell(cmd, cwd, timeout_sec=10):
        if cmd == "git symbolic-ref HEAD":
            return 0, "refs/heads/main\n"
        return 0, ""

    monkeypatch.setattr(checks.subprocess, "run", fake_run)
    monkeypatch.setattr(checks, "run_shell", fake_run_shell)
    monkeypatch.setattr("scripts.memory.watchdog.check_stale_issues", lambda root: [])

    rc = checks._cmd_doctor(tmp_path, {}, json_output=True)

    assert rc == 0
    assert calls
    assert calls[0][0] == [sys.executable, ".cnogo/scripts/workflow_validate.py", "--json"]

