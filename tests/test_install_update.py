"""Integration tests for install.sh update behavior."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install.sh"


def _run_install(*args, cwd=ROOT):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_update_adds_new_managed_files_missing_from_older_manifest(tmp_path):
    target = tmp_path / "project"
    target.mkdir()

    install = _run_install("-y", "--skip-graph", str(target))
    assert install.returncode == 0, install.stderr + install.stdout

    missing_paths = {
        ".claude/commands/shape.md",
        ".claude/skills/shape-facilitator/SKILL.md",
        ".cnogo/formulas/feature-delivery.json",
        ".cnogo/scripts/memory/runtime.py",
        ".cnogo/scripts/workflow/shared/config.py",
        ".cnogo/scripts/workflow/shared/formulas.py",
        ".cnogo/scripts/workflow/orchestration/delivery_run.py",
        ".cnogo/scripts/workflow/orchestration/integration.py",
        ".cnogo/scripts/workflow/orchestration/ship.py",
        ".cnogo/scripts/workflow/orchestration/watch.py",
        ".cnogo/scripts/workflow/orchestration/watch_artifacts.py",
    }

    manifest_path = target / ".cnogo" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [entry for entry in manifest["files"] if entry["path"] not in missing_paths]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for rel_path in missing_paths:
        file_path = target / rel_path
        if file_path.exists():
            file_path.unlink()

    update = _run_install("--update", "--skip-graph", "--from", str(ROOT), str(target))
    assert update.returncode == 0, update.stderr + update.stdout

    for rel_path in missing_paths:
        assert (target / rel_path).is_file(), rel_path

    updated_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    updated_paths = {entry["path"] for entry in updated_manifest["files"]}
    assert missing_paths.issubset(updated_paths)
