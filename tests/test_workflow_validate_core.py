"""Tests for plan/review policy enforcement in workflow_validate_core."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import workflow_validate_core as core


def _messages(findings):
    return [f.message for f in findings]


def _iso_now(offset_days: int = 0) -> str:
    return (
        datetime.now(timezone.utc) + timedelta(days=offset_days)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_plan_v1_is_backward_compatible_without_microsteps():
    findings = []
    contract = {
        "schemaVersion": 1,
        "feature": "demo",
        "planNumber": "01",
        "goal": "legacy",
        "tasks": [
            {
                "name": "legacy task",
                "files": ["a.py"],
                "action": "change a.py",
                "verify": ["pytest -q"],
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert not any("microSteps" in m for m in msgs)
    assert not any("schemaVersion>=2 requires 'tdd' object" in m for m in msgs)


def test_plan_v2_requires_microsteps_and_tdd():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "new policy",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "action": "change a.py",
                "verify": ["pytest -q"],
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("requires non-empty 'microSteps' array" in m for m in msgs)
    assert any("requires 'tdd' object" in m for m in msgs)


def test_plan_v2_tdd_required_needs_failing_and_passing_verify():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "tdd strict",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "microSteps": ["write failing test", "implement", "run passing tests"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {"required": True},
            }
        ],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("requires non-empty failingVerify[] commands" in m for m in msgs)
    assert any("requires non-empty passingVerify[] commands" in m for m in msgs)


def test_plan_v2_rationalized_tdd_exemption_is_rejected():
    findings = []
    contract = {
        "schemaVersion": 2,
        "feature": "demo",
        "planNumber": "01",
        "goal": "tdd strict",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "microSteps": ["tiny edit"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {"required": False, "reason": "too small, probably fine"},
            }
        ],
    }
    core._validate_plan_contract(contract, findings, Path("01-PLAN.json"), tdd_mode_level="error")
    msgs = _messages(findings)
    assert any("appears rationalized" in m for m in msgs)


def test_plan_v3_requires_context_links_and_failure_scenario():
    findings = []
    contract = {
        "schemaVersion": 3,
        "feature": "demo",
        "planNumber": "01",
        "goal": "stricter planning",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "microSteps": ["implement handler", "run tests"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {
                    "required": True,
                    "failingVerify": ["pytest tests/test_a.py"],
                    "passingVerify": ["pytest tests/test_a.py"],
                },
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(
        contract,
        findings,
        Path("01-PLAN.json"),
        tdd_mode_level="error",
        operating_principles_level="warn",
    )
    msgs = _messages(findings)
    assert any("requires non-empty 'contextLinks' array" in m for m in msgs)
    assert any("should name at least one explicit error-path scenario" in m for m in msgs)


def test_plan_v3_accepts_context_links_and_failure_scenario():
    findings = []
    contract = {
        "schemaVersion": 3,
        "feature": "demo",
        "planNumber": "01",
        "goal": "stricter planning",
        "tasks": [
            {
                "name": "task",
                "files": ["a.py"],
                "contextLinks": ["Constraint: return 400 on invalid input"],
                "microSteps": ["write invalid input failure test", "implement validation", "run tests"],
                "action": "change a.py",
                "verify": ["pytest -q"],
                "tdd": {
                    "required": True,
                    "failingVerify": ["pytest tests/test_a.py -k invalid_input"],
                    "passingVerify": ["pytest tests/test_a.py -k invalid_input"],
                },
            }
        ],
        "planVerify": ["pytest -q"],
    }
    core._validate_plan_contract(
        contract,
        findings,
        Path("01-PLAN.json"),
        tdd_mode_level="error",
        operating_principles_level="warn",
    )
    msgs = _messages(findings)
    assert not any("contextLinks" in m for m in msgs)
    assert not any("explicit error-path scenario" in m for m in msgs)


def test_review_v4_requires_stage_reviews_when_enabled(tmp_path):
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "REVIEW.md").write_text("# Review\n", encoding="utf-8")
    (feature_dir / "REVIEW.json").write_text(
        '{"schemaVersion":4,"verdict":"pass","securityFindings":[],"performanceFindings":[],"patternCompliance":[]}',
        encoding="utf-8",
    )
    findings = []
    core._validate_ci_verification(
        feature_dir,
        findings,
        "warn",
        "error",
        "error",
    )
    msgs = _messages(findings)
    assert any("requires stageReviews[spec-compliance, code-quality]" in m for m in msgs)


def test_review_requires_schema_v4_when_two_stage_policy_enabled(tmp_path):
    feature_dir = tmp_path / "feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "REVIEW.md").write_text("# Review\n", encoding="utf-8")
    (feature_dir / "REVIEW.json").write_text(
        '{"schemaVersion":3,"verdict":"pass","securityFindings":[],"performanceFindings":[],"patternCompliance":[]}',
        encoding="utf-8",
    )
    findings = []
    core._validate_ci_verification(
        feature_dir,
        findings,
        "warn",
        "error",
        "error",
    )
    msgs = _messages(findings)
    assert any("must set schemaVersion>=4" in m for m in msgs)


def test_workflow_config_accepts_task_ownership_and_max_takeovers(tmp_path):
    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "enforcement": {
            "taskOwnership": "error",
        },
        "agentTeams": {
            "staleIndicatorMinutes": 10,
            "maxTakeoversPerTask": 2,
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert not any("enforcement.taskOwnership should be off|warn|error" in m for m in msgs)
    assert not any("agentTeams.maxTakeoversPerTask should be an integer >= 0" in m for m in msgs)


def test_workflow_config_rejects_invalid_task_ownership_and_max_takeovers(tmp_path):
    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "enforcement": {
            "taskOwnership": "hard",
        },
        "agentTeams": {
            "maxTakeoversPerTask": -1,
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert any("enforcement.taskOwnership should be off|warn|error" in m for m in msgs)
    assert any("agentTeams.maxTakeoversPerTask should be an integer >= 0" in m for m in msgs)


def test_validate_research_wrapper_preserves_contract_checks(tmp_path):
    research_dir = tmp_path / "docs" / "planning" / "work" / "research" / "provider-study"
    research_dir.mkdir(parents=True, exist_ok=True)
    (research_dir / "RESEARCH.md").write_text("# Research\n", encoding="utf-8")
    (research_dir / "RESEARCH.json").write_text(
        json.dumps({"schemaVersion": 1, "sources": "not-an-array"}),
        encoding="utf-8",
    )

    findings = []
    core._validate_research(tmp_path, findings, lambda _path: True)

    assert any("RESEARCH.json: sources should be an array." in m for m in _messages(findings))


def test_validate_quick_wrapper_preserves_contract_checks(tmp_path):
    quick_dir = tmp_path / "docs" / "planning" / "work" / "quick" / "001-fix-typo"
    quick_dir.mkdir(parents=True, exist_ok=True)
    (quick_dir / "PLAN.md").write_text("# Quick Plan\n", encoding="utf-8")

    findings = []
    core._validate_quick_tasks(tmp_path, findings, lambda _path: True)

    assert any("Missing PLAN.json contract for quick PLAN.md" in m for m in _messages(findings))


def test_validate_quick_summary_wrapper_preserves_contract_checks():
    findings = []

    core._validate_quick_summary({"schemaVersion": 1, "changes": []}, findings, Path("SUMMARY.json"))

    msgs = _messages(findings)
    assert any("Quick summary missing non-empty 'outcome'." in m for m in msgs)
    assert any("Quick summary missing non-empty 'changes' list." in m for m in msgs)
    assert any("Quick summary missing non-empty 'verification' list." in m for m in msgs)


def test_workflow_config_accepts_review_default_composition_with_real_agents(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for name in ("code-reviewer", "security-scanner", "perf-analyzer"):
        (agents_dir / f"{name}.md").write_text("---\nname: test\n---\n", encoding="utf-8")

    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "agentTeams": {
            "defaultCompositions": {
                "review": ["code-reviewer", "security-scanner", "perf-analyzer"],
            }
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert not any("defaultCompositions.review should use at least 2 distinct reviewer agents" in m for m in msgs)
    assert not any("references missing agent" in m for m in msgs)


def test_workflow_config_warns_on_homogeneous_or_missing_review_agents(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "implementer.md").write_text("---\nname: test\n---\n", encoding="utf-8")

    findings = []
    cfg = {
        "version": 1,
        "repoShape": "auto",
        "agentTeams": {
            "defaultCompositions": {
                "review": ["implementer", "implementer", "missing-agent"],
            }
        },
        "packages": [],
    }
    core._validate_workflow_config(cfg, findings, tmp_path)
    msgs = _messages(findings)
    assert any("references missing agent 'missing-agent'" in m for m in msgs)
    assert any("should use at least 2 distinct reviewer agents" in m for m in msgs)


def test_detect_repo_shape_prefers_configured_packages(tmp_path):
    shape = core._detect_repo_shape(
        tmp_path,
        {
            "packages": [
                {"path": "apps/web", "kind": "node"},
                {"path": "services/api", "kind": "go"},
                {"path": "tools/worker", "kind": "go"},
            ]
        },
    )

    assert shape["package_json"] == 1
    assert shape["go_mod"] == 2
    assert shape["monorepo"] is True
    assert shape["polyglot"] is True


def test_policy_level_wrappers_fall_back_to_defaults():
    cfg = {
        "enforcement": {
            "monorepoVerifyScope": "nope",
            "operatingPrinciples": "nope",
            "tddMode": "nope",
            "verificationBeforeCompletion": "nope",
            "twoStageReview": "nope",
            "taskOwnership": "nope",
        }
    }

    assert core._get_monorepo_scope_level(cfg) == "warn"
    assert core._get_operating_principles_level(cfg) == "warn"
    assert core._get_tdd_mode_level(cfg) == "error"
    assert core._get_verification_before_completion_level(cfg) == "error"
    assert core._get_two_stage_review_level(cfg) == "error"
    assert core._get_task_ownership_level(cfg) == "error"


def test_verify_cmd_scoped_wrapper_distinguishes_scoped_and_unscoped_commands():
    assert core._verify_cmd_scoped("cd apps/web && npm test")
    assert core._verify_cmd_scoped("pytest -q")
    assert not core._verify_cmd_scoped("npm test")


def test_validate_token_budgets_warns_on_touched_shape_artifact(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "demo-shape"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    shape_md = ideas_dir / "SHAPE.md"
    shape_md.write_text(" ".join(["shape"] * 40), encoding="utf-8")

    findings = []
    core._validate_token_budgets(
        tmp_path,
        findings,
        lambda _path: True,
        {
            "enabled": True,
            "shapeWordMax": 5,
            "brainstormWordMax": 5,
        },
    )

    assert any("Shape artifact is" in m for m in _messages(findings))


def test_validate_bootstrap_context_warns_on_large_claude_files(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(" ".join(["root"] * 20), encoding="utf-8")
    workflow_claude = tmp_path / ".claude"
    workflow_claude.mkdir(parents=True, exist_ok=True)
    (workflow_claude / "CLAUDE.md").write_text(" ".join(["workflow"] * 20), encoding="utf-8")
    commands_dir = workflow_claude / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "shape.md").write_text(" ".join(["command"] * 20), encoding="utf-8")

    findings = []
    core._validate_bootstrap_context(
        tmp_path,
        findings,
        {
            "enabled": True,
            "rootClaudeWordMax": 5,
            "workflowClaudeWordMax": 5,
            "commandSetWordMax": 5,
        },
    )

    msgs = _messages(findings)
    assert any("Root CLAUDE.md is" in m for m in msgs)
    assert any("Workflow CLAUDE.md is" in m for m in msgs)
    assert any("Command artifact set totals" in m for m in msgs)


def test_memory_runtime_accepts_tracked_issues_jsonl(tmp_path):
    findings = []
    cnogo_dir = tmp_path / ".cnogo"
    cnogo_dir.mkdir(parents=True, exist_ok=True)
    (cnogo_dir / "issues.jsonl").write_text("", encoding="utf-8")

    core._validate_memory_runtime(tmp_path, findings)

    msgs = _messages(findings)
    assert not any("Memory runtime is not initialized locally" in m for m in msgs)


def test_memory_runtime_warns_when_runtime_and_sync_file_are_missing(tmp_path):
    findings = []

    core._validate_memory_runtime(tmp_path, findings)

    msgs = _messages(findings)
    assert any("Memory runtime is not initialized locally" in m for m in msgs)


def test_shape_artifact_allows_multiple_discuss_ready_features_with_stubs(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "personal-finance-app"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "SHAPE.md").write_text("# Shape\n", encoding="utf-8")
    (ideas_dir / "SHAPE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "initiative": "Personal finance application",
                "slug": "personal-finance-app",
                "problem": "Turn a broad product idea into discuss-ready features.",
                "constraints": ["Manual entry first"],
                "globalDecisions": ["Local-first MVP"],
                "researchRefs": [],
                "openQuestions": [],
                "candidateFeatures": [
                    {
                        "slug": "manual-transaction-ledger",
                        "displayName": "Manual Transaction Ledger",
                        "userOutcome": "Users can record transactions manually.",
                        "scopeSummary": "Ledger CRUD and balance tracking.",
                        "dependencies": [],
                        "risks": ["Schema churn"],
                        "status": "discuss-ready",
                        "readinessReason": "Core MVP slice is bounded.",
                        "handoffSummary": "Discuss fields, validation, and edit semantics.",
                    },
                    {
                        "slug": "monthly-dashboard",
                        "displayName": "Monthly Dashboard",
                        "userOutcome": "Users can review spending trends.",
                        "scopeSummary": "Read-only monthly totals and category trends.",
                        "dependencies": ["manual-transaction-ledger"],
                        "risks": ["Aggregation edge cases"],
                        "status": "discuss-ready",
                        "readinessReason": "Depends only on the ledger shape.",
                        "handoffSummary": "Discuss metrics and empty-state behavior.",
                    },
                ],
                "recommendedSequence": ["manual-transaction-ledger", "monthly-dashboard"],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    for slug in ("manual-transaction-ledger", "monthly-dashboard"):
        feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / slug
        feature_dir.mkdir(parents=True, exist_ok=True)
        (feature_dir / "FEATURE.md").write_text("# Feature\n", encoding="utf-8")
        (feature_dir / "FEATURE.json").write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "feature": slug,
                    "displayName": slug.replace("-", " ").title(),
                    "userOutcome": "Outcome",
                    "scopeSummary": "Scope",
                    "dependencies": [],
                    "risks": [],
                    "status": "discuss-ready",
                    "readinessReason": "Ready now",
                    "handoffSummary": "Discuss next",
                    "parentShape": {
                        "path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json",
                        "timestamp": _iso_now(),
                        "schemaVersion": 1,
                    },
                    "timestamp": _iso_now(),
                }
            ),
            encoding="utf-8",
        )

    findings = []
    core._validate_shape_artifacts(tmp_path, findings, lambda _path: True)

    msgs = _messages(findings)
    assert not any("discuss-ready but missing feature stub" in m for m in msgs)
    assert not any("duplicate candidate feature slug" in m for m in msgs)


def test_shape_artifact_allows_optional_workspace_fields(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "learning-platform-intelligence"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "SHAPE.md").write_text("# Shape\n", encoding="utf-8")
    (ideas_dir / "SHAPE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "initiative": "Learning platform intelligence",
                "slug": "learning-platform-intelligence",
                "problem": "Shape the initiative without forcing a feature handoff.",
                "constraints": ["Beam-first runtime"],
                "globalDecisions": ["Keep shape active while features branch into discuss"],
                "decisionLog": [
                    {
                        "title": "Workspace model",
                        "decision": "Treat discuss-ready as an optional exit",
                        "rationale": "Avoid forcing early handoff",
                    }
                ],
                "shapeThreads": [
                    {
                        "title": "Provider strategy",
                        "summary": "Decide whether provider support starts narrow or broad.",
                        "status": "open",
                        "relatedFeatures": ["scene-generation-pipeline"],
                    }
                ],
                "researchRefs": [],
                "openQuestions": ["Should provider choice remain open through the first discuss pass?"],
                "candidateFeatures": [
                    {
                        "slug": "learning-domain-model",
                        "displayName": "Learning Domain Model",
                        "userOutcome": "Authors can define learning entities and relationships.",
                        "scopeSummary": "Core shared data model and policy hooks.",
                        "dependencies": [],
                        "risks": ["Schema churn"],
                        "status": "draft",
                        "readinessReason": "Needs provider decision first.",
                        "handoffSummary": "Discuss after provider boundary is settled.",
                    }
                ],
                "nextShapeMoves": ["Compare provider strategy options", "Split the classroom orchestration candidate if still broad"],
                "recommendedSequence": ["learning-domain-model"],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_shape_artifacts(tmp_path, findings, lambda _path: True)

    assert not any("decisionLog" in m for m in _messages(findings))
    assert not any("shapeThreads" in m for m in _messages(findings))
    assert not any("nextShapeMoves" in m for m in _messages(findings))


def test_shape_artifact_requires_feature_md_and_json_for_discuss_ready_candidates(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "personal-finance-app"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "SHAPE.md").write_text("# Shape\n", encoding="utf-8")
    (ideas_dir / "SHAPE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "initiative": "Personal finance application",
                "slug": "personal-finance-app",
                "problem": "Turn a broad product idea into discuss-ready features.",
                "candidateFeatures": [
                    {
                        "slug": "manual-transaction-ledger",
                        "displayName": "Manual Transaction Ledger",
                        "userOutcome": "Users can record transactions manually.",
                        "scopeSummary": "Ledger CRUD and balance tracking.",
                        "dependencies": [],
                        "risks": [],
                        "status": "discuss-ready",
                        "readinessReason": "Core MVP slice is bounded.",
                        "handoffSummary": "Discuss fields and validation.",
                    }
                ],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "manual-transaction-ledger"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "FEATURE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "manual-transaction-ledger",
                "displayName": "Manual Transaction Ledger",
                "userOutcome": "Outcome",
                "scopeSummary": "Scope",
                "dependencies": [],
                "risks": [],
                "status": "discuss-ready",
                "readinessReason": "Ready now",
                "handoffSummary": "Discuss next",
                "parentShape": {
                    "path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json",
                    "timestamp": _iso_now(),
                    "schemaVersion": 1,
                },
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_shape_artifacts(tmp_path, findings, lambda _path: True)

    assert any(
        "discuss-ready but missing feature stub docs/planning/work/features/manual-transaction-ledger/FEATURE.md"
        in m
        for m in _messages(findings)
    )


def test_shape_artifact_rejects_duplicate_candidate_feature_slugs(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "duplicate-shape"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "SHAPE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "initiative": "Duplicate",
                "slug": "duplicate-shape",
                "problem": "Problem",
                "candidateFeatures": [
                    {
                        "slug": "same-feature",
                        "displayName": "One",
                        "userOutcome": "Outcome",
                        "scopeSummary": "Scope",
                        "dependencies": [],
                        "risks": [],
                        "status": "draft",
                        "readinessReason": "Reason",
                        "handoffSummary": "Handoff",
                    },
                    {
                        "slug": "same-feature",
                        "displayName": "Two",
                        "userOutcome": "Outcome",
                        "scopeSummary": "Scope",
                        "dependencies": [],
                        "risks": [],
                        "status": "draft",
                        "readinessReason": "Reason",
                        "handoffSummary": "Handoff",
                    },
                ],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_shape_artifacts(tmp_path, findings, lambda _path: True)

    assert any("duplicate candidate feature slug 'same-feature'" in m for m in _messages(findings))


def test_legacy_brainstorm_artifact_still_validates(tmp_path):
    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "legacy-idea"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "BRAINSTORM.md").write_text("# Brainstorm\n", encoding="utf-8")
    (ideas_dir / "BRAINSTORM.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "topic": "Legacy idea",
                "slug": "legacy-idea",
                "questionsAsked": ["Who is this for?"],
                "constraints": ["Small MVP"],
                "candidates": [{"name": "Option A", "summary": "A", "risks": [], "mvp": []}],
                "recommendation": {"primary": "Option A", "backup": "Option B"},
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_shape_artifacts(tmp_path, findings, lambda _path: True)

    msgs = _messages(findings)
    assert not any("Missing SHAPE.json" in m for m in msgs)
    assert not any("must be a JSON object" in m for m in msgs)


def test_feature_and_context_warn_when_parent_shape_is_stale(tmp_path):
    shape_ts = _iso_now()
    older_ts = _iso_now(-1)

    ideas_dir = tmp_path / "docs" / "planning" / "work" / "ideas" / "personal-finance-app"
    ideas_dir.mkdir(parents=True, exist_ok=True)
    (ideas_dir / "SHAPE.md").write_text("# Shape\n", encoding="utf-8")
    (ideas_dir / "SHAPE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "initiative": "Personal finance application",
                "slug": "personal-finance-app",
                "problem": "Problem",
                "candidateFeatures": [],
                "timestamp": shape_ts,
            }
        ),
        encoding="utf-8",
    )

    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "manual-transaction-ledger"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "FEATURE.md").write_text("# Feature\n", encoding="utf-8")
    (feature_dir / "FEATURE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "manual-transaction-ledger",
                "displayName": "Manual Transaction Ledger",
                "userOutcome": "Record transactions",
                "scopeSummary": "Scope",
                "dependencies": [],
                "risks": [],
                "status": "discuss-ready",
                "readinessReason": "Ready",
                "handoffSummary": "Discuss ledger fields",
                "parentShape": {
                    "path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json",
                    "timestamp": older_ts,
                    "schemaVersion": 1,
                },
                "timestamp": older_ts,
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "CONTEXT.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "CONTEXT.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "manual-transaction-ledger",
                "displayName": "Manual Transaction Ledger",
                "decisions": [],
                "constraints": [],
                "openQuestions": [],
                "relatedCode": [],
                "parentShape": {
                    "path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json",
                    "timestamp": older_ts,
                    "schemaVersion": 1,
                },
                "featureStub": {
                    "path": "docs/planning/work/features/manual-transaction-ledger/FEATURE.json",
                    "timestamp": older_ts,
                    "schemaVersion": 1,
                },
                "timestamp": older_ts,
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_features(
        tmp_path,
        findings,
        lambda _path: True,
        {"monorepo": False, "polyglot": False},
        "warn",
        "warn",
        "error",
        "error",
        "error",
        [],
        {"enabled": True, "contextMaxAgeDays": 30, "planMaxAgeDaysWithoutSummary": 14, "summaryMaxAgeDaysWithoutReview": 7},
    )

    msgs = _messages(findings)
    assert any("FEATURE.json: parentShape is stale" in m for m in msgs)
    assert any("CONTEXT.json: parentShape is stale" in m for m in msgs)


def test_direct_discuss_context_without_feature_stub_still_validates(tmp_path):
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "standalone-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "CONTEXT.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "CONTEXT.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "standalone-feature",
                "displayName": "Standalone Feature",
                "decisions": [],
                "constraints": [],
                "openQuestions": [],
                "relatedCode": [],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_features(
        tmp_path,
        findings,
        lambda _path: True,
        {"monorepo": False, "polyglot": False},
        "warn",
        "warn",
        "error",
        "error",
        "error",
        [],
        {"enabled": True, "contextMaxAgeDays": 30, "planMaxAgeDaysWithoutSummary": 14, "summaryMaxAgeDaysWithoutReview": 7},
    )

    msgs = _messages(findings)
    assert not any("Missing FEATURE.json contract for FEATURE.md" in m for m in msgs)


def test_context_shape_feedback_is_allowed_and_validated(tmp_path):
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "learning-domain-model"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "CONTEXT.md").write_text("# Context\n", encoding="utf-8")
    (feature_dir / "CONTEXT.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "learning-domain-model",
                "displayName": "Learning Domain Model",
                "decisions": [],
                "constraints": [],
                "openQuestions": [],
                "relatedCode": [],
                "shapeFeedback": [
                    {
                        "summary": "Provider support should remain a shape-level thread until scene-generation is discussed.",
                        "affectedFeatures": ["scene-generation-pipeline"],
                        "suggestedAction": "Re-run /shape to keep provider strategy open.",
                    }
                ],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_features(
        tmp_path,
        findings,
        lambda _path: True,
        {"monorepo": False, "polyglot": False},
        "warn",
        "warn",
        "error",
        "error",
        "error",
        [],
        {"enabled": True, "contextMaxAgeDays": 30, "planMaxAgeDaysWithoutSummary": 14, "summaryMaxAgeDaysWithoutReview": 7},
    )

    assert not any("shapeFeedback" in m for m in _messages(findings))


def test_standalone_feature_stub_without_parent_shape_still_validates(tmp_path):
    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "standalone-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "FEATURE.md").write_text("# Feature\n", encoding="utf-8")
    (feature_dir / "FEATURE.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "standalone-feature",
                "displayName": "Standalone Feature",
                "userOutcome": "Users can complete a focused standalone flow.",
                "scopeSummary": "Small independently discussed feature.",
                "dependencies": [],
                "risks": [],
                "status": "draft",
                "readinessReason": "Early feature stub for direct discuss.",
                "handoffSummary": "Discuss boundaries and code touch points.",
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    findings = []
    core._validate_features(
        tmp_path,
        findings,
        lambda _path: True,
        {"monorepo": False, "polyglot": False},
        "warn",
        "warn",
        "error",
        "error",
        "error",
        [],
        {"enabled": True, "contextMaxAgeDays": 30, "planMaxAgeDaysWithoutSummary": 14, "summaryMaxAgeDaysWithoutReview": 7},
    )

    assert not any("FEATURE.json should include parentShape linkage." in m for m in _messages(findings))


def test_validate_skills_resolves_directory_skill_references(tmp_path):
    skills_dir = tmp_path / ".claude" / "skills" / "shape-facilitator"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "SKILL.md").write_text(
        "---\nname: shape-facilitator\nappliesTo: [shape]\n---\n# Skill\n",
        encoding="utf-8",
    )
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "shape.md").write_text(
        "Use `.claude/skills/shape-facilitator/SKILL.md`.\n",
        encoding="utf-8",
    )

    findings = []
    core._validate_skills(tmp_path, findings, lambda _path: True)

    assert not any("Skill reference '.claude/skills/shape-facilitator/SKILL.md' not found." in m for m in _messages(findings))


def test_validate_skills_resolves_agent_references(tmp_path):
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "shape-scout.md").write_text(
        "---\nname: shape-scout\ndescription: Scout\n---\n# Agent\n",
        encoding="utf-8",
    )
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "shape.md").write_text(
        "Use `.claude/agents/shape-scout.md`.\n",
        encoding="utf-8",
    )

    findings = []
    core._validate_skills(tmp_path, findings, lambda _path: True)

    assert not any("Agent reference '.claude/agents/shape-scout.md' not found." in m for m in _messages(findings))


def test_validate_skills_warns_when_shape_references_spawn_research(tmp_path):
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "shape.md").write_text(
        "Use `/spawn research <task>` during shape.\n",
        encoding="utf-8",
    )

    findings = []
    core._validate_skills(tmp_path, findings, lambda _path: True)

    assert any(
        "Shape workspace should use `/research` directly instead of `/spawn research <task>`" in m
        for m in _messages(findings)
    )


def test_validate_skills_warns_when_scout_mappings_load_shared_skills(tmp_path):
    commands_dir = tmp_path / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    (commands_dir / "spawn.md").write_text(
        "- `shape-scout` -> `.claude/agents/shape-scout.md` + `.claude/skills/shape-facilitator/SKILL.md`\n",
        encoding="utf-8",
    )

    findings = []
    core._validate_skills(tmp_path, findings, lambda _path: True)

    assert any(
        "Scout specialization `shape-scout` should map only to a read-only agent" in m
        for m in _messages(findings)
    )


def test_validate_repo_accepts_generated_summary_metadata_and_reviewers(tmp_path):
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
    (planning_dir / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps(
            {
                "version": 1,
                "repoShape": "auto",
                "enforcement": {
                    "twoStageReview": "error",
                    "verificationBeforeCompletion": "error",
                    "tddMode": "error",
                },
                "packages": [],
            }
        ),
        encoding="utf-8",
    )

    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "01-PLAN.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "01-PLAN.json").write_text(
        json.dumps(
            {
                "schemaVersion": 3,
                "feature": "demo",
                "planNumber": "01",
                "goal": "demo",
                "tasks": [
                    {
                        "name": "Add handler",
                        "files": ["app.py"],
                        "contextLinks": ["Constraint: return deterministic output"],
                        "microSteps": ["write failure test", "implement handler", "run tests"],
                        "action": "Update app.py",
                        "verify": ["pytest -q"],
                        "tdd": {
                            "required": True,
                            "failingVerify": ["pytest -q -k fail"],
                            "passingVerify": ["pytest -q -k fail"],
                        },
                    }
                ],
                "planVerify": ["pytest -q"],
                "commitMessage": "feat: demo",
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "01-SUMMARY.md").write_text("# Summary\n", encoding="utf-8")
    (feature_dir / "01-SUMMARY.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "feature": "demo",
                "planNumber": "01",
                "outcome": "complete",
                "changes": [{"file": "app.py", "change": "Add handler"}],
                "verification": [{"scope": "task", "name": "Add handler", "result": "pass", "commands": ["pytest -q"]}],
                "commit": {"hash": "abc123", "message": "feat: demo"},
                "generatedFrom": {"kind": "workflow_checks.summarize"},
                "notes": ["Generated automatically."],
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "REVIEW.md").write_text("# Review\n", encoding="utf-8")
    (feature_dir / "REVIEW.json").write_text(
        json.dumps(
            {
                "schemaVersion": 4,
                "timestamp": _iso_now(),
                "reviewers": ["code-reviewer", "security-scanner", "perf-analyzer"],
                "stageReviews": [
                    {"stage": "spec-compliance", "status": "pass", "findings": [], "evidence": ["plan + diff"]},
                    {"stage": "code-quality", "status": "pass", "findings": [], "evidence": ["review agents"]},
                ],
                "securityFindings": [],
                "performanceFindings": [],
                "patternCompliance": [],
                "verdict": "pass",
            }
        ),
        encoding="utf-8",
    )

    findings = core.validate_repo(tmp_path, staged_only=False, feature_filter="demo")
    msgs = _messages(findings)

    assert not any("Summary generatedFrom" in m for m in msgs)
    assert not any("Summary notes" in m for m in msgs)
    assert not any("REVIEW.json reviewers" in m for m in msgs)


def test_validate_repo_accepts_delivery_run_and_session_link(tmp_path):
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
    (planning_dir / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps({"version": 1, "repoShape": "auto", "packages": []}),
        encoding="utf-8",
    )

    cnogo_dir = tmp_path / ".cnogo"
    cnogo_dir.mkdir(parents=True, exist_ok=True)
    (cnogo_dir / "memory.db").write_text("", encoding="utf-8")

    feature_dir = tmp_path / "docs" / "planning" / "work" / "features" / "demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "01-PLAN.json").write_text(
        json.dumps(
            {
                "schemaVersion": 3,
                "feature": "demo",
                "planNumber": "01",
                "goal": "demo",
                "tasks": [
                    {
                        "name": "Add handler",
                        "files": ["app.py"],
                        "contextLinks": ["Constraint: return deterministic output"],
                        "microSteps": ["write invalid-input failure test", "implement handler", "run tests"],
                        "action": "Update app.py",
                        "verify": ["pytest -q"],
                        "tdd": {
                            "required": True,
                            "failingVerify": ["pytest -q -k fail"],
                            "passingVerify": ["pytest -q -k fail"],
                        },
                    }
                ],
                "planVerify": ["pytest -q"],
                "commitMessage": "feat: demo",
                "timestamp": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    runs_dir = tmp_path / ".cnogo" / "runs" / "demo"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "demo-100.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "runId": "demo-100",
                "feature": "demo",
                "planNumber": "01",
                "mode": "team",
                "status": "active",
                "startedBy": "claude",
                "branch": "feature/demo",
                "planPath": "docs/planning/work/features/demo/01-PLAN.json",
                "summaryPath": "docs/planning/work/features/demo/01-SUMMARY.json",
                "reviewPath": "docs/planning/work/features/demo/REVIEW.json",
                "recommendation": {"recommended": True},
                "integration": {
                    "status": "awaiting_merge",
                    "mergedTaskIndices": [],
                    "awaitingMergeTaskIndices": [0],
                    "activeTaskIndices": [],
                    "conflictTaskIndex": None,
                    "conflictFiles": [],
                    "lastSessionPhase": "executing",
                    "updatedAt": _iso_now(),
                },
                "reviewReadiness": {
                    "status": "pending",
                    "planVerifyPassed": None,
                    "verifiedAt": "",
                    "verifiedCommands": [],
                    "notes": [],
                    "updatedAt": _iso_now(),
                },
                "tasks": [
                    {
                        "taskIndex": 0,
                        "title": "Add handler",
                        "status": "ready",
                        "memoryId": "cn-demo",
                        "blockedBy": [],
                        "filePaths": ["app.py"],
                        "forbiddenPaths": [],
                        "verifyCommands": ["pytest -q"],
                        "packageVerifyCommands": [],
                        "cwd": "",
                        "assignee": "",
                        "branch": "",
                        "worktreePath": "",
                        "notes": [],
                        "updatedAt": _iso_now(),
                    }
                ],
                "notes": [],
                "createdAt": _iso_now(),
                "updatedAt": _iso_now(),
            }
        ),
        encoding="utf-8",
    )

    (cnogo_dir / "worktree-session.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "demo",
                "planNumber": "01",
                "runId": "demo-100",
                "baseCommit": "abc123",
                "baseBranch": "feature/demo",
                "phase": "executing",
                "worktrees": [],
                "mergeOrder": [],
                "mergedSoFar": [],
            }
        ),
        encoding="utf-8",
    )

    findings = core.validate_repo(tmp_path, staged_only=False)
    msgs = _messages(findings)

    assert not any("Delivery run" in msg for msg in msgs)
    assert not any("worktree-session.json references runId" in msg for msg in msgs)


def test_validate_repo_warns_for_invalid_delivery_run_and_missing_session_link(tmp_path):
    planning_dir = tmp_path / "docs" / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    (planning_dir / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
    (planning_dir / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (planning_dir / "WORKFLOW.json").write_text(
        json.dumps({"version": 1, "repoShape": "auto", "packages": []}),
        encoding="utf-8",
    )

    cnogo_dir = tmp_path / ".cnogo"
    cnogo_dir.mkdir(parents=True, exist_ok=True)
    (cnogo_dir / "memory.db").write_text("", encoding="utf-8")

    runs_dir = tmp_path / ".cnogo" / "runs" / "demo"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "demo-bad.json").write_text(
        json.dumps(
            {
                "schemaVersion": "1",
                "runId": "",
                "feature": "wrong-feature",
                "planNumber": "",
                "mode": "invalid",
                "status": "mystery",
                "integration": {
                    "status": "mystery",
                    "mergedTaskIndices": "bad",
                    "conflictTaskIndex": "zero",
                },
                "reviewReadiness": {
                    "status": "mystery",
                    "planVerifyPassed": "yes",
                    "verifiedCommands": "pytest -q",
                },
                "tasks": [{"taskIndex": "0", "title": "", "status": "mystery"}],
            }
        ),
        encoding="utf-8",
    )

    (cnogo_dir / "worktree-session.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "feature": "demo",
                "planNumber": "01",
                "runId": "missing-run",
                "baseCommit": "abc123",
                "baseBranch": "feature/demo",
                "phase": "executing",
                "worktrees": [],
                "mergeOrder": [],
                "mergedSoFar": [],
            }
        ),
        encoding="utf-8",
    )

    findings = core.validate_repo(tmp_path, staged_only=False)
    msgs = _messages(findings)

    assert any("Delivery run schemaVersion should be an integer." in msg for msg in msgs)
    assert any("Delivery run mode should be serial|team." in msg for msg in msgs)
    assert any("Delivery run status should be one of" in msg for msg in msgs)
    assert any("Delivery run integration.status should be one of" in msg for msg in msgs)
    assert any("Delivery run reviewReadiness.status should be one of" in msg for msg in msgs)
    assert any("worktree-session.json references runId that does not exist" in msg for msg in msgs)


def test_validation_baseline_round_trip(tmp_path):
    warning = core._finding_to_warning(core.Finding("WARN", "Example warning", "demo.json"))
    path = core.save_baseline([warning], tmp_path)
    assert path.exists()

    loaded = core.load_baseline(tmp_path)
    assert loaded == [warning]

    diff = core.diff_baselines(loaded, loaded)
    assert diff == {"new": [], "resolved": [], "unchanged": [warning]}


def test_validate_repo_staged_requires_git_repo(tmp_path):
    findings = core.validate_repo(tmp_path, staged_only=True)

    assert any("--staged requires a git repository." in message for message in _messages(findings))
