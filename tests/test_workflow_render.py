"""Tests for markdown rendering from workflow contracts."""

from scripts import workflow_render as render


def test_render_shape_preserves_candidate_handoff_details():
    markdown = render.render_shape(
        {
            "initiative": "Personal finance application",
            "problem": "Turn a broad idea into discuss-ready slices.",
            "constraints": ["Manual entry first"],
            "globalDecisions": ["Local-first MVP"],
            "candidateFeatures": [
                {
                    "slug": "manual-transaction-ledger",
                    "displayName": "Manual Transaction Ledger",
                    "userOutcome": "Users can record transactions manually.",
                    "scopeSummary": "Ledger CRUD and balance tracking.",
                    "dependencies": ["shared-currency-formatting"],
                    "risks": ["Schema churn"],
                    "status": "discuss-ready",
                    "readinessReason": "Core MVP slice is bounded.",
                    "handoffSummary": "Discuss fields, validation, and edit semantics.",
                }
            ],
            "recommendedSequence": ["manual-transaction-ledger"],
        }
    )

    assert "## Feature Handoffs" in markdown
    assert "Manual Transaction Ledger" in markdown
    assert "- Scope: Ledger CRUD and balance tracking." in markdown
    assert "- Readiness: Core MVP slice is bounded." in markdown
    assert "- Handoff: Discuss fields, validation, and edit semantics." in markdown
    assert "  - shared-currency-formatting" in markdown
    assert "  - Schema churn" in markdown


def test_render_shape_workspace_sections_are_ordered_and_workspace_first():
    markdown = render.render_shape(
        {
            "initiative": "Learning platform intelligence",
            "problem": "Shape the initiative without forcing a feature exit.",
            "constraints": ["Beam-first runtime"],
            "globalDecisions": ["Keep shape active while features branch into discuss"],
            "decisionLog": [
                {
                    "title": "Workspace model",
                    "decision": "Discuss-ready features are optional exits",
                    "rationale": "Shape should remain active",
                }
            ],
            "shapeThreads": [
                {
                    "title": "Provider strategy",
                    "summary": "Compare narrow and broad provider support.",
                    "status": "open",
                    "relatedFeatures": ["scene-generation-pipeline"],
                }
            ],
            "candidateFeatures": [
                {
                    "slug": "learning-domain-model",
                    "displayName": "Learning Domain Model",
                    "userOutcome": "Authors can define the core model.",
                    "scopeSummary": "Shared entities, relationships, and policy hooks.",
                    "dependencies": [],
                    "risks": ["Schema churn"],
                    "status": "discuss-ready",
                    "readinessReason": "The foundation slice is bounded.",
                    "handoffSummary": "Discuss boundary and edit semantics.",
                }
            ],
            "nextShapeMoves": ["Compare provider strategy", "Split classroom orchestration if still broad"],
            "recommendedSequence": ["learning-domain-model"],
            "openQuestions": ["Should provider selection stay open longer?"],
        }
    )

    assert "## Stable Decisions" in markdown
    assert "## Active Shape Threads" in markdown
    assert "## Feature Queue" in markdown
    assert "## Suggested Next Shape Moves" in markdown
    assert "## Optional Discuss Exits" in markdown
    assert markdown.index("## Stable Decisions") < markdown.index("## Active Shape Threads")
    assert markdown.index("## Active Shape Threads") < markdown.index("## Feature Queue")
    assert markdown.index("## Feature Queue") < markdown.index("## Suggested Next Shape Moves")
    assert markdown.index("## Suggested Next Shape Moves") < markdown.index("## Optional Discuss Exits")
    assert "- `/discuss learning-domain-model` - Learning Domain Model" in markdown


def test_render_feature_stub_preserves_parent_shape_linkage():
    markdown = render.render_feature_stub(
        {
            "feature": "manual-transaction-ledger",
            "displayName": "Manual Transaction Ledger",
            "userOutcome": "Users can record transactions manually.",
            "scopeSummary": "Ledger CRUD and balance tracking.",
            "dependencies": [],
            "risks": [],
            "status": "discuss-ready",
            "readinessReason": "Core MVP slice is bounded.",
            "handoffSummary": "Discuss fields and validation.",
            "parentShape": {
                "path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json",
                "timestamp": "2026-03-19T20:00:00Z",
            },
        }
    )

    assert "# Feature: Manual Transaction Ledger" in markdown
    assert "## Parent Shape" in markdown
    assert "`docs/planning/work/ideas/personal-finance-app/SHAPE.json`" in markdown
    assert "`2026-03-19T20:00:00Z`" in markdown


def test_render_context_includes_parent_links_and_shape_feedback():
    markdown = render.render_context(
        {
            "feature": "manual-transaction-ledger",
            "displayName": "Manual Transaction Ledger",
            "decisions": [
                {
                    "area": "validation",
                    "decision": "Require amount and date.",
                    "rationale": "Core ledger integrity.",
                }
            ],
            "constraints": ["No bank sync in v1"],
            "relatedCode": ["lib/ledger.ts"],
            "openQuestions": ["Should edits keep audit history?"],
            "parentShape": {"path": "docs/planning/work/ideas/personal-finance-app/SHAPE.json"},
            "featureStub": {"path": "docs/planning/work/features/manual-transaction-ledger/FEATURE.json"},
            "shapeFeedback": [
                {
                    "summary": "Split reporting into a later feature.",
                    "suggestedAction": "Keep dashboard work in draft until ledger stabilizes.",
                }
            ],
        }
    )

    assert "# Context: Manual Transaction Ledger" in markdown
    assert "## Parent Links" in markdown
    assert "`docs/planning/work/ideas/personal-finance-app/SHAPE.json`" in markdown
    assert "`docs/planning/work/features/manual-transaction-ledger/FEATURE.json`" in markdown
    assert "## Suggested Shape Feedback" in markdown
    assert "Split reporting into a later feature." in markdown


