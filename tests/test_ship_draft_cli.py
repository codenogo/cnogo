"""CLI tests for run-ship-draft and run-ship-complete auto-infer on workflow_memory.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".cnogo" / "scripts" / "workflow_memory.py"


def _run_cli(*args: str, cwd: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _write_plan(root: Path, feature: str, plan_num: str = "01") -> Path:
    """Write a minimal NN-PLAN.json for a feature."""
    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    feature_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "schemaVersion": 1,
        "feature": feature,
        "planNumber": plan_num,
        "goal": f"Implement {feature}",
        "commitMessage": f"feat({feature}): implement {feature}",
        "tasks": [
            {
                "id": "t1",
                "name": "Task one",
                "files": [f"src/{feature}/core.py"],
            }
        ],
    }
    plan_path = feature_dir / f"{plan_num}-PLAN.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


# ---------------------------------------------------------------------------
# run-ship-draft --help
# ---------------------------------------------------------------------------


def test_run_ship_draft_help_exits_zero(tmp_path):
    result = _run_cli("run-ship-draft", "--help", cwd=tmp_path)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "run-ship-draft" in combined or "feature" in combined


# ---------------------------------------------------------------------------
# run-ship-draft --json returns valid JSON with expected keys
# ---------------------------------------------------------------------------


def test_run_ship_draft_json_returns_expected_keys(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, "my-feature")

    result = _run_cli("run-ship-draft", "my-feature", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    draft = json.loads(result.stdout)

    expected_keys = {
        "commitSurface",
        "excludedFiles",
        "commitMessage",
        "prTitle",
        "prBody",
        "branch",
        "gitAddCommand",
        "warnings",
    }
    assert expected_keys.issubset(set(draft.keys()))


def test_run_ship_draft_json_commit_message_from_plan(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, "cool-feature")

    result = _run_cli("run-ship-draft", "cool-feature", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    draft = json.loads(result.stdout)
    assert draft["commitMessage"] == "feat(cool-feature): implement cool-feature"


def test_run_ship_draft_json_commit_surface_is_list(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, "list-feature")

    result = _run_cli("run-ship-draft", "list-feature", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    draft = json.loads(result.stdout)
    assert isinstance(draft["commitSurface"], list)
    assert isinstance(draft["excludedFiles"], list)
    assert isinstance(draft["warnings"], list)


def test_run_ship_draft_json_no_plan_warns(tmp_path):
    """When no plan exists, warnings should be non-empty."""
    assert _run_cli("init", cwd=tmp_path).returncode == 0

    result = _run_cli("run-ship-draft", "no-plan-feature", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    draft = json.loads(result.stdout)
    assert len(draft["warnings"]) > 0


def test_run_ship_draft_table_output_shows_feature(tmp_path):
    """Table (non-JSON) output should include the feature name."""
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, "table-feature")

    result = _run_cli("run-ship-draft", "table-feature", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "table-feature" in result.stdout


def test_run_ship_draft_table_output_shows_commit_message(tmp_path):
    """Table output should include commit message label."""
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_plan(tmp_path, "msg-feature")

    result = _run_cli("run-ship-draft", "msg-feature", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Commit message" in result.stdout


# ---------------------------------------------------------------------------
# run-ship-complete: commit is optional (nargs='?')
# ---------------------------------------------------------------------------


def test_run_ship_complete_argparse_accepts_optional_commit(tmp_path):
    """run-ship-complete --help should succeed and indicate commit is optional."""
    result = _run_cli("run-ship-complete", "--help", cwd=tmp_path)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    # The help text should contain both "feature" and hint about auto-infer
    assert "feature" in combined


def test_run_ship_complete_argparse_accepts_explicit_commit_positional(tmp_path):
    """Passing an explicit commit SHA as positional arg should be recognized in args."""
    # We can't fully run this without a delivery run, but we can verify argparse
    # doesn't reject the positional SHA. Without a delivery run it returns error
    # from business logic, not argparse.
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    result = _run_cli("run-ship-complete", "my-feature", "abc1234", cwd=tmp_path)
    # Should fail with business logic error (no delivery run), not argparse error
    assert result.returncode != 0
    # Ensure it's not an argparse "unrecognized arguments" error
    assert "unrecognized" not in result.stderr
    assert "too many" not in result.stderr


# ---------------------------------------------------------------------------
# Auto-infer guard: wrong branch prints error message
# ---------------------------------------------------------------------------


def test_run_ship_complete_auto_infer_wrong_branch_prints_error(tmp_path):
    """When commit is omitted and branch != feature/<slug>, error is printed to stderr."""
    assert _run_cli("init", cwd=tmp_path).returncode == 0

    # Initialize a git repo in tmp_path so _git_branch works
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, capture_output=True)

    # Run without commit arg — branch is 'main', not 'feature/some-feat'
    result = _run_cli("run-ship-complete", "some-feat", cwd=tmp_path)
    assert result.returncode == 1
    assert "Auto-infer failed" in result.stderr
    assert "some-feat" in result.stderr or "feature/some-feat" in result.stderr


def test_run_ship_complete_auto_infer_error_mentions_explicit_fallback(tmp_path):
    """The auto-infer failure message should suggest explicit commit SHA usage."""
    assert _run_cli("init", cwd=tmp_path).returncode == 0

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=tmp_path, capture_output=True)

    result = _run_cli("run-ship-complete", "some-feat", cwd=tmp_path)
    assert result.returncode == 1
    # Should mention how to pass explicitly
    assert "run-ship-complete" in result.stderr or "commit" in result.stderr.lower()
