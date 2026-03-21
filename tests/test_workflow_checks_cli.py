"""Focused tests for workflow checks CLI dispatch helpers."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.workflow.checks import cli as checks_cli


def test_run_command_discover_emits_json(capsys, tmp_path):
    args = argparse.Namespace(cmd="discover", since_days=7, limit=5, format="json")

    rc = checks_cli.run_command(
        args,
        root=tmp_path,
        default_command_timeout_sec=60,
        load_workflow=lambda root=None: {"packages": []},
        autobootstrap_packages_if_empty=lambda root, wf, cmd, timeout_sec: wf,
        checks_runtime_cfg=lambda wf: {},
        infer_feature_from_state=lambda root: None,
        discover_command_usage=lambda root, log_file, since_days, limit: {
            "rows": [{"cmd": "review", "count": 2}],
            "logFile": log_file,
            "sinceDays": since_days,
            "limit": limit,
        },
        print_discover_text=lambda report: None,
        cmd_doctor=lambda root, wf, json_output=False: 0,
        cmd_summarize=lambda *args, **kwargs: 0,
        cmd_ship_ready=lambda *args, **kwargs: 0,
        run_invariant_checks=lambda *args, **kwargs: [],
        entropy_cfg=lambda wf: {},
        summarize_invariants=lambda findings: {"fail": 0},
        entropy_candidates=lambda *args, **kwargs: [],
        write_entropy_task=lambda *args, **kwargs: tmp_path / "entropy.md",
        packages_from_workflow=lambda wf: [],
        changed_relpaths=lambda root, fallback="none": set(),
        changed_relpaths_against_base=lambda root: set(),
        run_package_checks=lambda *args, **kwargs: [],
        write_verify_ci=lambda root, feature, per_pkg, invariant_findings: 0,
        write_review=lambda root, feature, per_pkg, invariant_findings: 0,
    )

    assert rc == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["sinceDays"] == 7
    assert rendered["limit"] == 5


def test_run_command_review_uses_inferred_feature_when_flag_missing(tmp_path):
    args = argparse.Namespace(cmd="review", feature=None)
    captured: dict[str, object] = {}

    rc = checks_cli.run_command(
        args,
        root=tmp_path,
        default_command_timeout_sec=60,
        load_workflow=lambda root=None: {"packages": []},
        autobootstrap_packages_if_empty=lambda root, wf, cmd, timeout_sec: wf,
        checks_runtime_cfg=lambda wf: {},
        infer_feature_from_state=lambda root: "demo-slice",
        discover_command_usage=lambda *args, **kwargs: {},
        print_discover_text=lambda report: None,
        cmd_doctor=lambda root, wf, json_output=False: 0,
        cmd_summarize=lambda *args, **kwargs: 0,
        cmd_ship_ready=lambda *args, **kwargs: 0,
        run_invariant_checks=lambda *args, **kwargs: [],
        entropy_cfg=lambda wf: {"enabled": True},
        summarize_invariants=lambda findings: {"fail": 0},
        entropy_candidates=lambda *args, **kwargs: [],
        write_entropy_task=lambda *args, **kwargs: tmp_path / "entropy.md",
        packages_from_workflow=lambda wf: [],
        changed_relpaths=lambda root, fallback="none": set(),
        changed_relpaths_against_base=lambda root: set(),
        run_package_checks=lambda *args, **kwargs: [],
        write_verify_ci=lambda root, feature, per_pkg, invariant_findings: 0,
        write_review=lambda root, feature, per_pkg, invariant_findings: captured.update(
            {"feature": feature, "packages": per_pkg, "invariants": invariant_findings}
        )
        or 0,
    )

    assert rc == 0
    assert captured["feature"] == "demo-slice"
    assert captured["packages"] == []
    assert captured["invariants"] == []
