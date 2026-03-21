"""CLI tests for initiative-show and initiative-list subcommands on workflow_memory.py."""

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


def _write_shape(root: Path, slug: str, initiative: str = "Test Initiative", candidates: list | None = None) -> Path:
    ideas_dir = root / "docs" / "planning" / "work" / "ideas" / slug
    ideas_dir.mkdir(parents=True, exist_ok=True)
    shape_path = ideas_dir / "SHAPE.json"
    shape_data = {
        "initiative": initiative,
        "slug": slug,
        "candidateFeatures": candidates or [],
    }
    shape_path.write_text(json.dumps(shape_data, indent=2) + "\n", encoding="utf-8")
    return shape_path


def test_initiative_list_json_returns_empty_list_when_no_ideas(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    result = _run_cli("initiative-list", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    initiatives = json.loads(result.stdout)
    assert isinstance(initiatives, list)
    assert initiatives == []


def test_initiative_list_json_returns_shape_entries(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_shape(tmp_path, "alpha-initiative", initiative="Alpha Initiative", candidates=[{"slug": "feat-a", "displayName": "Feature A"}])
    _write_shape(tmp_path, "beta-initiative", initiative="Beta Initiative", candidates=[])

    result = _run_cli("initiative-list", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    initiatives = json.loads(result.stdout)
    assert isinstance(initiatives, list)
    assert len(initiatives) == 2
    slugs = [i["slug"] for i in initiatives]
    assert "alpha-initiative" in slugs
    assert "beta-initiative" in slugs
    alpha = next(i for i in initiatives if i["slug"] == "alpha-initiative")
    assert alpha["initiative"] == "Alpha Initiative"
    assert alpha["candidateCount"] == 1


def test_initiative_list_table_output(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_shape(tmp_path, "my-initiative", initiative="My Initiative")
    result = _run_cli("initiative-list", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "my-initiative" in result.stdout
    assert "My Initiative" in result.stdout


def test_initiative_list_empty_table_output(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    result = _run_cli("initiative-list", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "No initiatives found." in result.stdout


def test_initiative_show_json_returns_rollup_for_valid_shape(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_shape(
        tmp_path,
        "context-graph",
        initiative="Context Graph",
        candidates=[
            {"slug": "graph-core", "displayName": "Graph Core", "status": "draft"},
            {"slug": "graph-query", "displayName": "Graph Query", "status": "draft"},
        ],
    )

    result = _run_cli("initiative-show", "context-graph", "--json", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    rollup = json.loads(result.stdout)
    assert rollup["initiative"] == "Context Graph"
    assert rollup["slug"] == "context-graph"
    assert "totalFeatures" in rollup
    assert rollup["totalFeatures"] == 2
    assert "completedFeatures" in rollup
    assert "features" in rollup
    assert "nextAction" in rollup
    assert "timestamp" in rollup


def test_initiative_show_nonexistent_returns_exit_code_1(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    result = _run_cli("initiative-show", "nonexistent-slug", cwd=tmp_path)
    assert result.returncode == 1
    assert "nonexistent-slug" in result.stderr


def test_initiative_show_table_output(tmp_path):
    assert _run_cli("init", cwd=tmp_path).returncode == 0
    _write_shape(
        tmp_path,
        "demo-initiative",
        initiative="Demo Initiative",
        candidates=[{"slug": "feat-one", "displayName": "Feat One", "status": "draft"}],
    )
    result = _run_cli("initiative-show", "demo-initiative", cwd=tmp_path)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Demo Initiative" in result.stdout
    assert "feat-one" in result.stdout
