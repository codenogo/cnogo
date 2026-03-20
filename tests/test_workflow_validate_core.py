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
