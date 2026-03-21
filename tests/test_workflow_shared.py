"""Tests for shared workflow refactor helpers."""

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.workflow.shared.artifacts import age_days, artifact_time, linked_artifact_time
from scripts.workflow.shared.config import (
    DEFAULT_BOOTSTRAP_CONTEXT,
    DEFAULT_SCHEDULER_SETTINGS,
    DEFAULT_TOKEN_BUDGETS,
    DEFAULT_WATCH_SETTINGS,
    bootstrap_context_cfg,
    scheduler_settings_cfg,
    token_budgets_cfg,
    watch_settings_cfg,
    workflow_packages,
)
from scripts.workflow.shared.git import is_git_repo, repo_root, staged_files
from scripts.workflow.shared.packages import infer_task_package
from scripts.workflow.shared.plans import normalize_plan_number


def test_workflow_packages_sort_longest_path_first():
    cfg = {
        "packages": [
            {"name": "root", "path": "."},
            {"name": "api", "path": "services/api"},
            {"name": "svc", "path": "services"},
        ]
    }
    packages = workflow_packages(cfg)
    assert [pkg["path"] for pkg in packages] == ["services/api", "services", "."]


def test_infer_task_package_prefers_explicit_cwd():
    packages = [
        {"name": "root", "path": "."},
        {"name": "api", "path": "services/api"},
    ]
    assert infer_task_package(["cmd/api/main.go"], packages, cwd="services/api") == "services/api"


def test_normalize_plan_number_zero_pads_numeric_values():
    assert normalize_plan_number(1) == "01"
    assert normalize_plan_number("1") == "01"
    assert normalize_plan_number("12") == "12"


def test_token_budgets_cfg_preserves_defaults_and_overrides():
    cfg = {
        "performance": {
            "tokenBudgets": {
                "enabled": False,
                "summaryWordMax": 777,
            }
        }
    }
    result = token_budgets_cfg(cfg)
    assert result["enabled"] is False
    assert result["summaryWordMax"] == 777
    assert result["planWordMax"] == DEFAULT_TOKEN_BUDGETS["planWordMax"]


def test_bootstrap_context_cfg_preserves_defaults_and_overrides():
    cfg = {
        "performance": {
            "bootstrapContext": {
                "enabled": False,
                "commandSetWordMax": 9000,
            }
        }
    }
    result = bootstrap_context_cfg(cfg)
    assert result["enabled"] is False
    assert result["commandSetWordMax"] == 9000
    assert result["rootClaudeWordMax"] == DEFAULT_BOOTSTRAP_CONTEXT["rootClaudeWordMax"]


def test_watch_settings_cfg_preserves_defaults_and_overrides():
    cfg = {
        "watch": {
            "enabled": False,
            "patrolIntervalMinutes": 20,
        }
    }
    result = watch_settings_cfg(cfg)
    assert result["enabled"] is False
    assert result["patrolIntervalMinutes"] == 20
    assert result["historyLimit"] == DEFAULT_WATCH_SETTINGS["historyLimit"]


def test_scheduler_settings_cfg_preserves_defaults_and_overrides():
    cfg = {
        "scheduler": {
            "enabled": False,
            "mode": "supervisor",
            "tickIntervalMinutes": 7,
            "opportunisticCommands": ["work-list"],
        }
    }
    result = scheduler_settings_cfg(cfg)
    assert result["enabled"] is False
    assert result["mode"] == "supervisor"
    assert result["tickIntervalMinutes"] == 7
    assert result["opportunisticCommands"] == ["work-list"]
    assert DEFAULT_SCHEDULER_SETTINGS["tickIntervalMinutes"] > 0


def test_artifact_helpers_prefer_contract_timestamp_and_track_age(tmp_path):
    artifact_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "demo"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = artifact_dir / "SHAPE.md"
    contract_path = artifact_dir / "SHAPE.json"
    markdown_path.write_text("# Shape\n", encoding="utf-8")
    timestamp = (
        datetime.now(timezone.utc) - timedelta(days=2)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contract_path.write_text(json.dumps({"timestamp": timestamp}), encoding="utf-8")

    load_json = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))

    resolved_time = artifact_time(markdown_path, contract_path, load_json=load_json)
    linked_time = linked_artifact_time(tmp_path, "docs/planning/work/ideas/demo/SHAPE.json", load_json=load_json)

    assert resolved_time is not None
    assert linked_time == resolved_time
    assert age_days(resolved_time) >= 2


def test_git_helpers_detect_repo_root_and_staged_files(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True, capture_output=True)

    assert is_git_repo(tmp_path) is True
    assert repo_root(tmp_path) == tmp_path.resolve()
    assert staged_files(tmp_path) == [tracked]
