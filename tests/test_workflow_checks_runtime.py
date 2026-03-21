"""Focused tests for workflow_checks_core runtime/output helpers."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_compact_check_output_focuses_failed_test_output():
    output = "\n".join(
        [
            "collected 2 items",
            "tests/test_demo.py F.",
            "=================================== FAILURES ===================================",
            "_______________________________ test_demo_fails _______________________________",
            "E   AssertionError: expected 1 == 2",
            "=========================== short test summary info ===========================",
            "FAILED tests/test_demo.py::test_demo_fails - AssertionError",
        ]
    )

    compact, reducer = checks.compact_check_output(
        "test",
        "pytest -q",
        output,
        rc=1,
        max_lines=20,
        fail_tail_lines=10,
        pass_lines=5,
        dedupe=True,
        enabled=True,
    )

    assert reducer == "failure-focus"
    assert "FAILURES:" in compact
    assert "SUMMARY:" in compact
    assert "AssertionError" in compact


def test_summarize_token_telemetry_aggregates_checks():
    summary = checks.summarize_token_telemetry(
        [
            {
                "checks": [
                    {
                        "result": "passed",
                        "tokenTelemetry": {
                            "inputTokens": 100,
                            "outputTokens": 40,
                            "savedTokens": 60,
                        },
                    },
                    {"result": "skipped"},
                ]
            },
            {
                "checks": [
                    {
                        "result": "failed",
                        "tokenTelemetry": {
                            "inputTokens": 50,
                            "outputTokens": 20,
                            "savedTokens": 30,
                        },
                    }
                ]
            },
        ]
    )

    assert summary["checksRun"] == 2
    assert summary["checksSkipped"] == 1
    assert summary["inputTokens"] == 150
    assert summary["outputTokens"] == 60
    assert summary["savedTokens"] == 90
    assert summary["savingsPct"] == 60.0


def test_discover_command_usage_groups_missed_and_unhandled(tmp_path):
    log_path = tmp_path / "telemetry.jsonl"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": checks.now_iso(),
                        "status": "optimized",
                        "command": "pytest -q",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": checks.now_iso(),
                        "status": "missed",
                        "category": "compaction",
                        "suggestion": "Use compact output",
                        "estimatedSaveableTokens": 120,
                        "command": "go test ./...",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": checks.now_iso(),
                        "status": "missed",
                        "category": "compaction",
                        "suggestion": "Use compact output",
                        "estimatedSaveableTokens": 80,
                        "command": "go test ./...",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": checks.now_iso(),
                        "status": "neutral",
                        "command": "python3 scripts/custom.py",
                    }
                ),
            ]),
        encoding="utf-8",
    )

    report = checks._discover_command_usage(
        tmp_path,
        log_file="telemetry.jsonl",
        since_days=30,
        limit=5,
    )

    assert report["commandsScanned"] == 4
    assert report["optimized"] == 1
    assert report["estimatedSaveableTokens"] == 200
    assert report["missed"][0]["count"] == 2
    assert report["missed"][0]["suggestion"] == "Use compact output"
    assert report["unhandled"][0]["command"] == "python3"
