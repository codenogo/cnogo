"""Tests for workspace-first shape command and skill contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_shape_command_is_workspace_first():
    text = _read(".claude/commands/shape.md")

    assert "available exit from shape" in text
    assert "stay-in-shape continuation moves first" in text
    assert "exact next commands for every ready feature" not in text


def test_discuss_command_records_shape_feedback_without_mutating_shape():
    text = _read(".claude/commands/discuss.md")

    assert "shapeFeedback[]" in text
    assert "instead of editing `SHAPE.json`" in text


def test_workspace_skills_and_brainstorm_alias_match_new_model():
    facilitator = _read(".claude/skills/shape-facilitator/SKILL.md")
    brainstorm = _read(".claude/commands/brainstorm.md")

    assert "available exit, not a stop signal" in facilitator
    assert "same workspace-first output contract as `/shape`" in brainstorm


def test_research_command_and_spawn_use_research_skill():
    research = _read(".claude/commands/research.md")
    spawn = _read(".claude/commands/spawn.md")
    skill = _read(".claude/skills/research-evidence-synthesis/SKILL.md")

    assert ".claude/skills/research-evidence-synthesis/SKILL.md" in research
    assert "`research` -> `.claude/skills/research-evidence-synthesis/SKILL.md`" in spawn
    assert "evidence, inference, and recommendation" in skill


def test_shape_workspace_supports_dedicated_read_only_scouts():
    shape = _read(".claude/commands/shape.md")
    spawn = _read(".claude/commands/spawn.md")
    risk_skill = _read(".claude/skills/shape-risk-challenge/SKILL.md")

    assert "`shape-scout`" in shape
    assert "`architecture-scout`" in shape
    assert "`risk-challenger`" in shape
    assert "SCOUT_REPORT" in shape
    assert "never use `/team` inside `/shape`" in shape
    assert "`shape-scout` -> `.claude/agents/shape-scout.md`" in spawn
    assert "`architecture-scout` -> `.claude/agents/architecture-scout.md`" in spawn
    assert "`risk-challenger` -> `.claude/agents/risk-challenger.md`" in spawn
    assert ".claude/skills/shape-facilitator/SKILL.md" not in spawn.split("`shape-scout` ->", 1)[1].splitlines()[0]
    assert "/spawn research <task>" not in shape
    assert "discuss-ready features that should regress to `draft` or `blocked`" in risk_skill
