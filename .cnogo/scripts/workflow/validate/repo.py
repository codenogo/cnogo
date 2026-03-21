"""Repo-level workflow validation orchestration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scripts.workflow.orchestration import (
    DELIVERY_INTEGRATION_STATUSES,
    DELIVERY_REVIEW_READINESS_STATUSES,
    DELIVERY_REVIEW_STAGE_STATUSES,
    DELIVERY_REVIEW_STATUSES,
    DELIVERY_REVIEW_STAGES,
    DELIVERY_REVIEW_VERDICTS,
    DELIVERY_RUN_STATUSES,
    DELIVERY_SHIP_STATUSES,
    DELIVERY_TASK_STATUSES,
    SCHEDULER_STATE_SCHEMA_VERSION,
    WATCH_STATE_SCHEMA_VERSION,
    WORK_ORDER_STATUSES,
)
from scripts.workflow.shared.profiles import is_profile_name


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
    run_id = data.get("runId")
    if run_id is not None and not isinstance(run_id, str):
        findings.append(finding_type("WARN", "worktree-session.json: runId should be a string.", str(session_path)))
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


def validate_watch_runtime(
    root: Path,
    findings: list[Any],
    touched: Callable[[Path], bool],
    *,
    load_json: Callable[[Path], Any],
    finding_type: Any,
) -> None:
    state_path = root / ".cnogo" / "watch" / "state.json"
    if not state_path.exists() or not touched(state_path):
        return
    try:
        data = load_json(state_path)
    except Exception as exc:
        findings.append(finding_type("ERROR", f"Failed to parse watch state: {exc}", str(state_path)))
        return
    if not isinstance(data, dict):
        findings.append(finding_type("ERROR", "Watch state must be a JSON object.", str(state_path)))
        return

    schema_version = data.get("schemaVersion")
    if not isinstance(schema_version, int):
        findings.append(finding_type("WARN", "Watch state schemaVersion should be an integer.", str(state_path)))
    elif schema_version != WATCH_STATE_SCHEMA_VERSION:
        findings.append(
            finding_type(
                "WARN",
                f"Watch state schemaVersion {schema_version} does not match expected {WATCH_STATE_SCHEMA_VERSION}.",
                str(state_path),
            )
        )

    enabled = data.get("enabled")
    if enabled is not None and not isinstance(enabled, bool):
        findings.append(finding_type("WARN", "Watch state enabled should be boolean.", str(state_path)))
    for key in ("patrolIntervalMinutes", "historyLimit", "attentionLimit"):
        value = data.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value <= 0):
            findings.append(
                finding_type("WARN", f"Watch state {key} should be an integer > 0.", str(state_path))
            )
    for key in (
        "lastPatrolAt",
        "nextPatrolAt",
        "lastResult",
        "lastReportPath",
        "lastAttentionPath",
        "lastSnapshotPath",
    ):
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            findings.append(finding_type("WARN", f"Watch state {key} should be a string.", str(state_path)))

    last_result = data.get("lastResult")
    if isinstance(last_result, str) and last_result not in {"ok", "warn", "fail"}:
        findings.append(
            finding_type("WARN", "Watch state lastResult should be ok|warn|fail.", str(state_path))
        )

    for key in ("lastAttentionSummary", "lastDeltaSummary"):
        value = data.get(key)
        if value is not None and not isinstance(value, dict):
            findings.append(finding_type("WARN", f"Watch state {key} should be an object.", str(state_path)))

    for key in ("lastReportPath", "lastAttentionPath", "lastSnapshotPath"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        resolved = Path(value)
        if not resolved.is_absolute():
            resolved = root / resolved
        if not resolved.exists():
            findings.append(
                finding_type("WARN", f"Watch state {key} points to missing file {value!r}.", str(state_path))
            )


def validate_delivery_runs(
    root: Path,
    findings: list[Any],
    touched: Callable[[Path], bool],
    *,
    feature_filter: str | None = None,
    load_json: Callable[[Path], Any],
    finding_type: Any,
) -> None:
    runs_root = root / ".cnogo" / "runs"
    target_dirs = []
    if runs_root.is_dir():
        if feature_filter:
            target_dir = runs_root / feature_filter
            if target_dir.exists():
                target_dirs.append(target_dir)
        else:
            target_dirs = [path for path in runs_root.iterdir() if path.is_dir()]

    run_ids_by_feature: dict[str, set[str]] = {}
    for feature_dir in target_dirs:
        if not touched(feature_dir):
            continue
        run_ids_by_feature[feature_dir.name] = set()
        for run_path in sorted(feature_dir.glob("*.json")):
            if not touched(run_path):
                continue
            try:
                contract = load_json(run_path)
            except Exception as exc:
                findings.append(
                    finding_type("ERROR", f"Failed to parse delivery run: {exc}", str(run_path))
                )
                continue
            if not isinstance(contract, dict):
                findings.append(
                    finding_type("ERROR", "Delivery run artifact must be a JSON object.", str(run_path))
                )
                continue

            run_id = contract.get("runId")
            if isinstance(run_id, str) and run_id.strip():
                run_ids_by_feature[feature_dir.name].add(run_id.strip())
            else:
                findings.append(
                    finding_type("WARN", "Delivery run should include non-empty runId.", str(run_path))
                )

            schema_version = contract.get("schemaVersion")
            if not isinstance(schema_version, int):
                findings.append(
                    finding_type("WARN", "Delivery run schemaVersion should be an integer.", str(run_path))
                )

            feature = contract.get("feature")
            if not isinstance(feature, str) or not feature.strip():
                findings.append(
                    finding_type("WARN", "Delivery run should include non-empty feature.", str(run_path))
                )
            elif feature.strip() != feature_dir.name:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Delivery run feature {feature!r} does not match directory slug {feature_dir.name!r}.",
                        str(run_path),
                    )
                )

            plan_number = contract.get("planNumber")
            if not isinstance(plan_number, str) or not plan_number.strip():
                findings.append(
                    finding_type("WARN", "Delivery run should include non-empty planNumber.", str(run_path))
                )

            mode = contract.get("mode")
            if mode not in {"serial", "team"}:
                findings.append(
                    finding_type("WARN", "Delivery run mode should be serial|team.", str(run_path))
                )

            status = contract.get("status")
            if status not in DELIVERY_RUN_STATUSES:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Delivery run status should be one of {sorted(DELIVERY_RUN_STATUSES)}.",
                        str(run_path),
                    )
                )

            for field in ("startedBy", "branch", "planPath", "summaryPath", "reviewPath", "createdAt", "updatedAt"):
                value = contract.get(field)
                if value is not None and not isinstance(value, str):
                    findings.append(
                        finding_type("WARN", f"Delivery run {field} should be a string when present.", str(run_path))
                    )

            plan_path = contract.get("planPath")
            if isinstance(plan_path, str) and plan_path.strip():
                resolved_plan = root / plan_path
                if not resolved_plan.exists():
                    findings.append(
                        finding_type(
                            "WARN",
                            f"Delivery run planPath not found: {plan_path}",
                            str(run_path),
                        )
                    )

            recommendation = contract.get("recommendation")
            if recommendation is not None and not isinstance(recommendation, dict):
                findings.append(
                    finding_type("WARN", "Delivery run recommendation should be an object.", str(run_path))
                )

            profile = contract.get("profile")
            if profile is not None:
                if not isinstance(profile, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run profile should be an object.", str(run_path))
                    )
                else:
                    name = profile.get("name")
                    if not isinstance(name, str) or not name.strip():
                        findings.append(
                            finding_type("WARN", "Delivery run profile.name should be non-empty.", str(run_path))
                        )
                    version = profile.get("version")
                    if version is not None and not isinstance(version, str):
                        findings.append(
                            finding_type("WARN", "Delivery run profile.version should be a string.", str(run_path))
                        )
                    source = profile.get("source")
                    if source is not None and not isinstance(source, str):
                        findings.append(
                            finding_type("WARN", "Delivery run profile.source should be a string.", str(run_path))
                        )
                    resolved_policy = profile.get("resolvedPolicy")
                    if resolved_policy is not None and not isinstance(resolved_policy, dict):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run profile.resolvedPolicy should be an object.",
                                str(run_path),
                            )
                        )

            formula = contract.get("formula")
            if formula is not None:
                if not isinstance(formula, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run formula should be an object.", str(run_path))
                    )
                else:
                    name = formula.get("name")
                    if not isinstance(name, str) or not name.strip():
                        findings.append(
                            finding_type("WARN", "Delivery run formula.name should be non-empty.", str(run_path))
                        )
                    version = formula.get("version")
                    if version is not None and not isinstance(version, str):
                        findings.append(
                            finding_type("WARN", "Delivery run formula.version should be a string.", str(run_path))
                        )
                    source = formula.get("source")
                    if source is not None and not isinstance(source, str):
                        findings.append(
                            finding_type("WARN", "Delivery run formula.source should be a string.", str(run_path))
                        )
                    resolved_policy = formula.get("resolvedPolicy")
                    if resolved_policy is not None and not isinstance(resolved_policy, dict):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run formula.resolvedPolicy should be an object.",
                                str(run_path),
                            )
                        )

            integration = contract.get("integration")
            if integration is not None:
                if not isinstance(integration, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run integration should be an object.", str(run_path))
                    )
                else:
                    status_value = integration.get("status")
                    if status_value not in DELIVERY_INTEGRATION_STATUSES:
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run integration.status should be one of "
                                f"{sorted(DELIVERY_INTEGRATION_STATUSES)}.",
                                str(run_path),
                            )
                        )
                    for list_field in (
                        "mergedTaskIndices",
                        "awaitingMergeTaskIndices",
                        "activeTaskIndices",
                        "conflictFiles",
                    ):
                        value = integration.get(list_field)
                        if value is not None and not isinstance(value, list):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run integration.{list_field} should be an array.",
                                    str(run_path),
                                )
                            )
                    conflict_task_index = integration.get("conflictTaskIndex")
                    if conflict_task_index is not None and not isinstance(conflict_task_index, int):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run integration.conflictTaskIndex should be an integer when present.",
                                str(run_path),
                            )
                        )
                    for field in ("lastSessionPhase", "updatedAt"):
                        value = integration.get(field)
                        if value is not None and not isinstance(value, str):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run integration.{field} should be a string when present.",
                                    str(run_path),
                                )
                            )

            review_readiness = contract.get("reviewReadiness")
            if review_readiness is not None:
                if not isinstance(review_readiness, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run reviewReadiness should be an object.", str(run_path))
                    )
                else:
                    status_value = review_readiness.get("status")
                    if status_value not in DELIVERY_REVIEW_READINESS_STATUSES:
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run reviewReadiness.status should be one of "
                                f"{sorted(DELIVERY_REVIEW_READINESS_STATUSES)}.",
                                str(run_path),
                            )
                        )
                    plan_verify_passed = review_readiness.get("planVerifyPassed")
                    if plan_verify_passed is not None and not isinstance(plan_verify_passed, bool):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run reviewReadiness.planVerifyPassed should be a boolean when present.",
                                str(run_path),
                            )
                        )
                    for list_field in ("verifiedCommands", "notes"):
                        value = review_readiness.get(list_field)
                        if value is not None and not isinstance(value, list):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run reviewReadiness.{list_field} should be an array.",
                                    str(run_path),
                                )
                            )
                    for field in ("verifiedAt", "updatedAt"):
                        value = review_readiness.get(field)
                        if value is not None and not isinstance(value, str):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run reviewReadiness.{field} should be a string when present.",
                                    str(run_path),
                                )
                            )

            review_state = contract.get("review")
            if review_state is not None:
                if not isinstance(review_state, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run review should be an object.", str(run_path))
                    )
                else:
                    review_status = review_state.get("status")
                    if review_status not in DELIVERY_REVIEW_STATUSES:
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run review.status should be one of "
                                f"{sorted(DELIVERY_REVIEW_STATUSES)}.",
                                str(run_path),
                            )
                        )
                    for field in ("automatedVerdict", "finalVerdict"):
                        value = review_state.get(field)
                        if value not in DELIVERY_REVIEW_VERDICTS:
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run review.{field} should be one of {sorted(DELIVERY_REVIEW_VERDICTS)}.",
                                    str(run_path),
                                )
                            )
                    reviewers = review_state.get("reviewers")
                    if reviewers is not None and not isinstance(reviewers, list):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run review.reviewers should be an array.",
                                str(run_path),
                            )
                        )
                    stages = review_state.get("stages")
                    if stages is not None:
                        if not isinstance(stages, list):
                            findings.append(
                                finding_type("WARN", "Delivery run review.stages should be an array.", str(run_path))
                            )
                        else:
                            expected_stages = list(DELIVERY_REVIEW_STAGES)
                            if len(stages) < len(expected_stages):
                                findings.append(
                                    finding_type(
                                        "WARN",
                                        "Delivery run review.stages should include spec-compliance and code-quality.",
                                        str(run_path),
                                    )
                                )
                            for index, expected_stage in enumerate(expected_stages):
                                if index >= len(stages):
                                    break
                                stage = stages[index]
                                if not isinstance(stage, dict):
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            f"Delivery run review.stages[{index}] should be an object.",
                                            str(run_path),
                                        )
                                    )
                                    continue
                                if stage.get("stage") != expected_stage:
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            f"Delivery run review.stages[{index}].stage should be {expected_stage!r}.",
                                            str(run_path),
                                        )
                                    )
                                if stage.get("status") not in DELIVERY_REVIEW_STAGE_STATUSES:
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            f"Delivery run review.stages[{index}].status should be one of "
                                            f"{sorted(DELIVERY_REVIEW_STAGE_STATUSES)}.",
                                            str(run_path),
                                        )
                                    )
                                for list_field in ("findings", "evidence", "notes"):
                                    value = stage.get(list_field)
                                    if value is not None and not isinstance(value, list):
                                        findings.append(
                                            finding_type(
                                                "WARN",
                                                f"Delivery run review.stages[{index}].{list_field} should be an array.",
                                                str(run_path),
                                            )
                                        )
                                updated_at = stage.get("updatedAt")
                                if updated_at is not None and not isinstance(updated_at, str):
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            f"Delivery run review.stages[{index}].updatedAt should be a string when present.",
                                            str(run_path),
                                        )
                                    )
                    for field in (
                        "reviewStartedAt",
                        "reviewCompletedAt",
                        "artifactTimestamp",
                        "artifactUpdatedAt",
                        "artifactPath",
                        "syncedAt",
                        "updatedAt",
                    ):
                        value = review_state.get(field)
                        if value is not None and not isinstance(value, str):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run review.{field} should be a string when present.",
                                    str(run_path),
                                )
                            )
                    notes = review_state.get("notes")
                    if notes is not None and not isinstance(notes, list):
                        findings.append(
                            finding_type("WARN", "Delivery run review.notes should be an array.", str(run_path))
                        )

            notes = contract.get("notes")
            if notes is not None and not isinstance(notes, list):
                findings.append(
                    finding_type("WARN", "Delivery run notes should be an array.", str(run_path))
                                    )

            ship_state = contract.get("ship")
            if ship_state is not None:
                if not isinstance(ship_state, dict):
                    findings.append(
                        finding_type("WARN", "Delivery run ship should be an object.", str(run_path))
                    )
                else:
                    status_value = ship_state.get("status")
                    if status_value not in DELIVERY_SHIP_STATUSES:
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run ship.status should be one of "
                                f"{sorted(DELIVERY_SHIP_STATUSES)}.",
                                str(run_path),
                            )
                        )
                    attempts = ship_state.get("attempts")
                    if attempts is not None and (not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 0):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run ship.attempts should be an integer >= 0 when present.",
                                str(run_path),
                            )
                        )
                    notes = ship_state.get("notes")
                    if notes is not None and not isinstance(notes, list):
                        findings.append(
                            finding_type(
                                "WARN",
                                "Delivery run ship.notes should be an array.",
                                str(run_path),
                            )
                        )
                    for field in (
                        "startedAt",
                        "completedAt",
                        "failedAt",
                        "commit",
                        "branch",
                        "prUrl",
                        "lastError",
                        "updatedAt",
                    ):
                        value = ship_state.get(field)
                        if value is not None and not isinstance(value, str):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"Delivery run ship.{field} should be a string when present.",
                                    str(run_path),
                                )
                            )

            tasks = contract.get("tasks")
            if not isinstance(tasks, list):
                findings.append(
                    finding_type("ERROR", "Delivery run tasks should be an array.", str(run_path))
                )
                continue
            for index, task in enumerate(tasks, start=1):
                label = f"tasks[{index}]"
                if not isinstance(task, dict):
                    findings.append(
                        finding_type("WARN", f"Delivery run {label} should be an object.", str(run_path))
                    )
                    continue
                task_index = task.get("taskIndex")
                if not isinstance(task_index, int):
                    findings.append(
                        finding_type("WARN", f"Delivery run {label}.taskIndex should be an integer.", str(run_path))
                    )
                title = task.get("title")
                if not isinstance(title, str) or not title.strip():
                    findings.append(
                        finding_type("WARN", f"Delivery run {label}.title should be non-empty.", str(run_path))
                    )
                task_status = task.get("status")
                if task_status not in DELIVERY_TASK_STATUSES:
                    findings.append(
                        finding_type(
                            "WARN",
                            f"Delivery run {label}.status should be one of {sorted(DELIVERY_TASK_STATUSES)}.",
                            str(run_path),
                        )
                    )
                for list_field in (
                    "blockedBy",
                    "filePaths",
                    "forbiddenPaths",
                    "verifyCommands",
                    "packageVerifyCommands",
                    "notes",
                ):
                    value = task.get(list_field)
                    if value is not None and not isinstance(value, list):
                        findings.append(
                            finding_type(
                                "WARN",
                                f"Delivery run {label}.{list_field} should be an array.",
                                str(run_path),
                            )
                        )

    def _validate_profile_dir(base_dir: Path, *, label: str, warn_legacy: bool) -> None:
        if not base_dir.is_dir() or not touched(base_dir):
            return
        for profile_path in sorted(base_dir.glob("*.json")):
            if not touched(profile_path):
                continue
            try:
                contract = load_json(profile_path)
            except Exception as exc:
                findings.append(
                    finding_type("ERROR", f"Failed to parse {label} contract: {exc}", str(profile_path))
                )
                continue
            if not isinstance(contract, dict):
                findings.append(
                    finding_type("ERROR", f"{label.title()} contract must be a JSON object.", str(profile_path))
                )
                continue
            if warn_legacy:
                findings.append(
                    finding_type(
                        "WARN",
                        "Legacy formula contracts are deprecated; store canonical contracts under .cnogo/profiles/.",
                        str(profile_path),
                    )
                )
            schema_version = contract.get("schemaVersion")
            if schema_version is not None and not isinstance(schema_version, int):
                findings.append(
                    finding_type("WARN", f"{label.title()} contract schemaVersion should be an integer.", str(profile_path))
                )
            name = contract.get("name")
            if not isinstance(name, str) or not name.strip():
                findings.append(
                    finding_type("WARN", f"{label.title()} contract should include non-empty name.", str(profile_path))
                )
            elif not is_profile_name(name):
                findings.append(
                    finding_type(
                        "WARN",
                        f"{label.title()} contract name should be a lowercase slug like 'feature-delivery'.",
                        str(profile_path),
                    )
                )
            elif profile_path.stem != name.strip():
                findings.append(
                    finding_type(
                        "WARN",
                        f"{label.title()} filename {profile_path.name!r} should match contract name {name.strip()!r}.",
                        str(profile_path),
                    )
                )
            version = contract.get("version")
            if version is not None and not isinstance(version, str):
                findings.append(
                    finding_type("WARN", f"{label.title()} contract version should be a string.", str(profile_path))
                )
            defaults = contract.get("defaults")
            if defaults is not None and not isinstance(defaults, dict):
                findings.append(
                    finding_type("WARN", f"{label.title()} contract defaults should be an object.", str(profile_path))
                )

    _validate_profile_dir(root / ".cnogo" / "profiles", label="profile", warn_legacy=False)
    _validate_profile_dir(root / ".cnogo" / "formulas", label="formula", warn_legacy=True)

    session_path = root / ".cnogo" / "worktree-session.json"
    if session_path.exists():
        try:
            session = load_json(session_path)
        except Exception:
            return
        if isinstance(session, dict):
            session_feature = session.get("feature")
            session_run_id = session.get("runId")
            if isinstance(session_feature, str) and session_feature.strip() and isinstance(session_run_id, str) and session_run_id.strip():
                known_run_ids = run_ids_by_feature.get(session_feature.strip(), set())
                if session_run_id.strip() not in known_run_ids:
                    findings.append(
                        finding_type(
                            "WARN",
                            (
                                "worktree-session.json references runId that does not exist under "
                                f".cnogo/runs/{session_feature}: {session_run_id}"
                            ),
                            str(session_path),
                        )
                    )

    work_orders_root = root / ".cnogo" / "work-orders"
    if work_orders_root.is_dir() and touched(work_orders_root):
        for order_path in sorted(work_orders_root.glob("*.json")):
            if not touched(order_path):
                continue
            try:
                contract = load_json(order_path)
            except Exception as exc:
                findings.append(
                    finding_type("ERROR", f"Failed to parse Work Order: {exc}", str(order_path))
                )
                continue
            if not isinstance(contract, dict):
                findings.append(
                    finding_type("ERROR", "Work Order artifact must be a JSON object.", str(order_path))
                )
                continue
            schema_version = contract.get("schemaVersion")
            if not isinstance(schema_version, int):
                findings.append(
                    finding_type("WARN", "Work Order schemaVersion should be an integer.", str(order_path))
                )
            feature = contract.get("feature")
            if not isinstance(feature, str) or not feature.strip():
                findings.append(finding_type("WARN", "Work Order feature should be non-empty.", str(order_path)))
            work_order_id = contract.get("workOrderId")
            if not isinstance(work_order_id, str) or not work_order_id.strip():
                findings.append(finding_type("WARN", "Work Order workOrderId should be non-empty.", str(order_path)))
            elif isinstance(feature, str) and feature.strip() and work_order_id.strip() != feature.strip():
                findings.append(
                    finding_type("WARN", "Work Order workOrderId should match feature slug.", str(order_path))
                )
            status = contract.get("status")
            if status not in WORK_ORDER_STATUSES:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Work Order status should be one of {sorted(WORK_ORDER_STATUSES)}.",
                        str(order_path),
                    )
                )
            profile = contract.get("profile")
            if profile is not None and not isinstance(profile, dict):
                findings.append(finding_type("WARN", "Work Order profile should be an object.", str(order_path)))
            run_history = contract.get("runHistory")
            if run_history is not None and not isinstance(run_history, list):
                findings.append(finding_type("WARN", "Work Order runHistory should be an array.", str(order_path)))
            next_action = contract.get("nextAction")
            if next_action is not None and not isinstance(next_action, dict):
                findings.append(finding_type("WARN", "Work Order nextAction should be an object.", str(order_path)))

    scheduler_state_path = root / ".cnogo" / "scheduler" / "state.json"
    if scheduler_state_path.exists() and touched(scheduler_state_path):
        try:
            state = load_json(scheduler_state_path)
        except Exception as exc:
            findings.append(
                finding_type("ERROR", f"Failed to parse scheduler state: {exc}", str(scheduler_state_path))
            )
            state = None
        if isinstance(state, dict):
            schema_version = state.get("schemaVersion")
            if schema_version is not None and schema_version != SCHEDULER_STATE_SCHEMA_VERSION:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Scheduler state schemaVersion {schema_version} does not match expected {SCHEDULER_STATE_SCHEMA_VERSION}.",
                        str(scheduler_state_path),
                    )
                )
            mode = state.get("mode")
            if mode is not None and mode not in {"hybrid", "supervisor"}:
                findings.append(
                    finding_type("WARN", "Scheduler state mode should be hybrid|supervisor.", str(scheduler_state_path))
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
    validate_delivery_runs: Callable[[Path, list[Any], Callable[[Path], bool]], None],
    validate_watch_runtime: Callable[[Path, list[Any], Callable[[Path], bool]], None],
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

    validate_delivery_runs(root, findings, touched, feature_filter=feature_filter)
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
        validate_watch_runtime(root, findings, touched)
        validate_token_budgets(root, findings, touched, token_budgets)
        validate_bootstrap_context(root, findings, bootstrap_context)
        validate_skills(root, findings, touched)

    return findings
