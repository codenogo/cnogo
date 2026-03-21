"""Shape-workspace validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def validate_shape_artifacts(
    root: Path,
    findings: list[Any],
    touched: Any,
    *,
    iter_ideas_dirs: Any,
    require: Any,
    load_json: Any,
    validate_shape_contract: Any,
    validate_legacy_brainstorm_contract: Any,
    finding_type: Any,
) -> None:
    """Validate initiative-level shape artifacts, including legacy brainstorms."""
    for idea_dir in iter_ideas_dirs(root):
        if not touched(idea_dir):
            continue

        shape_md = idea_dir / "SHAPE.md"
        shape_json = idea_dir / "SHAPE.json"
        if shape_md.exists():
            require(shape_json, findings, "Missing SHAPE.json contract for SHAPE.md")
        if shape_json.exists():
            try:
                validate_shape_contract(root, idea_dir, load_json(shape_json), findings, shape_json)
            except Exception as exc:
                findings.append(finding_type("ERROR", f"Failed to parse SHAPE.json: {exc}", str(shape_json)))

        brainstorm_md = idea_dir / "BRAINSTORM.md"
        brainstorm_json = idea_dir / "BRAINSTORM.json"
        if brainstorm_md.exists():
            require(brainstorm_json, findings, "Missing BRAINSTORM.json contract for BRAINSTORM.md")
        if brainstorm_json.exists():
            try:
                validate_legacy_brainstorm_contract(load_json(brainstorm_json), findings, brainstorm_json)
            except Exception as exc:
                findings.append(
                    finding_type("ERROR", f"Failed to parse BRAINSTORM.json: {exc}", str(brainstorm_json))
                )


def validate_shape_contract(
    root: Path,
    idea_dir: Path,
    contract: Any,
    findings: list[Any],
    path: Path,
    *,
    feature_slug_re: Any,
    shape_candidate_statuses: set[str],
    is_nonempty_str: Any,
    validate_decision_log: Any,
    validate_shape_threads: Any,
    validate_next_shape_moves: Any,
    finding_type: Any,
) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "SHAPE.json must be a JSON object.", str(path)))
        return

    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "SHAPE.json missing schemaVersion (recommended).", str(path)))

    slug = contract.get("slug")
    if is_nonempty_str(slug):
        slug = slug.strip()
        if slug != idea_dir.name:
            findings.append(
                finding_type(
                    "WARN",
                    f"SHAPE.json slug {slug!r} does not match directory slug {idea_dir.name!r}.",
                    str(path),
                )
            )
        if not feature_slug_re.match(slug):
            findings.append(finding_type("WARN", "SHAPE.json slug should be kebab-case.", str(path)))
    else:
        findings.append(finding_type("WARN", "SHAPE.json should include non-empty slug.", str(path)))

    for field in ("initiative", "problem"):
        if not is_nonempty_str(contract.get(field)):
            findings.append(finding_type("WARN", f"SHAPE.json should include non-empty {field}.", str(path)))

    for field in ("constraints", "globalDecisions", "researchRefs", "openQuestions"):
        value = contract.get(field)
        if value is not None and not isinstance(value, list):
            findings.append(finding_type("WARN", f"SHAPE.json: {field} should be an array.", str(path)))

    validate_decision_log(contract.get("decisionLog"), findings, path)
    validate_shape_threads(contract.get("shapeThreads"), findings, path)
    validate_next_shape_moves(contract.get("nextShapeMoves"), findings, path)

    candidate_features = contract.get("candidateFeatures")
    if candidate_features is not None and not isinstance(candidate_features, list):
        findings.append(finding_type("WARN", "SHAPE.json: candidateFeatures should be an array.", str(path)))
        candidate_features = []

    seen_feature_slugs: set[str] = set()
    if isinstance(candidate_features, list):
        for idx, candidate in enumerate(candidate_features, start=1):
            label = f"candidateFeatures[{idx}]"
            if not isinstance(candidate, dict):
                findings.append(finding_type("ERROR", f"SHAPE.json: {label} should be an object.", str(path)))
                continue

            candidate_slug = candidate.get("slug")
            if not is_nonempty_str(candidate_slug):
                findings.append(
                    finding_type("ERROR", f"SHAPE.json: {label}.slug should be a non-empty string.", str(path))
                )
                continue
            candidate_slug = candidate_slug.strip()
            if not feature_slug_re.match(candidate_slug):
                findings.append(finding_type("ERROR", f"SHAPE.json: {label}.slug should be kebab-case.", str(path)))
            if candidate_slug in seen_feature_slugs:
                findings.append(
                    finding_type("ERROR", f"SHAPE.json: duplicate candidate feature slug {candidate_slug!r}.", str(path))
                )
            seen_feature_slugs.add(candidate_slug)

            for field in ("displayName", "userOutcome", "scopeSummary", "readinessReason", "handoffSummary"):
                if not is_nonempty_str(candidate.get(field)):
                    findings.append(
                        finding_type("WARN", f"SHAPE.json: {label}.{field} should be a non-empty string.", str(path))
                    )
            for field in ("dependencies", "risks"):
                if not isinstance(candidate.get(field), list):
                    findings.append(finding_type("WARN", f"SHAPE.json: {label}.{field} should be an array.", str(path)))

            status = candidate.get("status")
            if status not in shape_candidate_statuses:
                findings.append(
                    finding_type(
                        "ERROR",
                        f"SHAPE.json: {label}.status should be one of {sorted(shape_candidate_statuses)}.",
                        str(path),
                    )
                )
            elif status == "discuss-ready":
                stub_md = root / "docs" / "planning" / "work" / "features" / candidate_slug / "FEATURE.md"
                stub_json = root / "docs" / "planning" / "work" / "features" / candidate_slug / "FEATURE.json"
                if not stub_md.exists():
                    findings.append(
                        finding_type(
                            "ERROR",
                            (
                                f"SHAPE.json candidate {candidate_slug!r} is discuss-ready but missing feature stub "
                                f"{stub_md.relative_to(root)}."
                            ),
                            str(path),
                        )
                    )
                if not stub_json.exists():
                    findings.append(
                        finding_type(
                            "ERROR",
                            (
                                f"SHAPE.json candidate {candidate_slug!r} is discuss-ready but missing feature stub "
                                f"{stub_json.relative_to(root)}."
                            ),
                            str(path),
                        )
                    )

    recommended_sequence = contract.get("recommendedSequence")
    if recommended_sequence is not None:
        if not isinstance(recommended_sequence, list):
            findings.append(finding_type("WARN", "SHAPE.json: recommendedSequence should be an array.", str(path)))
        else:
            for idx, slug_value in enumerate(recommended_sequence, start=1):
                if not is_nonempty_str(slug_value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"SHAPE.json: recommendedSequence[{idx}] should be a non-empty string.",
                            str(path),
                        )
                    )
                    continue
                if seen_feature_slugs and slug_value.strip() not in seen_feature_slugs:
                    findings.append(
                        finding_type(
                            "WARN",
                            f"SHAPE.json: recommendedSequence references unknown candidate slug {slug_value!r}.",
                            str(path),
                        )
                    )


def validate_legacy_brainstorm_contract(contract: Any, findings: list[Any], path: Path, *, finding_type: Any) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "BRAINSTORM.json must be a JSON object.", str(path)))
        return

    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "BRAINSTORM.json missing schemaVersion (recommended).", str(path)))
    if contract.get("candidates") is not None and not isinstance(contract.get("candidates"), list):
        findings.append(finding_type("WARN", "BRAINSTORM.json: candidates should be an array.", str(path)))
    if contract.get("recommendation") is not None and not isinstance(contract.get("recommendation"), dict):
        findings.append(finding_type("WARN", "BRAINSTORM.json: recommendation should be an object.", str(path)))


def validate_decision_log(entries: Any, findings: list[Any], path: Path, *, is_nonempty_str: Any, finding_type: Any) -> None:
    if entries is None:
        return
    if not isinstance(entries, list):
        findings.append(finding_type("WARN", "SHAPE.json: decisionLog should be an array.", str(path)))
        return
    for idx, entry in enumerate(entries, start=1):
        label = f"decisionLog[{idx}]"
        if not isinstance(entry, dict):
            findings.append(finding_type("WARN", f"SHAPE.json: {label} should be an object.", str(path)))
            continue
        for field in ("title", "decision"):
            if not is_nonempty_str(entry.get(field)):
                findings.append(finding_type("WARN", f"SHAPE.json: {label}.{field} should be a non-empty string.", str(path)))
        rationale = entry.get("rationale")
        if rationale is not None and not is_nonempty_str(rationale):
            findings.append(finding_type("WARN", f"SHAPE.json: {label}.rationale should be a non-empty string.", str(path)))


def validate_shape_threads(entries: Any, findings: list[Any], path: Path, *, is_nonempty_str: Any, finding_type: Any) -> None:
    if entries is None:
        return
    if not isinstance(entries, list):
        findings.append(finding_type("WARN", "SHAPE.json: shapeThreads should be an array.", str(path)))
        return
    for idx, entry in enumerate(entries, start=1):
        label = f"shapeThreads[{idx}]"
        if not isinstance(entry, dict):
            findings.append(finding_type("WARN", f"SHAPE.json: {label} should be an object.", str(path)))
            continue
        for field in ("title", "summary", "status"):
            if not is_nonempty_str(entry.get(field)):
                findings.append(finding_type("WARN", f"SHAPE.json: {label}.{field} should be a non-empty string.", str(path)))
        related_features = entry.get("relatedFeatures")
        if related_features is not None and not isinstance(related_features, list):
            findings.append(finding_type("WARN", f"SHAPE.json: {label}.relatedFeatures should be an array.", str(path)))
        elif isinstance(related_features, list):
            for rf_idx, value in enumerate(related_features, start=1):
                if not is_nonempty_str(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"SHAPE.json: {label}.relatedFeatures[{rf_idx}] should be a non-empty string.",
                            str(path),
                        )
                    )


def validate_next_shape_moves(entries: Any, findings: list[Any], path: Path, *, is_nonempty_str: Any, finding_type: Any) -> None:
    if entries is None:
        return
    if not isinstance(entries, list):
        findings.append(finding_type("WARN", "SHAPE.json: nextShapeMoves should be an array.", str(path)))
        return
    for idx, value in enumerate(entries, start=1):
        if not is_nonempty_str(value):
            findings.append(finding_type("WARN", f"SHAPE.json: nextShapeMoves[{idx}] should be a non-empty string.", str(path)))


def validate_shape_feedback(entries: Any, findings: list[Any], path: Path, *, is_nonempty_str: Any, finding_type: Any) -> None:
    if entries is None:
        return
    if not isinstance(entries, list):
        findings.append(finding_type("WARN", "CONTEXT.json: shapeFeedback should be an array.", str(path)))
        return
    for idx, entry in enumerate(entries, start=1):
        label = f"shapeFeedback[{idx}]"
        if isinstance(entry, str):
            if not entry.strip():
                findings.append(finding_type("WARN", f"CONTEXT.json: {label} should be a non-empty string.", str(path)))
            continue
        if not isinstance(entry, dict):
            findings.append(
                finding_type("WARN", f"CONTEXT.json: {label} should be an object or non-empty string.", str(path))
            )
            continue
        if not is_nonempty_str(entry.get("summary")):
            findings.append(finding_type("WARN", f"CONTEXT.json: {label}.summary should be a non-empty string.", str(path)))
        suggested_action = entry.get("suggestedAction")
        if suggested_action is not None and not is_nonempty_str(suggested_action):
            findings.append(
                finding_type("WARN", f"CONTEXT.json: {label}.suggestedAction should be a non-empty string.", str(path))
            )
        affected_features = entry.get("affectedFeatures")
        if affected_features is not None and not isinstance(affected_features, list):
            findings.append(
                finding_type("WARN", f"CONTEXT.json: {label}.affectedFeatures should be an array.", str(path))
            )
        elif isinstance(affected_features, list):
            for af_idx, value in enumerate(affected_features, start=1):
                if not is_nonempty_str(value):
                    findings.append(
                        finding_type(
                            "WARN",
                            f"CONTEXT.json: {label}.affectedFeatures[{af_idx}] should be a non-empty string.",
                            str(path),
                        )
                    )