def test_render_research_preserves_sources_and_recommendation():
    markdown = render.render_research(
        {
            "topic": "Provider strategy",
            "mode": "auto",
            "summary": ["Anthropic-only is simpler initially."],
            "sources": [
                {
                    "type": "repo",
                    "path": "docs/planning/PROJECT.md",
                    "description": "Current project constraints",
                },
                {
                    "type": "web",
                    "url": "https://example.com/spec",
                    "description": "External spec",
                },
            ],
            "recommendation": "Start Anthropic-only and revisit multi-provider later.",
        }
    )

    assert "# Research: Provider strategy" in markdown
    assert "## Sources" in markdown
    assert "`repo`: Current project constraints (docs/planning/PROJECT.md)" in markdown
    assert "`web`: External spec (https://example.com/spec)" in markdown
    assert "Start Anthropic-only and revisit multi-provider later." in markdown


def test_render_review_includes_stage_state_and_final_verdict():
    markdown = render.render_review(
        {
            "timestamp": "2026-03-21T12:00:00Z",
            "branch": "feature/demo",
            "feature": "demo",
            "automated": [
                {"name": "lint", "result": "pass"},
                {"name": "tests", "result": "warn"},
            ],
            "reviewers": ["code-reviewer", "perf-analyzer"],
            "automatedVerdict": "warn",
            "verdict": "pass",
            "stageReviews": [
                {
                    "stage": "spec-compliance",
                    "status": "pass",
                    "findings": [],
                    "evidence": ["plan checked"],
                    "notes": "ok",
                },
                {
                    "stage": "code-quality",
                    "status": "warn",
                    "findings": ["minor issue"],
                    "evidence": ["pytest -q"],
                    "notes": "watch later",
                },
            ],
        }
    )

    assert "# Review Report" in markdown
    assert "## Stage Reviews" in markdown
    assert "### spec-compliance" in markdown
    assert "- Status: `pass`" in markdown
    assert "### code-quality" in markdown
    assert "minor issue" in markdown
    assert "## Final Verdict" in markdown
    assert "**PASS**" in markdown


def test_render_plan_shows_context_links_for_schema_v3_tasks():
    markdown = render.render_plan(
        {
            "schemaVersion": 3,
            "feature": "demo",
            "planNumber": "01",
            "goal": "Tighten auth handler behavior.",
            "tasks": [
                {
                    "name": "Add auth validation",
                    "files": ["internal/auth/handler.go"],
                    "contextLinks": ["Constraint: return 401 on missing auth context"],
                    "microSteps": ["write unauthorized failure test", "implement auth check", "run tests"],
                    "action": "Implement missing auth guard.",
                    "verify": ["go test ./..."],
                    "tdd": {
                        "required": True,
                        "failingVerify": ["go test ./... -run TestUnauthorized"],
                        "passingVerify": ["go test ./... -run TestUnauthorized"],
                    },
                }
            ],
        }
    )

    assert "**Context links:**" in markdown
    assert "Constraint: return 401 on missing auth context" in markdown


def test_render_plan_shows_profile_when_present():
    markdown = render.render_plan(
        {
            "schemaVersion": 3,
            "feature": "demo",
            "planNumber": "01",
            "profile": "migration-rollout",
            "goal": "Tighten auth handler behavior.",
            "tasks": [],
        }
    )

    assert "## Profile" in markdown
    assert "`migration-rollout`" in markdown


def test_render_plan_shows_profile_when_present():
    markdown = render.render_plan(
        {
            "schemaVersion": 3,
            "feature": "demo",
            "planNumber": "01",
            "profile": "migration-rollout",
            "goal": "Tighten auth handler behavior.",
            "tasks": [],
        }
    )

    assert "## Profile" in markdown
    assert "`migration-rollout`" in markdown


def test_render_summary_supports_structured_verification_and_generation_metadata():
    markdown = render.render_summary(
        {
            "schemaVersion": 2,
            "feature": "demo",
            "planNumber": "01",
            "outcome": "complete",
            "changes": [{"file": "app.py", "change": "Add demo handler"}],
            "verification": [
                {
                    "scope": "task",
                    "name": "Add demo handler",
                    "result": "pass",
                    "commands": ["pytest -q tests/test_demo.py -k invalid"],
                    "source": "task-evidence",
                    "timestamp": "2026-03-20T11:59:00Z",
                },
                {
                    "scope": "plan",
                    "name": "planVerify",
                    "result": "pass",
                    "commands": ["pytest -q tests/test_demo.py"],
                    "source": "plan-contract",
                },
            ],
            "commit": {"hash": "abc123", "message": "feat: demo"},
            "generatedFrom": {
                "kind": "workflow_checks.summarize",
                "planPath": "docs/planning/work/features/demo/01-PLAN.json",
                "changedFilesSource": "git:HEAD",
                "taskEvidenceSource": "task-evidence",
                "generatedAt": "2026-03-20T12:00:00Z",
            },
            "notes": ["Generated automatically."],
        }
    )

    assert "task: Add demo handler — pass [task-evidence]" in markdown
    assert "commands: `pytest -q tests/test_demo.py -k invalid`" in markdown
    assert "## Generated From" in markdown
    assert "`workflow_checks.summarize`" in markdown
    assert "## Notes" in markdown
    assert "Generated automatically." in markdown
