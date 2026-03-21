"""Focused tests for workflow validate CLI helpers."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.validate import cli as validate_cli


class _Finding:
    def __init__(self, level: str, message: str, path: str | None = None) -> None:
        self.level = level
        self.message = message
        self.path = path

    def format(self) -> str:
        loc = f" ({self.path})" if self.path else ""
        return f"[{self.level}]{loc} {self.message}"


def test_run_cli_emits_json_findings(capsys, tmp_path):
    args = argparse.Namespace(
        root=str(tmp_path),
        staged=False,
        feature=" demo ",
        json=True,
        save_baseline=False,
        diff_baseline=False,
    )

    rc = validate_cli.run_cli(
        args,
        repo_root=lambda path: path,
        validate_repo=lambda root, staged_only, feature_filter=None: [_Finding("WARN", "shape drift", "SHAPE.json")],
        finding_to_warning=lambda finding: {"level": finding.level, "message": finding.message, "file": finding.path},
        save_baseline=lambda warnings, root: root / ".baseline.json",
        load_baseline=lambda root: None,
        diff_baselines=lambda baseline, current: {"new": [], "resolved": [], "unchanged": []},
        save_latest=lambda warnings, root: None,
    )

    assert rc == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered == [{"level": "WARN", "message": "shape drift", "path": "SHAPE.json"}]


def test_run_cli_diff_baseline_requires_existing_file(capsys, tmp_path):
    args = argparse.Namespace(
        root=str(tmp_path),
        staged=False,
        feature=None,
        json=False,
        save_baseline=False,
        diff_baseline=True,
    )

    rc = validate_cli.run_cli(
        args,
        repo_root=lambda path: path,
        validate_repo=lambda root, staged_only, feature_filter=None: [],
        finding_to_warning=lambda finding: {},
        save_baseline=lambda warnings, root: root / ".baseline.json",
        load_baseline=lambda root: None,
        diff_baselines=lambda baseline, current: {"new": [], "resolved": [], "unchanged": []},
        save_latest=lambda warnings, root: None,
    )

    assert rc == 1
    assert "Run with --save-baseline first." in capsys.readouterr().out
