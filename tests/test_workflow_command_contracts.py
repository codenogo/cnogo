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


def test_plan_and_implement_commands_enforce_stricter_execution_contracts():
    plan = _read(".claude/commands/plan.md")
    implement = _read(".claude/commands/implement.md")
    team = _read(".claude/commands/team.md")
    resume = _read(".claude/commands/resume.md")

    assert "Each task needs `name`" in plan
    assert "`contextLinks[]`" in plan
    assert "explicit error-path scenario" in plan
    assert "[--serial]" in implement
    assert "recommend_team_mode(taskdescs)" in implement
    assert "Delivery Run" in implement
    assert ".cnogo/runs/<feature>/<run-id>.json" in implement
    assert "workflow_memory.py run-create <feature-slug> <NN>" in implement
    assert "workflow_memory.py run-plan-verify <feature-slug> pass" in implement
    assert "workflow_memory.py run-task-set <feature-slug> <task-index> in_progress" in implement
    assert "workflow_memory.py run-task-set <feature-slug> <task-index> done" in implement
    assert "integration` plus `reviewReadiness`" in implement
    assert "auto-appended package `lint` / `typecheck` / `test` commands" in implement
    assert "workflow_checks.py summarize --feature <feature-slug> --plan <NN>" in implement
    assert "Delivery Run" in team
    assert "same `run_id`" in team
    assert "workflow_memory.py run-create <feature> <NN> --mode team --run-id <run-id>" in team
    assert "workflow_memory.py run-sync-session <feature> --run-id <run-id> --json" in team
    assert "run-plan-verify <feature> pass|fail" in team
    assert "Delivery Run state, Integration state, Review readiness" in team
    assert "session-status --json" in resume
    assert "status`, `integration`, and `reviewReadiness`" in resume


def test_review_command_uses_pending_final_verdict_and_reviewer_agents():
    review = _read(".claude/commands/review.md")
    spawn = _read(".claude/commands/spawn.md")
    workflow = _read("docs/planning/WORKFLOW.json")
    code_reviewer = _read(".claude/agents/code-reviewer.md")
    security_scanner = _read(".claude/agents/security-scanner.md")
    perf_analyzer = _read(".claude/agents/perf-analyzer.md")

    assert "automatedVerdict" in review
    assert "verdict: pending" in review
    assert "always spawn" in review
    assert "REVIEW.json.reviewers[]" in review
    assert "reviewReadiness.status == ready" in review
    assert "workflow_memory.py run-show <feature-slug> --json" in review
    assert "auto-syncs the linked Delivery Run" in review
    assert "workflow_memory.py run-review-sync <feature-slug>" in review
    assert "code-reviewer" in review
    assert "security-scanner" in review
    assert "perf-analyzer" in review
    assert "`code-reviewer` -> `.claude/agents/code-reviewer.md` + `.claude/skills/code-review.md`" in spawn
    assert "`security-scanner` -> `.claude/agents/security-scanner.md` + `.claude/skills/security-scan.md`" in spawn
    assert "`perf-analyzer` -> `.claude/agents/perf-analyzer.md` + `.claude/skills/performance-review.md`" in spawn
    assert '"review": ["code-reviewer", "security-scanner", "perf-analyzer"]' in workflow
    assert "correctness and contract reviewer" in code_reviewer
    assert "security reviewer" in security_scanner
    assert "performance and reliability reviewer" in perf_analyzer
