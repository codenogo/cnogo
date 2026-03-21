"""Focused tests for workflow_checks_core package-check helpers."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_run_package_checks_scopes_to_changed_packages_and_repo_root(monkeypatch, tmp_path):
    (tmp_path / "apps" / "web").mkdir(parents=True, exist_ok=True)
    (tmp_path / "libs" / "shared").mkdir(parents=True, exist_ok=True)

    calls = []

    def fake_run_shell(cmd, cwd, *, timeout_sec=300):
        del timeout_sec
        calls.append((cmd, cwd))
        return 0, "ok"

    monkeypatch.setattr(checks, "run_shell", fake_run_shell)

    results = checks.run_package_checks(
        tmp_path,
        [
            {
                "name": "web",
                "path": "apps/web",
                "kind": "node",
                "commands": {"test": "python -m pytest apps/web/tests"},
            },
            {
                "name": "shared",
                "path": "libs/shared",
                "kind": "node",
                "commands": {"test": "npm test"},
            },
        ],
        changed_relpaths={"apps/web/src/index.ts"},
        token_telemetry_enabled=False,
    )

    web_test = next(check for check in results[0]["checks"] if check["name"] == "test")
    shared_test = next(check for check in results[1]["checks"] if check["name"] == "test")

    assert web_test["result"] == "pass"
    assert web_test["cwd"] == "."
    assert shared_test["result"] == "skipped"
    assert shared_test["reason"] == "no changed files for package"
    assert calls[0][0] == "python -m pytest apps/web/tests"
    assert calls[0][1] == tmp_path


def test_write_verify_ci_writes_contract_and_markdown(tmp_path):
    per_pkg = [
        {
            "name": "web",
            "path": "apps/web",
            "kind": "node",
            "checks": [
                {
                    "name": "lint",
                    "result": "pass",
                    "cmd": "npm test",
                    "cwd": ".",
                    "tokenTelemetry": {
                        "inputTokens": 10,
                        "outputTokens": 4,
                        "savedTokens": 6,
                        "savingsPct": 60.0,
                    },
                },
                {"name": "typecheck", "result": "skipped", "cmd": None},
                {"name": "test", "result": "pass", "cmd": "npm test", "cwd": "."},
            ],
        }
    ]
    findings = [
        checks.InvariantFinding(
            rule="python-bare-except",
            severity="fail",
            file="app.py",
            line=4,
            message="Bare except detected",
        )
    ]

    rc = checks.write_verify_ci(tmp_path, "demo", per_pkg, findings)

    contract_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "VERIFICATION-CI.json"
    markdown_path = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "VERIFICATION-CI.md"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    rendered = markdown_path.read_text(encoding="utf-8")

    assert rc == 1
    assert contract["invariants"]["summary"]["fail"] == 1
    assert contract["checks"][0]["name"] == "lint"
    assert "## Invariant Findings" in rendered
    assert "Bare except detected" in rendered
