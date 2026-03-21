"""Tests for worker-branch enforcement in workflow_hooks.pre_bash."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".cnogo" / "scripts"))

import workflow_hooks as hooks


def _init_repo(root: Path, branch: str) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)
    (root / "README.md").write_text("demo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "bootstrap"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "checkout", "-b", branch], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_pre_bash_blocks_repo_authority_commands_on_agent_branches(tmp_path):
    _init_repo(tmp_path, "agent/demo-01-task-0")
    with mock.patch.object(hooks, "repo_root", return_value=tmp_path), mock.patch.object(hooks, "load_workflow", return_value={}):
        with mock.patch.dict(os.environ, {"CLAUDE_TOOL_INPUT": '{"command":"git commit -m \\"test\\""}'}):
            assert hooks.pre_bash() == 2


def test_pre_bash_allows_repo_authority_commands_on_feature_branches(tmp_path):
    _init_repo(tmp_path, "feature/demo")
    with mock.patch.object(hooks, "repo_root", return_value=tmp_path), mock.patch.object(hooks, "load_workflow", return_value={}):
        with mock.patch.dict(os.environ, {"CLAUDE_TOOL_INPUT": '{"command":"git commit -m \\"test\\""}'}):
            assert hooks.pre_bash() == 0


def test_pre_bash_allows_non_authority_commands_on_agent_branches(tmp_path):
    _init_repo(tmp_path, "agent/demo-01-task-0")
    with mock.patch.object(hooks, "repo_root", return_value=tmp_path), mock.patch.object(hooks, "load_workflow", return_value={}):
        with mock.patch.dict(os.environ, {"CLAUDE_TOOL_INPUT": '{"command":"git status --short"}'}):
            assert hooks.pre_bash() == 0
