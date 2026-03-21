"""Tests for auto-generated feature summaries."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_checks_core as checks


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".cnogo" / "scripts" / "workflow_checks.py"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True)


def _write_plan(root: Path, *, memory_id: str | None = None) -> None:
    feature_dir = root / "docs" / "planning" / "work" / "features" / "demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        feature_dir / "01-PLAN.json",
        {
            "schemaVersion": 3,
            "feature": "demo",
            "planNumber": "01",
            "goal": "Implement the demo handler.",
            "tasks": [
                {
                    "name": "Add demo handler",
                    "memoryId": memory_id,
                    "files": ["app.py"],
                    "contextLinks": ["Constraint: keep the demo response deterministic"],
                    "microSteps": [
                        "write failure test for invalid demo response",
                        "implement deterministic handler",
                        "run tests",
                    ],
                    "action": "Update the demo handler behavior.",
                    "verify": ["pytest -q tests/test_demo.py"],
                    "tdd": {
                        "required": True,
                        "failingVerify": ["pytest -q tests/test_demo.py -k invalid"],
                        "passingVerify": ["pytest -q tests/test_demo.py -k invalid"],
                    },
                }
            ],
            "planVerify": ["pytest -q tests/test_demo.py"],
            "commitMessage": "feat(demo): implement handler",
            "timestamp": "2026-03-20T10:00:00Z",
        },
    )


def test_write_summary_uses_latest_commit_and_plan_contract(tmp_path):
    _init_repo(tmp_path)
    _write_plan(tmp_path)
    app = tmp_path / "app.py"
    app.write_text("print('before')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "chore: bootstrap"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    app.write_text("print('after')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: update demo"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    contract = checks.write_summary(tmp_path, "demo", "01", notes=["Generated automatically."])

    assert contract["schemaVersion"] == 2
    assert contract["outcome"] == "complete"
    assert contract["commit"]["message"] == "feat: update demo"
    assert contract["generatedFrom"]["taskEvidenceSource"] == "plan-contract"
    assert contract["generatedFrom"]["changedFilesSource"] == "git:HEAD"
    assert contract["changes"] == [{"file": "app.py", "change": "Add demo handler"}]
    assert any(entry.get("scope") == "task" and entry.get("source") == "plan-contract" for entry in contract["verification"])
    assert any(entry.get("scope") == "plan" for entry in contract["verification"])
    assert contract["notes"] == ["Generated automatically."]

    summary_md = tmp_path / "docs" / "planning" / "work" / "features" / "demo" / "01-SUMMARY.md"
    assert summary_md.exists()
    rendered = summary_md.read_text(encoding="utf-8")
    assert "## Generated From" in rendered
    assert "## Notes" in rendered


def test_write_summary_prefers_task_evidence_when_memory_outputs_exist(tmp_path, monkeypatch):
    _write_plan(tmp_path, memory_id="cn-123")
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "demo"

    monkeypatch.setattr(checks, "_summary_changed_files", lambda root: (["app.py"], "git:HEAD"))
    monkeypatch.setattr(checks, "_head_commit_metadata", lambda root: {"hash": "abc123", "message": "feat: demo"})
    monkeypatch.setattr(
        checks,
        "_load_memory_task_issues",
        lambda root, feature, plan_number: [
            SimpleNamespace(
                id="cn-123",
                title="Add demo handler",
                plan_number="01",
                state="done_by_worker",
                status="open",
                updated_at="2026-03-20T12:00:00Z",
                metadata={
                    "outputs": {
                        "verification": {
                            "commands": ["pytest -q tests/test_demo.py -k invalid"],
                            "timestamp": "2026-03-20T11:59:00Z",
                        }
                    }
                },
            )
        ],
    )

    contract = checks.write_summary(tmp_path, "demo", "01")

    assert contract["generatedFrom"]["taskEvidenceSource"] == "task-evidence"
    task_entry = contract["verification"][0]
    assert task_entry["scope"] == "task"
    assert task_entry["source"] == "task-evidence"
    assert task_entry["commands"] == ["pytest -q tests/test_demo.py -k invalid"]
    assert task_entry["timestamp"] == "2026-03-20T11:59:00Z"
    assert (feature_dir / "01-SUMMARY.json").exists()


def test_write_summary_prefers_working_tree_changes_over_last_commit(tmp_path):
    _init_repo(tmp_path)
    _write_plan(tmp_path)
    app = tmp_path / "app.py"
    old = tmp_path / "old.py"
    app.write_text("print('before')\n", encoding="utf-8")
    old.write_text("print('old-before')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "chore: bootstrap"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    old.write_text("print('old-after')\n", encoding="utf-8")
    subprocess.run(["git", "add", "old.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: update old"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    app.write_text("print('working-tree')\n", encoding="utf-8")

    contract = checks.write_summary(tmp_path, "demo", "01")

    assert contract["generatedFrom"]["changedFilesSource"] == "git:working-tree"
    assert contract["changes"] == [{"file": "app.py", "change": "Add demo handler"}]


def test_write_summary_filters_changes_to_plan_scope(tmp_path, monkeypatch):
    _write_plan(tmp_path)
    monkeypatch.setattr(
        checks,
        "_summary_changed_files",
        lambda root: (["app.py", ".cnogo/scripts/workflow/orchestration/ship_draft.py"], "git:working-tree"),
    )
    monkeypatch.setattr(checks, "_head_commit_metadata", lambda root: {"hash": "abc123", "message": "feat: demo"})

    contract = checks.write_summary(tmp_path, "demo", "01")

    assert contract["changes"] == [{"file": "app.py", "change": "Add demo handler"}]


def test_summarize_cli_accepts_positional_feature_and_plan(tmp_path):
    _init_repo(tmp_path)
    _write_plan(tmp_path)
    app = tmp_path / "app.py"
    app.write_text("print('before')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "chore: bootstrap"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    app.write_text("print('after')\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: update demo"], cwd=tmp_path, check=True, stdout=subprocess.DEVNULL)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "summarize", "demo", "01", "--json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    contract = json.loads(result.stdout)
    assert contract["generatedFrom"]["changedFilesSource"] == "git:HEAD"
