"""Tests for scripts/hook-subagent-stop.py observer-mode validation."""

import importlib.util
import io
import json
import sys
from pathlib import Path


def _load_hook_module():
    root = Path(__file__).resolve().parent.parent
    script_path = root / "scripts" / "hook-subagent-stop.py"
    spec = importlib.util.spec_from_file_location("hook_subagent_stop", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_task_evidence_valid_json():
    mod = _load_hook_module()
    msg = (
        "done\n"
        'TASK_EVIDENCE: {"verification":{"commands":["pytest -q"],"timestamp":"2026-02-25T00:00:00Z"},'
        '"tdd":{"required":true,"failingVerify":["pytest -q"],"passingVerify":["pytest -q"]}}\n'
        "TASK_DONE: [cn-abc]\n"
    )
    evidence = mod._extract_task_evidence(msg)
    assert isinstance(evidence, dict)
    assert evidence["verification"]["commands"] == ["pytest -q"]


def test_extract_task_evidence_malformed_json_returns_none(capsys):
    mod = _load_hook_module()
    msg = "TASK_EVIDENCE: {not-json}\nTASK_DONE: [cn-abc]\n"
    evidence = mod._extract_task_evidence(msg)
    assert evidence is None
    assert "malformed TASK_EVIDENCE JSON" in capsys.readouterr().err


def test_main_observer_mode_reports_done_ids(monkeypatch, capsys):
    mod = _load_hook_module()
    payload = {
        "last_assistant_message": (
            "result\n"
            'TASK_EVIDENCE: {"verification":{"commands":["pytest -q"],"timestamp":"2026-02-25T00:00:00Z"}}\n'
            "TASK_DONE: [cn-a, cn-b]"
        )
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = mod.main()
    assert rc == 0
    err = capsys.readouterr().err
    assert "observed TASK_DONE for: cn-a, cn-b" in err
    assert "_report_done" not in dir(mod)


def test_main_warns_on_duplicate_ids_and_missing_evidence(monkeypatch, capsys):
    mod = _load_hook_module()
    payload = {
        "last_assistant_message": "TASK_DONE: [cn-a, cn-a]"
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = mod.main()
    assert rc == 0
    err = capsys.readouterr().err
    assert "duplicate TASK_DONE ids detected" in err
    assert "missing or malformed TASK_EVIDENCE payload" in err
