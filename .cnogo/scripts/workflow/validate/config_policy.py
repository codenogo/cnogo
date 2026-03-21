"""Workflow config, budget, bootstrap, and skill validation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable


_SKILL_REF_RE = re.compile(r"`?\.claude/skills/([^`\s]+\.md)`?")
_AGENT_REF_RE = re.compile(r"`?\.claude/agents/([^`\s]+\.md)`?")
_SPAWN_SCOUT_LINE_RE = re.compile(
    r"^- `(?P<name>shape-scout|architecture-scout|risk-challenger)` -> (?P<mapping>.+)$",
    re.MULTILINE,
)


def validate_workflow_config(
    cfg: dict[str, Any],
    findings: list[Any],
    root: Path,
    *,
    is_positive_int: Any,
    finding_type: Any,
) -> None:
    """Minimal validation of WORKFLOW.json without external dependencies."""
    cfg_path = root / "docs" / "planning" / "WORKFLOW.json"

    version = cfg.get("version")
    if not isinstance(version, int) or version < 1:
        findings.append(finding_type("WARN", "WORKFLOW.json: 'version' should be an integer >= 1.", str(cfg_path)))

    repo_shape = cfg.get("repoShape")
    if repo_shape not in {"auto", "single", "monorepo", "polyglot"}:
        findings.append(
            finding_type(
                "WARN",
                "WORKFLOW.json: 'repoShape' should be one of auto|single|monorepo|polyglot.",
                str(cfg_path),
            )
        )

    perf = cfg.get("performance")
    if perf is not None and not isinstance(perf, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'performance' should be an object.", str(cfg_path)))
    elif isinstance(perf, dict):
        pef = perf.get("postEditFormat", "auto")
        if pef not in {"auto", "off"}:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.postEditFormat should be auto|off.", str(cfg_path))
            )
        scope = perf.get("postEditFormatScope", "changed")
        if scope not in {"changed", "repo"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: performance.postEditFormatScope should be changed|repo.",
                    str(cfg_path),
                )
            )
        check_scope = perf.get("checkScope", "auto")
        if check_scope not in {"auto", "changed", "all"}:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.checkScope should be auto|changed|all.", str(cfg_path))
            )
        changed_fallback = perf.get("changedFilesFallback", "none")
        if changed_fallback not in {"none", "head"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: performance.changedFilesFallback should be none|head.",
                    str(cfg_path),
                )
            )
        timeout = perf.get("commandTimeoutSec")
        if timeout is not None and not is_positive_int(timeout):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.commandTimeoutSec should be an integer > 0.", str(cfg_path))
            )

        budgets = perf.get("tokenBudgets")
        if budgets is not None and not isinstance(budgets, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.tokenBudgets should be an object.", str(cfg_path))
            )
        elif isinstance(budgets, dict):
            enabled = budgets.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type("WARN", "WORKFLOW.json: performance.tokenBudgets.enabled should be boolean.", str(cfg_path))
                )
            for key in (
                "commandWordMax",
                "commandsTotalWordMax",
                "contextWordMax",
                "planWordMax",
                "summaryWordMax",
                "reviewWordMax",
                "researchWordMax",
                "shapeWordMax",
                "brainstormWordMax",
            ):
                value = budgets.get(key)
                if value is not None and not is_positive_int(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"WORKFLOW.json: performance.tokenBudgets.{key} should be an integer > 0.",
                            str(cfg_path),
                        )
                    )

        compaction = perf.get("outputCompaction")
        if compaction is not None and not isinstance(compaction, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.outputCompaction should be an object.", str(cfg_path))
            )
        elif isinstance(compaction, dict):
            enabled = compaction.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.outputCompaction.enabled should be boolean.",
                        str(cfg_path),
                    )
                )
            dedupe = compaction.get("dedupe")
            if dedupe is not None and not isinstance(dedupe, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.outputCompaction.dedupe should be boolean.",
                        str(cfg_path),
                    )
                )
            for key in ("maxLines", "failTailLines", "passLines"):
                value = compaction.get(key)
                if value is not None and not is_positive_int(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"WORKFLOW.json: performance.outputCompaction.{key} should be an integer > 0.",
                            str(cfg_path),
                        )
                    )

        recovery = perf.get("outputRecovery")
        if recovery is not None and not isinstance(recovery, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.outputRecovery should be an object.", str(cfg_path))
            )
        elif isinstance(recovery, dict):
            enabled = recovery.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.outputRecovery.enabled should be boolean.",
                        str(cfg_path),
                    )
                )
            mode = recovery.get("mode")
            if mode is not None and mode not in {"failures", "always", "never"}:
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.outputRecovery.mode should be failures|always|never.",
                        str(cfg_path),
                    )
                )
            directory = recovery.get("directory")
            if directory is not None and (not isinstance(directory, str) or not directory.strip()):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.outputRecovery.directory should be a non-empty string.",
                        str(cfg_path),
                    )
                )
            for key in ("minChars", "maxFiles", "maxFileSize"):
                value = recovery.get(key)
                if value is not None and not is_positive_int(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"WORKFLOW.json: performance.outputRecovery.{key} should be an integer > 0.",
                            str(cfg_path),
                        )
                    )

        telemetry = perf.get("tokenTelemetry")
        if telemetry is not None and not isinstance(telemetry, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.tokenTelemetry should be an object.", str(cfg_path))
            )
        elif isinstance(telemetry, dict):
            enabled = telemetry.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.tokenTelemetry.enabled should be boolean.",
                        str(cfg_path),
                    )
                )

        hook_opt = perf.get("hookOptimization")
        if hook_opt is not None and not isinstance(hook_opt, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.hookOptimization should be an object.", str(cfg_path))
            )
        elif isinstance(hook_opt, dict):
            enabled = hook_opt.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.hookOptimization.enabled should be boolean.",
                        str(cfg_path),
                    )
                )
            mode = hook_opt.get("mode")
            if mode is not None and mode not in {"suggest", "enforce", "off"}:
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.hookOptimization.mode should be suggest|enforce|off.",
                        str(cfg_path),
                    )
                )
            show = hook_opt.get("showSuggestions")
            if show is not None and not isinstance(show, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.hookOptimization.showSuggestions should be boolean.",
                        str(cfg_path),
                    )
                )
            log_file = hook_opt.get("logFile")
            if log_file is not None and (not isinstance(log_file, str) or not log_file.strip()):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.hookOptimization.logFile should be a non-empty string.",
                        str(cfg_path),
                    )
                )

        bootstrap = perf.get("bootstrapContext")
        if bootstrap is not None and not isinstance(bootstrap, dict):
            findings.append(
                finding_type("WARN", "WORKFLOW.json: performance.bootstrapContext should be an object.", str(cfg_path))
            )
        elif isinstance(bootstrap, dict):
            enabled = bootstrap.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: performance.bootstrapContext.enabled should be boolean.",
                        str(cfg_path),
                    )
                )
            for key in ("rootClaudeWordMax", "workflowClaudeWordMax", "commandSetWordMax"):
                value = bootstrap.get(key)
                if value is not None and not is_positive_int(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"WORKFLOW.json: performance.bootstrapContext.{key} should be an integer > 0.",
                            str(cfg_path),
                        )
                    )

    enforcement = cfg.get("enforcement")
    if enforcement is not None and not isinstance(enforcement, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'enforcement' should be an object.", str(cfg_path)))
    elif isinstance(enforcement, dict):
        monorepo_verify_scope = enforcement.get("monorepoVerifyScope", "warn")
        if monorepo_verify_scope not in {"warn", "error"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: enforcement.monorepoVerifyScope should be warn|error.",
                    str(cfg_path),
                )
            )
        operating_principles = enforcement.get("operatingPrinciples", "warn")
        if operating_principles not in {"off", "warn", "error"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: enforcement.operatingPrinciples should be off|warn|error.",
                    str(cfg_path),
                )
            )
        tdd_mode = enforcement.get("tddMode", "error")
        if tdd_mode not in {"off", "warn", "error"}:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: enforcement.tddMode should be off|warn|error.", str(cfg_path))
            )
        verification = enforcement.get("verificationBeforeCompletion", "error")
        if verification not in {"off", "warn", "error"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: enforcement.verificationBeforeCompletion should be off|warn|error.",
                    str(cfg_path),
                )
            )
        two_stage_review = enforcement.get("twoStageReview", "error")
        if two_stage_review not in {"off", "warn", "error"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: enforcement.twoStageReview should be off|warn|error.",
                    str(cfg_path),
                )
            )
        ownership = enforcement.get("taskOwnership", "error")
        if ownership not in {"off", "warn", "error"}:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: enforcement.taskOwnership should be off|warn|error.", str(cfg_path))
            )

    packages = cfg.get("packages")
    if packages is not None and not isinstance(packages, list):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'packages' should be an array.", str(cfg_path)))
    elif isinstance(packages, list):
        for idx, package in enumerate(packages, start=1):
            if not isinstance(package, dict):
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: packages[{idx}] should be an object.", str(cfg_path))
                )
                continue
            path = package.get("path")
            if not isinstance(path, str) or not path.strip():
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: packages[{idx}].path is required.", str(cfg_path))
                )
                continue
            if not (root / path).exists():
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: packages[{idx}].path does not exist: {path}", str(cfg_path))
                )
            commands = package.get("commands")
            if commands is not None and not isinstance(commands, dict):
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: packages[{idx}].commands should be an object.", str(cfg_path))
                )
            elif isinstance(commands, dict):
                for key in ["build", "test", "lint", "format", "typecheck", "run"]:
                    value = commands.get(key)
                    if value is not None and (not isinstance(value, str) or not value.strip()):
                        findings.append(
                            finding_type(
                                "WARN",
                                f"WORKFLOW.json: packages[{idx}].commands.{key} should be a non-empty string.",
                                str(cfg_path),
                            )
                        )

    research = cfg.get("research")
    if research is not None and not isinstance(research, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'research' should be an object.", str(cfg_path)))
    elif isinstance(research, dict):
        mode = research.get("mode", "auto")
        if mode not in {"off", "local", "mcp", "web", "auto"}:
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: research.mode should be off|local|mcp|web|auto.",
                    str(cfg_path),
                )
            )
        min_sources = research.get("minSources", 0)
        if not isinstance(min_sources, int) or min_sources < 0:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: research.minSources should be an integer >= 0.", str(cfg_path))
            )

    agent_teams = cfg.get("agentTeams")
    if agent_teams is not None and not isinstance(agent_teams, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'agentTeams' should be an object.", str(cfg_path)))
    elif isinstance(agent_teams, dict):
        stale_indicator = agent_teams.get("staleIndicatorMinutes")
        if stale_indicator is not None and not is_positive_int(stale_indicator):
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: agentTeams.staleIndicatorMinutes should be an integer > 0.",
                    str(cfg_path),
                )
            )
        max_takeovers = agent_teams.get("maxTakeoversPerTask")
        if max_takeovers is not None and not is_positive_int(max_takeovers, allow_zero=True):
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: agentTeams.maxTakeoversPerTask should be an integer >= 0.",
                    str(cfg_path),
                )
            )
        worktree_mode = agent_teams.get("worktreeMode")
        if worktree_mode is not None:
            if isinstance(worktree_mode, bool) or not isinstance(worktree_mode, str) or worktree_mode not in ("always", "off"):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: agentTeams.worktreeMode should be 'always' or 'off'.",
                        str(cfg_path),
                    )
                )
        default_compositions = agent_teams.get("defaultCompositions")
        if default_compositions is not None and not isinstance(default_compositions, dict):
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: agentTeams.defaultCompositions should be an object.",
                    str(cfg_path),
                )
            )
        elif isinstance(default_compositions, dict):
            agents_dir = root / ".claude" / "agents"
            for composition_name, members in default_compositions.items():
                if not isinstance(members, list) or not members:
                    findings.append(
                        finding_type(
                            "WARN",
                            f"WORKFLOW.json: agentTeams.defaultCompositions.{composition_name} should be a non-empty array of agent names.",
                            str(cfg_path),
                        )
                    )
                    continue
                normalized_members: list[str] = []
                for idx, member in enumerate(members, start=1):
                    if not isinstance(member, str) or not member.strip():
                        findings.append(
                            finding_type(
                                "WARN",
                                f"WORKFLOW.json: agentTeams.defaultCompositions.{composition_name}[{idx}] should be a non-empty string.",
                                str(cfg_path),
                            )
                        )
                        continue
                    agent_name = member.strip()
                    normalized_members.append(agent_name)
                    if not (agents_dir / f"{agent_name}.md").exists():
                        findings.append(
                            finding_type(
                                "WARN",
                                f"WORKFLOW.json: agentTeams.defaultCompositions.{composition_name}[{idx}] references missing agent {agent_name!r}.",
                                str(cfg_path),
                            )
                        )
                existing_unique_members = {
                    agent_name
                    for agent_name in normalized_members
                    if (agents_dir / f"{agent_name}.md").exists()
                }
                if composition_name == "review" and len(existing_unique_members) < 2:
                    findings.append(
                        finding_type(
                            "WARN",
                            "WORKFLOW.json: agentTeams.defaultCompositions.review should use at least 2 distinct reviewer agents.",
                            str(cfg_path),
                        )
                    )

    freshness = cfg.get("freshness")
    if freshness is not None and not isinstance(freshness, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'freshness' should be an object.", str(cfg_path)))
    elif isinstance(freshness, dict):
        enabled = freshness.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            findings.append(finding_type("WARN", "WORKFLOW.json: freshness.enabled should be boolean.", str(cfg_path)))
        for key in ("contextMaxAgeDays", "planMaxAgeDaysWithoutSummary", "summaryMaxAgeDaysWithoutReview"):
            value = freshness.get(key)
            if value is not None and not is_positive_int(value, allow_zero=True):
                findings.append(
                    finding_type(
                        "WARN",
                        f"WORKFLOW.json: freshness.{key} should be an integer >= 0.",
                        str(cfg_path),
                    )
                )

    invariants = cfg.get("invariants")
    if invariants is not None and not isinstance(invariants, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'invariants' should be an object.", str(cfg_path)))
    elif isinstance(invariants, dict):
        enabled = invariants.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            findings.append(finding_type("WARN", "WORKFLOW.json: invariants.enabled should be boolean.", str(cfg_path)))
        scope = invariants.get("scanScope")
        if scope is not None and scope not in {"changed", "repo"}:
            findings.append(
                finding_type("WARN", "WORKFLOW.json: invariants.scanScope should be changed|repo.", str(cfg_path))
            )
        for key in ("maxFileLines", "maxLineLength"):
            value = invariants.get(key)
            if value is not None and not is_positive_int(value):
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: invariants.{key} should be an integer > 0.", str(cfg_path))
                )
        exceptions = invariants.get("maxFileLinesExceptions")
        if exceptions is not None:
            if not isinstance(exceptions, list):
                findings.append(
                    finding_type(
                        "WARN",
                        "WORKFLOW.json: invariants.maxFileLinesExceptions should be an array of path patterns.",
                        str(cfg_path),
                    )
                )
            else:
                for idx, item in enumerate(exceptions, start=1):
                    if not isinstance(item, str) or not item.strip():
                        findings.append(
                            finding_type(
                                "WARN",
                                f"WORKFLOW.json: invariants.maxFileLinesExceptions[{idx}] should be a non-empty string.",
                                str(cfg_path),
                            )
                        )
        forbidden_import_patterns = invariants.get("forbiddenImportPatterns")
        if forbidden_import_patterns is not None and not isinstance(forbidden_import_patterns, list):
            findings.append(
                finding_type(
                    "WARN",
                    "WORKFLOW.json: invariants.forbiddenImportPatterns should be an array.",
                    str(cfg_path),
                )
            )

    entropy = cfg.get("entropy")
    if entropy is not None and not isinstance(entropy, dict):
        findings.append(finding_type("WARN", "WORKFLOW.json: 'entropy' should be an object.", str(cfg_path)))
    elif isinstance(entropy, dict):
        enabled = entropy.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            findings.append(finding_type("WARN", "WORKFLOW.json: entropy.enabled should be boolean.", str(cfg_path)))
        mode = entropy.get("mode")
        if mode is not None and mode not in {"background", "manual"}:
            findings.append(finding_type("WARN", "WORKFLOW.json: entropy.mode should be background|manual.", str(cfg_path)))
        for key in ("maxFilesPerTask", "maxTasksPerRun"):
            value = entropy.get(key)
            if value is not None and not is_positive_int(value):
                findings.append(
                    finding_type("WARN", f"WORKFLOW.json: entropy.{key} should be an integer > 0.", str(cfg_path))
                )


def validate_token_budgets(
    root: Path,
    findings: list[Any],
    touched: Callable[[Path], bool],
    budgets: dict[str, Any],
    *,
    default_token_budgets: dict[str, int],
    iter_feature_dirs: Any,
    iter_quick_dirs: Any,
    iter_research_dirs: Any,
    iter_ideas_dirs: Any,
    word_count: Any,
    finding_type: Any,
) -> None:
    """Warn on markdown artifacts that exceed configured word budgets."""
    if not budgets.get("enabled", True):
        return

    command_word_max = int(budgets.get("commandWordMax", default_token_budgets["commandWordMax"]))
    commands_total_word_max = int(budgets.get("commandsTotalWordMax", default_token_budgets["commandsTotalWordMax"]))
    context_word_max = int(budgets.get("contextWordMax", default_token_budgets["contextWordMax"]))
    plan_word_max = int(budgets.get("planWordMax", default_token_budgets["planWordMax"]))
    summary_word_max = int(budgets.get("summaryWordMax", default_token_budgets["summaryWordMax"]))
    review_word_max = int(budgets.get("reviewWordMax", default_token_budgets["reviewWordMax"]))
    research_word_max = int(budgets.get("researchWordMax", default_token_budgets["researchWordMax"]))
    shape_word_max = int(
        budgets.get("shapeWordMax", budgets.get("brainstormWordMax", default_token_budgets["shapeWordMax"]))
    )
    brainstorm_word_max = int(budgets.get("brainstormWordMax", default_token_budgets["brainstormWordMax"]))

    word_cache: dict[Path, int] = {}

    def words_for(path: Path) -> int:
        cached = word_cache.get(path)
        if cached is not None:
            return cached
        value = word_count(path)
        word_cache[path] = value
        return value

    def check_path(path: Path, max_words: int, label: str) -> None:
        if not path.exists() or not path.is_file() or not touched(path):
            return
        words = words_for(path)
        if words > max_words:
            findings.append(
                finding_type(
                    "WARN",
                    f"{label} is {words} words (budget {max_words}). Consider trimming for context efficiency.",
                    str(path),
                )
            )

    cmd_dir = root / ".claude" / "commands"
    command_files = sorted(path for path in cmd_dir.glob("*.md") if path.is_file())
    command_total = 0
    any_command_touched = False
    for path in command_files:
        words = words_for(path)
        command_total += words
        if touched(path):
            any_command_touched = True
            if words > command_word_max:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Command artifact is {words} words (budget {command_word_max}). Consider trimming for context efficiency.",
                        str(path),
                    )
                )
    if any_command_touched and command_total > commands_total_word_max:
        findings.append(
            finding_type(
                "WARN",
                f"Command artifact set totals {command_total} words (budget {commands_total_word_max}).",
                str(cmd_dir),
            )
        )

    for feature_dir in iter_feature_dirs(root):
        if not touched(feature_dir):
            continue
        check_path(feature_dir / "FEATURE.md", context_word_max, "Feature stub artifact")
        check_path(feature_dir / "CONTEXT.md", context_word_max, "Feature CONTEXT artifact")
        check_path(feature_dir / "REVIEW.md", review_word_max, "Feature REVIEW artifact")
        for plan in feature_dir.glob("*-PLAN.md"):
            check_path(plan, plan_word_max, "Feature PLAN artifact")
        for summary in feature_dir.glob("*-SUMMARY.md"):
            check_path(summary, summary_word_max, "Feature SUMMARY artifact")

    quick_root = root / "docs" / "planning" / "work" / "quick"
    if quick_root.exists() and touched(quick_root):
        for quick_dir in iter_quick_dirs(root):
            if not touched(quick_dir):
                continue
            check_path(quick_dir / "PLAN.md", plan_word_max, "Quick PLAN artifact")
            check_path(quick_dir / "SUMMARY.md", summary_word_max, "Quick SUMMARY artifact")

    for research_dir in iter_research_dirs(root):
        if not touched(research_dir):
            continue
        check_path(research_dir / "RESEARCH.md", research_word_max, "Research artifact")
    for idea_dir in iter_ideas_dirs(root):
        if not touched(idea_dir):
            continue
        check_path(idea_dir / "SHAPE.md", shape_word_max, "Shape artifact")
        check_path(idea_dir / "BRAINSTORM.md", brainstorm_word_max, "Brainstorm artifact")


def validate_bootstrap_context(
    root: Path,
    findings: list[Any],
    bootstrap_cfg: dict[str, Any],
    *,
    default_bootstrap_context: dict[str, int],
    word_count: Any,
    finding_type: Any,
) -> None:
    """Always-on checks for baseline context footprint."""
    if not bootstrap_cfg.get("enabled", True):
        return

    checks = [
        (
            root / "CLAUDE.md",
            int(bootstrap_cfg.get("rootClaudeWordMax", default_bootstrap_context["rootClaudeWordMax"])),
            "Root CLAUDE.md",
        ),
        (
            root / ".claude" / "CLAUDE.md",
            int(bootstrap_cfg.get("workflowClaudeWordMax", default_bootstrap_context["workflowClaudeWordMax"])),
            "Workflow CLAUDE.md",
        ),
    ]
    for path, max_words, label in checks:
        if not path.exists() or not path.is_file():
            continue
        words = word_count(path)
        if words > max_words:
            findings.append(
                finding_type(
                    "WARN",
                    f"{label} is {words} words (budget {max_words}). Consider slimming baseline context.",
                    str(path),
                )
            )

    command_set_word_max = int(
        bootstrap_cfg.get("commandSetWordMax", default_bootstrap_context["commandSetWordMax"])
    )
    cmd_dir = root / ".claude" / "commands"
    if cmd_dir.exists() and cmd_dir.is_dir():
        total = 0
        for path in cmd_dir.glob("*.md"):
            if path.is_file():
                total += word_count(path)
        if total > command_set_word_max:
            findings.append(
                finding_type(
                    "WARN",
                    f"Command artifact set totals {total} words (bootstrap budget {command_set_word_max}).",
                    str(cmd_dir),
                )
            )


def validate_skills(
    root: Path,
    findings: list[Any],
    touched: Callable[[Path], bool],
    *,
    iter_skill_paths: Any,
    parse_skill_frontmatter: Any,
    finding_type: Any,
) -> None:
    """Validate skill/agent frontmatter and command cross-references."""
    skills_dir = root / ".claude" / "skills"
    if skills_dir.is_dir():
        for md_path in iter_skill_paths(skills_dir):
            if not touched(md_path):
                continue
            info = parse_skill_frontmatter(md_path)
            if info["name"] is None:
                findings.append(
                    finding_type("WARN", "Skill file missing frontmatter 'name' field.", str(md_path))
                )

    agents_dir = root / ".claude" / "agents"
    if agents_dir.is_dir():
        for md_path in sorted(agents_dir.glob("*.md")):
            if not touched(md_path):
                continue
            info = parse_skill_frontmatter(md_path)
            if info["name"] is None:
                findings.append(
                    finding_type("WARN", "Agent file missing frontmatter 'name' field.", str(md_path))
                )

    cmd_dir = root / ".claude" / "commands"
    if not cmd_dir.is_dir():
        return
    for cmd_path in sorted(cmd_dir.glob("*.md")):
        if not touched(cmd_path):
            continue
        try:
            text = cmd_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for match in _SKILL_REF_RE.finditer(text):
            skill_file = match.group(1)
            skill_path = root / ".claude" / "skills" / skill_file
            if not skill_path.exists():
                findings.append(
                    finding_type(
                        "WARN",
                        f"Skill reference '.claude/skills/{skill_file}' not found.",
                        str(cmd_path),
                    )
                )
        for match in _AGENT_REF_RE.finditer(text):
            agent_file = match.group(1)
            agent_path = root / ".claude" / "agents" / agent_file
            if not agent_path.exists():
                findings.append(
                    finding_type(
                        "WARN",
                        f"Agent reference '.claude/agents/{agent_file}' not found.",
                        str(cmd_path),
                    )
                )
        if cmd_path.name == "spawn.md":
            for match in _SPAWN_SCOUT_LINE_RE.finditer(text):
                mapping = match.group("mapping")
                if ".claude/skills/" in mapping:
                    findings.append(
                        finding_type(
                            "WARN",
                            f"Scout specialization `{match.group('name')}` should map only to a read-only agent, not shared skills.",
                            str(cmd_path),
                        )
                    )
        if cmd_path.name == "shape.md" and "/spawn research <task>" in text:
            findings.append(
                finding_type(
                    "WARN",
                    "Shape workspace should use `/research` directly instead of `/spawn research <task>` to preserve a single-writer flow.",
                    str(cmd_path),
                )
            )
