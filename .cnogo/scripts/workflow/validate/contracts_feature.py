"""Feature-directory validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_features(
    root: Path,
    findings: list[Any],
    touched: Any,
    *,
    shape: dict[str, Any],
    monorepo_scope_level: str,
    operating_principles_level: str,
    tdd_mode_level: str,
    verification_before_completion_level: str,
    two_stage_review_level: str,
    packages_cfg: list[dict[str, str]],
    freshness_cfg: dict[str, Any],
    feature_filter: str | None = None,
    iter_feature_dirs: Any,
    require: Any,
    load_json: Any,
    validate_feature_slug: Any,
    validate_feature_stub_contract: Any,
    validate_shape_feedback: Any,
    validate_contract_link: Any,
    warn_if_link_stale: Any,
    validate_plan_contract: Any,
    infer_task_package: Any,
    verify_cmd_scoped: Any,
    plan_md_re: Any,
    summary_md_re: Any,
    validate_ci_verification: Any,
    validate_feature_lifecycle_and_freshness: Any,
    finding_type: Any,
) -> None:
    """Validate feature directories: context, plans, summaries, reviews."""
    if feature_filter:
        feature_dir = root / "docs" / "planning" / "work" / "features" / feature_filter
        if not feature_dir.is_dir():
            findings.append(
                finding_type(
                    "ERROR",
                    f"--feature target not found: {feature_filter!r}",
                    str(feature_dir),
                )
            )
            return
        feature_dirs: list[Path] = [feature_dir]
    else:
        feature_dirs = list(iter_feature_dirs(root))

    for feature_dir in feature_dirs:
        if not touched(feature_dir):
            continue
        validate_feature_slug(feature_dir.name, findings, feature_dir)

        plan_nums: set[str] = set()
        summary_nums: set[str] = set()
        plan_files_by_num: dict[str, set[str]] = {}
        summary_change_files_by_num: dict[str, set[str]] = {}

        feature_md = feature_dir / "FEATURE.md"
        feature_json = feature_dir / "FEATURE.json"
        if feature_md.exists():
            require(feature_json, findings, "Missing FEATURE.json contract for FEATURE.md")
        if feature_json.exists():
            try:
                feature_contract = load_json(feature_json)
                validate_feature_stub_contract(root, feature_dir, feature_contract, findings, feature_json)
            except Exception as exc:
                findings.append(finding_type("ERROR", f"Failed to parse FEATURE.json: {exc}", str(feature_json)))

        context_md = feature_dir / "CONTEXT.md"
        context_json = feature_dir / "CONTEXT.json"
        if context_md.exists():
            require(context_json, findings, "Missing CONTEXT.json contract for CONTEXT.md")
        if context_json.exists():
            try:
                context_contract = load_json(context_json)
                if not isinstance(context_contract, dict):
                    findings.append(finding_type("ERROR", "CONTEXT.json must be a JSON object.", str(context_json)))
                else:
                    if "schemaVersion" not in context_contract:
                        findings.append(
                            finding_type("WARN", "CONTEXT.json missing schemaVersion (recommended).", str(context_json))
                        )
                    contract_feature = context_contract.get("feature")
                    if (
                        isinstance(contract_feature, str)
                        and contract_feature.strip()
                        and contract_feature != feature_dir.name
                    ):
                        findings.append(
                            finding_type(
                                "WARN",
                                f"CONTEXT.json feature {contract_feature!r} does not match directory slug {feature_dir.name!r}.",
                                str(context_json),
                            )
                        )
                    validate_shape_feedback(context_contract.get("shapeFeedback"), findings, context_json)
                    parent_shape = context_contract.get("parentShape")
                    if parent_shape is not None:
                        validate_contract_link(
                            root,
                            parent_shape,
                            findings,
                            context_json,
                            field_name="parentShape",
                            required_timestamp=True,
                        )
                        warn_if_link_stale(
                            root,
                            parent_shape,
                            findings,
                            context_json,
                            field_name="parentShape",
                            target_label="SHAPE artifact",
                        )
                    feature_stub_link = context_contract.get("featureStub")
                    if feature_stub_link is not None:
                        validate_contract_link(
                            root,
                            feature_stub_link,
                            findings,
                            context_json,
                            field_name="featureStub",
                            required_timestamp=True,
                        )
                        warn_if_link_stale(
                            root,
                            feature_stub_link,
                            findings,
                            context_json,
                            field_name="featureStub",
                            target_label="FEATURE artifact",
                        )
            except Exception as exc:
                findings.append(finding_type("ERROR", f"Failed to parse CONTEXT.json: {exc}", str(context_json)))

        for path in feature_dir.iterdir():
            if not path.is_file():
                continue
            match = plan_md_re.match(path.name)
            if not match:
                continue
            num = match.group("num")
            plan_nums.add(num)
            plan_json = feature_dir / f"{num}-PLAN.json"
            require(plan_json, findings, f"Missing plan contract {num}-PLAN.json for {path.name}")
            if plan_json.exists():
                try:
                    contract = load_json(plan_json)
                    validate_plan_contract(
                        contract,
                        findings,
                        plan_json,
                        tdd_mode_level=tdd_mode_level,
                        operating_principles_level=operating_principles_level,
                    )

                    if isinstance(contract, dict):
                        contract_feature = contract.get("feature")
                        if (
                            isinstance(contract_feature, str)
                            and contract_feature.strip()
                            and contract_feature != feature_dir.name
                        ):
                            findings.append(
                                finding_type(
                                    "WARN",
                                    f"{num}-PLAN.json feature {contract_feature!r} does not match directory slug {feature_dir.name!r}.",
                                    str(plan_json),
                                )
                            )
                        tasks = contract.get("tasks")
                        if isinstance(tasks, list):
                            planned_files: set[str] = set()
                            for task in tasks:
                                if not isinstance(task, dict):
                                    continue
                                files = task.get("files")
                                if not isinstance(files, list):
                                    continue
                                for file_path in files:
                                    if isinstance(file_path, str) and file_path.strip():
                                        planned_files.add(file_path.strip())
                            plan_files_by_num[num] = planned_files

                    if shape.get("monorepo") and isinstance(contract, dict):
                        tasks = contract.get("tasks")
                        if isinstance(tasks, list):
                            for idx, task in enumerate(tasks, start=1):
                                if not isinstance(task, dict):
                                    continue
                                cwd = task.get("cwd")
                                verify = task.get("verify")
                                files = task.get("files")
                                if isinstance(cwd, str) and cwd.strip():
                                    continue
                                inferred = None
                                if isinstance(files, list) and all(isinstance(item, str) for item in files):
                                    inferred = infer_task_package([str(item) for item in files], packages_cfg)
                                if isinstance(verify, list) and any(isinstance(value, str) and value.strip() for value in verify):
                                    unscoped = [
                                        value
                                        for value in verify
                                        if isinstance(value, str) and value.strip() and not verify_cmd_scoped(value)
                                    ]
                                    if unscoped:
                                        message = (
                                            f"Plan task {idx} has verify commands that may be unscoped for a monorepo/polyglot repo. "
                                            "Add task.cwd or scope verify with `cd <pkg> && ...` / workspace flags."
                                        )
                                        if inferred:
                                            message += f" Inferred package cwd from files: {inferred!r}."
                                        level = "ERROR" if monorepo_scope_level == "error" else "WARN"
                                        findings.append(finding_type(level, message, str(plan_json)))
                except Exception as exc:
                    findings.append(finding_type("ERROR", f"Failed to parse plan contract: {exc}", str(plan_json)))

            summary_md = feature_dir / f"{num}-SUMMARY.md"
            summary_json = feature_dir / f"{num}-SUMMARY.json"
            if summary_md.exists():
                summary_nums.add(num)
                require(summary_json, findings, f"Missing summary contract {num}-SUMMARY.json for {summary_md.name}")
                if summary_json.exists():
                    try:
                        summary_contract = load_json(summary_json)
                        if not isinstance(summary_contract, dict):
                            findings.append(
                                finding_type("ERROR", "Summary contract must be a JSON object.", str(summary_json))
                            )
                        else:
                            contract_feature = summary_contract.get("feature")
                            if (
                                isinstance(contract_feature, str)
                                and contract_feature.strip()
                                and contract_feature != feature_dir.name
                            ):
                                findings.append(
                                    finding_type(
                                        "WARN",
                                        f"{num}-SUMMARY.json feature {contract_feature!r} does not match directory slug {feature_dir.name!r}.",
                                        str(summary_json),
                                    )
                                )
                            plan_number = summary_contract.get("planNumber")
                            if plan_number is not None:
                                plan_number_str = str(plan_number).strip()
                                if plan_number_str and plan_number_str != num:
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            f"{num}-SUMMARY.json planNumber {plan_number_str!r} does not match filename plan number {num!r}.",
                                            str(summary_json),
                                        )
                                    )
                            changes = summary_contract.get("changes")
                            changed_files: set[str] = set()
                            if isinstance(changes, list):
                                for change in changes:
                                    if isinstance(change, dict):
                                        file_path = change.get("file")
                                        if isinstance(file_path, str) and file_path.strip():
                                            changed_files.add(file_path.strip())
                            summary_change_files_by_num[num] = changed_files
                            outcome = summary_contract.get("outcome")
                            if outcome not in {"complete", "partial", "failed"}:
                                findings.append(
                                    finding_type(
                                        "ERROR",
                                        "Summary contract must include outcome: complete|partial|failed",
                                        str(summary_json),
                                    )
                                )
                            generated_from = summary_contract.get("generatedFrom")
                            if generated_from is not None and not isinstance(generated_from, dict):
                                findings.append(
                                    finding_type("WARN", "Summary generatedFrom should be an object if present.", str(summary_json))
                                )
                            notes = summary_contract.get("notes")
                            if notes is not None:
                                if not isinstance(notes, list):
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            "Summary notes should be an array of non-empty strings.",
                                            str(summary_json),
                                        )
                                    )
                                elif not all(isinstance(note, str) and note.strip() for note in notes):
                                    findings.append(
                                        finding_type(
                                            "WARN",
                                            "Summary notes entries should be non-empty strings.",
                                            str(summary_json),
                                        )
                                    )
                    except Exception as exc:
                        findings.append(
                            finding_type("ERROR", f"Failed to parse summary contract: {exc}", str(summary_json))
                        )

        for path in feature_dir.iterdir():
            if not path.is_file():
                continue
            match = summary_md_re.match(path.name)
            if match:
                summary_nums.add(match.group("num"))

        validate_ci_verification(
            feature_dir,
            findings,
            operating_principles_level,
            verification_before_completion_level,
            two_stage_review_level,
        )
        validate_feature_lifecycle_and_freshness(
            feature_dir=feature_dir,
            context_md=context_md,
            context_json=context_json,
            plan_nums=plan_nums,
            summary_nums=summary_nums,
            plan_files_by_num=plan_files_by_num,
            summary_change_files_by_num=summary_change_files_by_num,
            freshness=freshness_cfg,
            findings=findings,
        )


def validate_ci_verification(
    feature_dir: Path,
    findings: list[Any],
    operating_principles_level: str,
    verification_before_completion_level: str,
    two_stage_review_level: str,
    *,
    require: Any,
    load_json: Any,
    policy_level_to_finding: Any,
    finding_type: Any,
) -> None:
    """Validate review, CI verification, and human verification artifacts within a feature."""
    review_md = feature_dir / "REVIEW.md"
    review_json = feature_dir / "REVIEW.json"
    if review_md.exists():
        require(review_json, findings, "Missing REVIEW.json contract for REVIEW.md")
        if review_json.exists():
            try:
                review_contract = load_json(review_json)
                if isinstance(review_contract, dict):
                    if "schemaVersion" not in review_contract:
                        findings.append(
                            finding_type("WARN", "REVIEW.json missing schemaVersion (recommended).", str(review_json))
                        )
                    schema_version = review_contract.get("schemaVersion")
                    if isinstance(schema_version, int) and not isinstance(schema_version, bool) and schema_version >= 3:
                        for field in ("securityFindings", "performanceFindings", "patternCompliance"):
                            value = review_contract.get(field)
                            if value is None:
                                level = "ERROR" if operating_principles_level == "error" else "WARN"
                                findings.append(
                                    finding_type(level, f"REVIEW.json schemaVersion>=3 requires {field} array.", str(review_json))
                                )
                            elif not isinstance(value, list):
                                findings.append(
                                    finding_type("WARN", f"REVIEW.json {field} should be an array.", str(review_json))
                                )
                    if two_stage_review_level != "off":
                        stage_level = policy_level_to_finding(two_stage_review_level)
                        reviewers = review_contract.get("reviewers")
                        if reviewers is not None:
                            if not isinstance(reviewers, list):
                                findings.append(
                                    finding_type(
                                        "WARN",
                                        "REVIEW.json reviewers should be an array of non-empty agent names.",
                                        str(review_json),
                                    )
                                )
                            elif not all(isinstance(name, str) and name.strip() for name in reviewers):
                                findings.append(
                                    finding_type(
                                        "WARN",
                                        "REVIEW.json reviewers entries should be non-empty strings.",
                                        str(review_json),
                                    )
                                )
                        if not (
                            isinstance(schema_version, int)
                            and not isinstance(schema_version, bool)
                            and schema_version >= 4
                        ):
                            findings.append(
                                finding_type(
                                    stage_level,
                                    "REVIEW.json must set schemaVersion>=4 when twoStageReview policy is enabled.",
                                    str(review_json),
                                )
                            )
                        else:
                            stage_reviews = review_contract.get("stageReviews")
                            verify_level = policy_level_to_finding(verification_before_completion_level)
                            expected_stages = ["spec-compliance", "code-quality"]
                            if not isinstance(stage_reviews, list) or len(stage_reviews) < 2:
                                findings.append(
                                    finding_type(
                                        stage_level,
                                        "REVIEW.json schemaVersion>=4 requires stageReviews[spec-compliance, code-quality].",
                                        str(review_json),
                                    )
                                )
                            else:
                                for idx, expected in enumerate(expected_stages):
                                    if idx >= len(stage_reviews):
                                        findings.append(
                                            finding_type(
                                                stage_level,
                                                f"REVIEW.json missing stageReviews[{idx}] for {expected}.",
                                                str(review_json),
                                            )
                                        )
                                        continue
                                    stage_review = stage_reviews[idx]
                                    if not isinstance(stage_review, dict):
                                        findings.append(
                                            finding_type(
                                                stage_level,
                                                f"REVIEW.json stageReviews[{idx}] must be an object.",
                                                str(review_json),
                                            )
                                        )
                                        continue
                                    stage_name = stage_review.get("stage")
                                    if stage_name != expected:
                                        findings.append(
                                            finding_type(
                                                stage_level,
                                                f"REVIEW.json stageReviews[{idx}].stage should be {expected!r}.",
                                                str(review_json),
                                            )
                                        )
                                    status = stage_review.get("status")
                                    if status not in {"pending", "pass", "warn", "fail"}:
                                        findings.append(
                                            finding_type(
                                                stage_level,
                                                f"REVIEW.json stageReviews[{idx}].status must be pending|pass|warn|fail.",
                                                str(review_json),
                                            )
                                        )
                                    stage_findings = stage_review.get("findings")
                                    if not isinstance(stage_findings, list):
                                        findings.append(
                                            finding_type(
                                                stage_level,
                                                f"REVIEW.json stageReviews[{idx}].findings should be an array.",
                                                str(review_json),
                                            )
                                        )
                                    evidence = stage_review.get("evidence")
                                    if verification_before_completion_level != "off":
                                        if not isinstance(evidence, list):
                                            findings.append(
                                                finding_type(
                                                    verify_level,
                                                    f"REVIEW.json stageReviews[{idx}].evidence should be an array.",
                                                    str(review_json),
                                                )
                                            )
                                        elif status in {"pass", "warn", "fail"} and not evidence:
                                            findings.append(
                                                finding_type(
                                                    verify_level,
                                                    f"REVIEW.json stageReviews[{idx}] completed status requires evidence entries.",
                                                    str(review_json),
                                                )
                                            )
            except Exception:
                pass

    vci_md = feature_dir / "VERIFICATION-CI.md"
    vci_json = feature_dir / "VERIFICATION-CI.json"
    if vci_md.exists():
        require(vci_json, findings, "Missing VERIFICATION-CI.json contract for VERIFICATION-CI.md")
        if vci_json.exists():
            try:
                ci_contract = load_json(vci_json)
                if isinstance(ci_contract, dict) and "schemaVersion" not in ci_contract:
                    findings.append(
                        finding_type("WARN", "VERIFICATION-CI.json missing schemaVersion (recommended).", str(vci_json))
                    )
            except Exception:
                pass

    verification_md = feature_dir / "VERIFICATION.md"
    verification_json = feature_dir / "VERIFICATION.json"
    if verification_md.exists():
        require(verification_json, findings, "Missing VERIFICATION.json contract for VERIFICATION.md")
        if verification_json.exists():
            try:
                human_contract = load_json(verification_json)
                if isinstance(human_contract, dict) and "schemaVersion" not in human_contract:
                    findings.append(
                        finding_type("WARN", "VERIFICATION.json missing schemaVersion (recommended).", str(verification_json))
                    )
            except Exception:
                pass


def validate_feature_lifecycle_and_freshness(
    *,
    feature_dir: Path,
    context_md: Path,
    context_json: Path,
    plan_nums: set[str],
    summary_nums: set[str],
    plan_files_by_num: dict[str, set[str]],
    summary_change_files_by_num: dict[str, set[str]],
    freshness: dict[str, Any],
    findings: list[Any],
    artifact_time: Any,
    age_days: Any,
    finding_type: Any,
) -> None:
    """Cross-link and freshness checks across CONTEXT/PLAN/SUMMARY/REVIEW."""
    review_md = feature_dir / "REVIEW.md"

    if review_md.exists() and not summary_nums:
        findings.append(
            finding_type(
                "WARN",
                "REVIEW.md exists without any SUMMARY artifacts (missing summary->review link).",
                str(review_md),
            )
        )

    if plan_nums and not context_md.exists():
        findings.append(
            finding_type(
                "WARN",
                "Feature has PLAN artifacts but no CONTEXT.md (missing context->plan link).",
                str(feature_dir),
            )
        )

    for num in sorted(summary_nums):
        if num not in plan_nums:
            findings.append(
                finding_type(
                    "ERROR",
                    f"Found {num}-SUMMARY.md without matching {num}-PLAN.md.",
                    str(feature_dir / f"{num}-SUMMARY.md"),
                )
            )

    for num in sorted(plan_nums):
        if num not in summary_nums:
            continue
        planned = plan_files_by_num.get(num, set())
        changed = summary_change_files_by_num.get(num, set())
        if not planned or not changed:
            continue
        outside = sorted(changed - planned)
        if outside:
            sample = ", ".join(outside[:5])
            findings.append(
                finding_type(
                    "WARN",
                    f"{num}-SUMMARY.json records files outside {num}-PLAN.json task files: {sample}",
                    str(feature_dir / f"{num}-SUMMARY.json"),
                )
            )

    if summary_nums and not review_md.exists():
        newest_summary_dt = None
        for num in summary_nums:
            dt = artifact_time(feature_dir / f"{num}-SUMMARY.md", feature_dir / f"{num}-SUMMARY.json")
            if dt is not None and (newest_summary_dt is None or dt > newest_summary_dt):
                newest_summary_dt = dt
        if newest_summary_dt is not None:
            age = age_days(newest_summary_dt)
            threshold = int(freshness.get("summaryMaxAgeDaysWithoutReview", 7))
            if age is not None and age > threshold:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Feature has SUMMARY artifacts but no REVIEW.md and latest summary is {age} days old (> {threshold}).",
                        str(feature_dir),
                    )
                )

    if not freshness.get("enabled", True):
        return

    if context_md.exists() and not plan_nums:
        age = age_days(artifact_time(context_md, context_json))
        threshold = int(freshness.get("contextMaxAgeDays", 30))
        if age is not None and age > threshold:
            findings.append(
                finding_type(
                    "WARN",
                    f"CONTEXT exists without any PLAN and is {age} days old (> {threshold}).",
                    str(context_md),
                )
            )

    for num in sorted(plan_nums):
        if num in summary_nums:
            continue
        age = age_days(artifact_time(feature_dir / f"{num}-PLAN.md", feature_dir / f"{num}-PLAN.json"))
        threshold = int(freshness.get("planMaxAgeDaysWithoutSummary", 14))
        if age is not None and age > threshold:
            findings.append(
                finding_type(
                    "WARN",
                    f"{num}-PLAN has no SUMMARY and is {age} days old (> {threshold}).",
                    str(feature_dir / f"{num}-PLAN.md"),
                )
            )


def validate_feature_stub_contract(
    root: Path,
    feature_dir: Path,
    contract: Any,
    findings: list[Any],
    path: Path,
    *,
    is_nonempty_str: Any,
    shape_candidate_statuses: set[str],
    validate_contract_link: Any,
    warn_if_link_stale: Any,
    finding_type: Any,
) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "FEATURE.json must be a JSON object.", str(path)))
        return
    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "FEATURE.json missing schemaVersion (recommended).", str(path)))

    feature = contract.get("feature")
    if is_nonempty_str(feature):
        if feature != feature_dir.name:
            findings.append(
                finding_type(
                    "WARN",
                    f"FEATURE.json feature {feature!r} does not match directory slug {feature_dir.name!r}.",
                    str(path),
                )
            )
    else:
        findings.append(finding_type("WARN", "FEATURE.json should include non-empty feature.", str(path)))

    for field in ("displayName", "userOutcome", "scopeSummary", "readinessReason", "handoffSummary"):
        if not is_nonempty_str(contract.get(field)):
            findings.append(finding_type("WARN", f"FEATURE.json should include non-empty {field}.", str(path)))
    for field in ("dependencies", "risks"):
        if not isinstance(contract.get(field), list):
            findings.append(finding_type("WARN", f"FEATURE.json: {field} should be an array.", str(path)))

    status = contract.get("status")
    normalized_status = "ready" if status == "discuss-ready" else status
    if status == "discuss-ready":
        findings.append(
            finding_type(
                "WARN",
                "FEATURE.json status 'discuss-ready' is deprecated; use 'ready' instead.",
                str(path),
            )
        )
    if normalized_status not in shape_candidate_statuses:
        findings.append(
            finding_type(
                "ERROR",
                f"FEATURE.json status should be one of {sorted(shape_candidate_statuses)}.",
                str(path),
            )
        )

    parent_shape = contract.get("parentShape")
    if parent_shape is not None:
        validate_contract_link(root, parent_shape, findings, path, field_name="parentShape", required_timestamp=True)
        warn_if_link_stale(
            root,
            parent_shape,
            findings,
            path,
            field_name="parentShape",
            target_label="SHAPE artifact",
        )


def validate_contract_link(
    root: Path,
    link: Any,
    findings: list[Any],
    contract_path: Path,
    *,
    field_name: str,
    required_timestamp: bool,
    is_nonempty_str: Any,
    resolve_contract_ref: Any,
    parse_ts: Any,
    finding_type: Any,
) -> None:
    if not isinstance(link, dict):
        findings.append(finding_type("WARN", f"{contract_path.name}: {field_name} should be an object.", str(contract_path)))
        return

    raw_path = link.get("path")
    if not is_nonempty_str(raw_path):
        findings.append(
            finding_type(
                "WARN",
                f"{contract_path.name}: {field_name}.path should be a non-empty string.",
                str(contract_path),
            )
        )
    else:
        resolved = resolve_contract_ref(root, raw_path.strip())
        if not resolved.exists():
            findings.append(
                finding_type(
                    "WARN",
                    f"{contract_path.name}: {field_name}.path not found: {raw_path}",
                    str(contract_path),
                )
            )

    raw_timestamp = link.get("timestamp")
    if required_timestamp and parse_ts(raw_timestamp) is None:
        findings.append(
            finding_type(
                "WARN",
                f"{contract_path.name}: {field_name}.timestamp should be an ISO-8601 string.",
                str(contract_path),
            )
        )

    schema_version = link.get("schemaVersion")
    if schema_version is not None and not isinstance(schema_version, int):
        findings.append(
            finding_type(
                "WARN",
                f"{contract_path.name}: {field_name}.schemaVersion should be an integer.",
                str(contract_path),
            )
        )


def warn_if_link_stale(
    root: Path,
    link: Any,
    findings: list[Any],
    contract_path: Path,
    *,
    field_name: str,
    target_label: str,
    is_nonempty_str: Any,
    parse_ts: Any,
    linked_artifact_time: Any,
    finding_type: Any,
) -> None:
    if not isinstance(link, dict):
        return
    raw_path = link.get("path")
    raw_timestamp = link.get("timestamp")
    if not is_nonempty_str(raw_path):
        return
    recorded_ts = parse_ts(raw_timestamp)
    if recorded_ts is None:
        return
    actual_ts = linked_artifact_time(root, raw_path.strip())
    if actual_ts is None:
        return
    if actual_ts > recorded_ts:
        findings.append(
            finding_type(
                "WARN",
                (
                    f"{contract_path.name}: {field_name} is stale; linked {target_label} changed "
                    "after this artifact was last refreshed."
                ),
                str(contract_path),
            )
        )
