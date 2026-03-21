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
    status = _read(".claude/commands/status.md")

    assert "Each task needs `name`" in plan
    assert "Optional top-level `profile`" in plan
    assert "profile-list --json" in plan
    assert "profile-suggest $ARGUMENTS --plan <NN> --json" in plan
    assert "profile-init <profile-slug> --base feature-delivery" in plan
    assert "profile-stamp $ARGUMENTS <NN>" in plan
    assert "`contextLinks[]`" in plan
    assert "explicit error-path scenario" in plan
    assert "[--serial]" in implement
    assert "recommend_team_mode(taskdescs)" in implement
    assert "Resolve the plan profile" in implement
    assert "Delivery Run" in implement
    assert "work-show <feature-slug> --json" in implement
    assert ".cnogo/runs/<feature>/<run-id>.json" in implement
    assert "workflow_memory.py run-create <feature-slug> <NN>" in implement
    assert "workflow_memory.py run-next <feature-slug> --run-id <run-id> --json" in implement
    assert "returned `nextAction`" in implement
    assert "serial mode, `run-plan-verify` absorbs integration" in implement
    assert "workflow_memory.py run-plan-verify <feature-slug> pass" in implement
    assert "workflow_memory.py run-task-begin <feature-slug> <task-index>" in implement
    assert "workflow_memory.py run-task-complete <feature-slug> <task-index>" in implement
    assert "workflow_memory.py run-task-fail <feature-slug> <task-index>" in implement
    assert "integration` plus `reviewReadiness`" in implement
    assert "auto-appended package `lint` / `typecheck` / `test` commands" in implement
    assert "workflow_checks.py summarize --feature <feature-slug> --plan <NN>" in implement
    assert "run-watch-patrol --feature <feature-slug>" in implement
    assert "work-next <feature-slug> --json" in implement
    assert "run-review-ready <feature-slug> --run-id <run-id>" in implement
    assert "Delivery Run" in team
    assert "Work Order state" in team
    assert "workflow_memory.py run-create <feature> <NN> --mode team --json" in team
    assert "workflow_memory.py run-task-prompt <feature> <task-index> --run-id <run-id>" in team
    assert "workflow_memory.py run-sync-session <feature> --run-id <run-id> --json" in team
    assert "workflow_memory.py session-apply --json" in team
    assert "workflow_memory.py verify-import <module> [symbol...]" in team
    assert "run-plan-verify <feature> pass|fail" in team
    assert "--use-plan-verify" in team
    assert "Workers must not commit, push, create PRs, or stage repo-wide changes" in team
    assert "Work Order state, Delivery Run state, Integration state, Review readiness" in team
    assert "work-list --needs-attention --json" in team
    assert "session-status --json" in resume
    assert "status`, `integration`, and `reviewReadiness`" in resume
    assert "work-list --needs-attention --json" in resume
    assert "run-watch-patrol --feature <feature>" in resume
    assert "work-list --needs-attention --json" in status
    assert "initiative-current --json" in status
    assert "initiative-current --json" in resume


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
    assert "run-review-ready <feature-slug> --json" in review
    assert "must stop if there is no linked Delivery Run" in review
    assert "review.status = in_progress" in review
    assert "profile-required reviewers" in review
    assert "work-show <feature-slug> --json" in review
    assert "work-next <feature-slug> --json" in review
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


def test_ship_command_uses_delivery_run_ship_lifecycle():
    ship = _read(".claude/commands/ship.md")

    assert "work-show <feature-slug> --json" in ship
    assert "run-show <feature-slug> --json" in ship
    assert "ship.status == ready" in ship
    assert "resolved profile as ship policy context" in ship
    assert "workflow_checks.py ship-ready --feature <feature-slug>" in ship
    assert "workflow_memory.py run-ship-start <feature-slug>" in ship
    assert "ship.status = in_progress" in ship
    assert "workflow_memory.py run-ship-complete <feature-slug> --pr-url <pr-url>" in ship
    assert "workflow_memory.py run-ship-fail <feature-slug>" in ship
    assert "work-next <feature-slug> --json" in ship
