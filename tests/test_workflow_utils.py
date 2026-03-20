"""Tests for workflow utility helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_utils as utils


def test_discover_skills_supports_flat_and_directory_formats(tmp_path):
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "flat-skill.md").write_text(
        "---\nname: flat-skill\nappliesTo: [review]\n---\n# Flat\n",
        encoding="utf-8",
    )
    nested_dir = skills_dir / "shape-facilitator"
    nested_dir.mkdir(parents=True, exist_ok=True)
    (nested_dir / "SKILL.md").write_text(
        "---\nname: shape-facilitator\nappliesTo: [shape]\n---\n# Shape\n",
        encoding="utf-8",
    )

    discovered = utils.discover_skills(skills_dir)
    names = {entry["name"] for entry in discovered}
    paths = {Path(entry["path"]).name for entry in discovered}

    assert names == {"flat-skill", "shape-facilitator"}
    assert "flat-skill.md" in paths
    assert "SKILL.md" in paths
