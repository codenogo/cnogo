"""Repo-level workflow validation orchestration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def validate_worktree_session(
    root: Path,
    findings: list[Any],
    *,
    load_json: Callable[[Path], Any],
    finding_type: Any,
) -> None:
    """Validate .cnogo/worktree-session.json schema if it exists."""
    session_path = root / ".cnogo" / "worktree-session.json"
    if not session_path.exists():
        return
    try:
        data = load_json(session_path)
    except Exception as exc:
        findings.append(finding_type("ERROR", f"Failed to parse worktree-session.json: {exc}", str(session_path)))
        return
    if not isinstance(data, dict):
        findings.append(finding_type("ERROR", "worktree-session.json must be a JSON object.", str(session_path)))
        return

    valid_phases = {"setup", "executing", "merging", "merged", "verified", "cleaned"}
    valid_worktree_statuses = {"created", "executing", "completed", "merged", "conflict", "cleaned"}

    schema_version = data.get("schemaVersion")
    if not isinstance(schema_version, int):
        findings.append(finding_type("WARN", "worktree-session.json: schemaVersion should be an integer.", str(session_path)))
    for field in ("feature", "planNumber", "baseCommit", "baseBranch"):
        value = data.get(field)
        if not isinstance(value, str):
            findings.append(finding_type("WARN", f"worktree-session.json: {field} should be a string.", str(session_path)))
    phase = data.get("phase")
    if not isinstance(phase, str) or phase not in valid_phases:
        findings.append(
            finding_type("WARN", f"worktree-session.json: phase should be one of {sorted(valid_phases)}.", str(session_path))
        )
    for array_field in ("worktrees", "mergeOrder", "mergedSoFar"):
        value = data.get(array_field)
        if not isinstance(value, list):
            findings.append(finding_type("WARN", f"worktree-session.json: {array_field} should be an array.", str(session_path)))

    worktrees = data.get("worktrees")
    if isinstance(worktrees, list):
        for index, worktree in enumerate(worktrees, start=1):
            if not isinstance(worktree, dict):
                findings.append(
                    finding_type("WARN", f"worktree-session.json: worktrees[{index}] should be an object.", str(session_path))
                )
                continue
            status = worktree.get("status")
            if not isinstance(status, str) or status not in valid_worktree_statuses:
                findings.append(
                    finding_type(
                        "WARN",
                        f"worktree-session.json: worktrees[{index}].status should be one of {sorted(valid_worktree_statuses)}.",
                        str(session_path),
                    )
                )


def build_touched_predicate(
    root: Path,
    findings: list[Any],
    *,
    staged_only: bool,
    is_git_repo: Callable[[Path], bool],
    staged_files: Callable[[Path], list[Path]],
    finding_type: Any,
) -> Callable[[Path], bool] | None:
    """Build the repo touch predicate, optionally constrained to staged files."""
    if not staged_only:
        return lambda _path: True

    if not is_git_repo(root):
        findings.append(finding_type("ERROR", "--staged requires a git repository.", str(root)))
        return None

    staged = [path.resolve() for path in staged_files(root)]
    touched_cache: dict[Path, bool] = {}

    def _contains_path(base: Path, target: Path) -> bool:
        try:
            target.relative_to(base)
            return True
        except ValueError:
            return False

    def touched(path: Path) -> bool:
        resolved = path.resolve()
        cached = touched_cache.get(resolved)
        if cached is not None:
            return cached
        try:
            for staged_path in staged:
                if staged_path == resolved or _contains_path(resolved, staged_path):
                    touched_cache[resolved] = True
                    return True
            touched_cache[resolved] = False
            return False
        except Exception:
            touched_cache[resolved] = False
            return False

    return touched


def validate_repo(
    root: Path,
    *,
    staged_only: bool,
    feature_filter: str | None = None,
    load_workflow_config: Callable[[Path], dict[str, Any]],
    validate_workflow_config: Callable[[dict[str, Any], list[Any], Path], None],
    detect_repo_shape: Callable[[Path, dict[str, Any] | None], dict[str, Any]],
    get_monorepo_scope_level: Callable[[dict[str, Any]], str],
    get_operating_principles_level: Callable[[dict[str, Any]], str],
    get_tdd_mode_level: Callable[[dict[str, Any]], str],
    get_verification_before_completion_level: Callable[[dict[str, Any]], str],
    get_two_stage_review_level: Callable[[dict[str, Any]], str],
    packages_from_cfg: Callable[[dict[str, Any]], list[dict[str, str]]],
    freshness_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    token_budgets_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    bootstrap_context_cfg: Callable[[dict[str, Any]], dict[str, Any]],
    require: Callable[[Path, list[Any], str], None],
    validate_memory_runtime: Callable[[Path, list[Any]], None],
    build_touched: Callable[..., Callable[[Path], bool] | None],
    is_git_repo: Callable[[Path], bool],
    staged_files: Callable[[Path], list[Path]],
    validate_features: Callable[..., None],
    validate_quick_tasks: Callable[[Path, list[Any], Callable[[Path], bool]], None],
    validate_research: Callable[[Path, list[Any], Callable[[Path], bool]], None],
    validate_shape_artifacts: Callable[[Path, list[Any], Callable[[Path], bool]], None],
    validate_worktree_session: Callable[[Path, list[Any]], None],
    validate_token_budgets: Callable[[Path, list[Any], Callable[[Path], bool], dict[str, Any]], None],
    validate_bootstrap_context: Callable[[Path, list[Any], dict[str, Any]], None],
    validate_skills: Callable[[Path, list[Any], Callable[[Path], bool]], None],
    finding_type: Any,
) -> list[Any]:
    findings: list[Any] = []

    cfg = load_workflow_config(root)
    validate_workflow_config(cfg, findings, root)
    shape = detect_repo_shape(root, cfg)
    monorepo_scope_level = get_monorepo_scope_level(cfg)
    operating_principles_level = get_operating_principles_level(cfg)
    tdd_mode_level = get_tdd_mode_level(cfg)
    verification_before_completion_level = get_verification_before_completion_level(cfg)
    two_stage_review_level = get_two_stage_review_level(cfg)
    packages_cfg = packages_from_cfg(cfg)
    freshness = freshness_cfg(cfg)
    token_budgets = token_budgets_cfg(cfg)
    bootstrap_context = bootstrap_context_cfg(cfg)

    require(root / "docs" / "planning" / "PROJECT.md", findings, "Missing planning doc PROJECT.md")
    validate_memory_runtime(root, findings)
    require(root / "docs" / "planning" / "ROADMAP.md", findings, "Missing planning doc ROADMAP.md")

    touched = build_touched(
        root,
        findings,
        staged_only=staged_only,
        is_git_repo=is_git_repo,
        staged_files=staged_files,
        finding_type=finding_type,
    )
    if touched is None:
        return findings

    validate_features(
        root,
        findings,
        touched,
        shape,
        monorepo_scope_level,
        operating_principles_level,
        tdd_mode_level,
        verification_before_completion_level,
        two_stage_review_level,
        packages_cfg,
        freshness,
        feature_filter=feature_filter,
    )
    if feature_filter is None:
        validate_quick_tasks(root, findings, touched)
        validate_research(root, findings, touched)
        validate_shape_artifacts(root, findings, touched)
        validate_worktree_session(root, findings)
        validate_token_budgets(root, findings, touched, token_budgets)
        validate_bootstrap_context(root, findings, bootstrap_context)
        validate_skills(root, findings, touched)

    return findings
