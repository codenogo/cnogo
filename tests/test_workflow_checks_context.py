"""Focused tests for workflow checks context inference helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


def test_infer_feature_from_state_falls_back_to_branch_for_non_repo_root(tmp_path, monkeypatch):
    monkeypatch.setattr(checks, "git_branch", lambda root: "feature/demo-slice")

    inferred = checks.infer_feature_from_state(tmp_path)

    assert inferred == "demo-slice"
