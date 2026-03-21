"""Focused tests for workflow_checks_core configuration helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_invariants_cfg_normalizes_exceptions_and_forbidden_patterns():
    cfg = checks._invariants_cfg(
        {
            "invariants": {
                "enabled": False,
                "scanScope": "repo",
                "maxFileLines": 1200,
                "maxFileLinesExceptions": [" docs/generated.py ", "", 123],
                "todoRequiresTicket": False,
                "pythonBareExcept": "fail",
                "forbiddenImportPatterns": [
                    {
                        "pattern": "import *",
                        "mode": "substring",
                        "severity": "fail",
                        "message": "Avoid star imports.",
                    },
                    {
                        "pattern": "^from bad import .*$",
                        "mode": "regex",
                    },
                    {"pattern": ""},
                ],
            }
        }
    )

    assert cfg["enabled"] is False
    assert cfg["scanScope"] == "repo"
    assert cfg["maxFileLines"] == 1200
    assert cfg["maxFileLinesExceptions"] == ["docs/generated.py"]
    assert cfg["todoRequiresTicket"] is False
    assert cfg["pythonBareExcept"] == "fail"
    assert cfg["forbiddenImportPatterns"][0]["severity"] == "fail"
    assert cfg["forbiddenImportPatterns"][1]["mode"] == "regex"


def test_checks_runtime_cfg_applies_valid_overrides_and_ignores_invalid_values():
    cfg = checks._checks_runtime_cfg(
        {
            "performance": {
                "checkScope": "changed",
                "changedFilesFallback": "head",
                "commandTimeoutSec": 45,
                "outputCompaction": {
                    "enabled": False,
                    "maxLines": 50,
                    "failTailLines": -1,
                    "passLines": 10,
                    "dedupe": False,
                },
                "outputRecovery": {
                    "enabled": True,
                    "mode": "always",
                    "minChars": 250,
                    "maxFiles": 4,
                    "maxFileSize": 4096,
                    "directory": "tmp/tee",
                },
                "tokenTelemetry": {"enabled": False},
                "hookOptimization": {
                    "enabled": True,
                    "mode": "enforce",
                    "showSuggestions": False,
                    "logFile": "tmp/usage.jsonl",
                },
            }
        }
    )

    assert cfg["checkScope"] == "changed"
    assert cfg["changedFilesFallback"] == "head"
    assert cfg["commandTimeoutSec"] == 45
    assert cfg["outputCompaction"]["enabled"] is False
    assert cfg["outputCompaction"]["maxLines"] == 50
    assert cfg["outputCompaction"]["failTailLines"] == checks.DEFAULT_OUTPUT_COMPACT_FAIL_TAIL_LINES
    assert cfg["outputCompaction"]["passLines"] == 10
    assert cfg["outputCompaction"]["dedupe"] is False
    assert cfg["outputRecovery"]["mode"] == "always"
    assert cfg["outputRecovery"]["directory"] == "tmp/tee"
    assert cfg["tokenTelemetry"]["enabled"] is False
    assert cfg["hookOptimization"]["mode"] == "enforce"
    assert cfg["hookOptimization"]["showSuggestions"] is False
