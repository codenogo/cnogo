"""Deterministic plan generation from ready feature dossiers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.workflow.shared.packages import configured_packages, infer_task_package, scope_package_command
from scripts.workflow.shared.plans import normalize_plan_number
from scripts.workflow.shared.profiles import (
    profile_auto_advance,
    profile_auto_plan,
    profile_mode_preference,
    resolve_profile,
    suggest_profile,
)
from scripts.workflow.shared.runtime_root import runtime_root
from scripts.workflow.validate import common as _validate_common
from scripts.workflow.validate import contracts_plan as _validate_plan_contracts
from scripts.workflow.validate import repo_policy as _validate_repo_policy
from scripts.workflow_render import render_plan, write
from scripts.workflow_utils import load_json, write_json
from scripts.workflow.shared.config import load_workflow_config


@dataclass
class _PlanFactoryFinding:
    level: str
    message: str
    path: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _feature_dir(root: Path, feature: str) -> Path:
    return root / "docs" / "planning" / "work" / "features" / feature


def _sync_ready_dossier(root: Path, feature: str) -> dict[str, Any]:
    source_root = runtime_root(root)
    source_feature_dir = _feature_dir(source_root, feature)
    target_feature_dir = _feature_dir(root, feature)
    synced: list[str] = []
    if source_root.resolve() == root.resolve():
        return {"sourceRoot": str(source_root), "syncedArtifacts": synced}
    for name in ("FEATURE.json", "CONTEXT.json", "FEATURE.md", "CONTEXT.md"):
        source_path = source_feature_dir / name
        if not source_path.exists():
            continue
        target_path = target_feature_dir / name
        try:
            source_text = source_path.read_text(encoding="utf-8")
        except Exception:
            continue
        target_text = ""
        if target_path.exists():
            try:
                target_text = target_path.read_text(encoding="utf-8")
            except Exception:
                target_text = ""
        if target_path.exists() and target_text == source_text:
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(source_text, encoding="utf-8")
        synced.append(str(target_path))
    return {"sourceRoot": str(source_root), "syncedArtifacts": synced}


def _load_contract(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must be a JSON object")
    return payload


def _latest_plan_path(feature_dir: Path) -> Path | None:
    plans = sorted(feature_dir.glob("[0-9][0-9]-PLAN.json"))
    return plans[-1] if plans else None


def _next_plan_number(feature_dir: Path) -> str:
    latest = _latest_plan_path(feature_dir)
    if latest is None:
        return "01"
    stem = latest.stem.replace("-PLAN", "")
    if stem.isdigit():
        return normalize_plan_number(int(stem) + 1)
    return "01"


def _existing_or_target_plan_path(feature_dir: Path, plan_number: str | None) -> Path | None:
    if isinstance(plan_number, str) and plan_number.strip():
        return feature_dir / f"{normalize_plan_number(plan_number)}-PLAN.json"
    return _latest_plan_path(feature_dir)


def _normalize_paths(paths: list[Any]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in paths:
        if not isinstance(raw, str):
            continue
        value = raw.strip().lstrip("./")
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return sorted(normalized)


def _collect_context_links(context: dict[str, Any], feature_contract: dict[str, Any]) -> list[str]:
    links: list[str] = []
    constraints = context.get("constraints", [])
    if isinstance(constraints, list):
        for item in constraints:
            if isinstance(item, str) and item.strip():
                links.append(f"Constraint: {item.strip()}")
    decisions = context.get("decisions", [])
    if isinstance(decisions, list):
        for entry in decisions:
            if isinstance(entry, dict):
                decision = str(entry.get("decision", "")).strip()
                if not decision:
                    continue
                area = str(entry.get("area", "")).strip()
                prefix = f"Decision ({area})" if area else "Decision"
                links.append(f"{prefix}: {decision}")
            elif isinstance(entry, str) and entry.strip():
                links.append(f"Decision: {entry.strip()}")
    if links:
        return links
    scope_summary = str(feature_contract.get("scopeSummary", "")).strip()
    user_outcome = str(feature_contract.get("userOutcome", "")).strip()
    if scope_summary:
        return [f"Constraint: scope summary — {scope_summary}"]
    if user_outcome:
        return [f"Constraint: user outcome — {user_outcome}"]
    return [f"Constraint: implement feature `{feature_contract.get('feature', 'feature')}` deterministically."]


def _bucket_key(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2 and parts[0] in {"src", "app", "lib", "internal", "pkg", "services", "packages"}:
        return "/".join(parts[:2])
    if len(parts) >= 2:
        return parts[0]
    return Path(path).stem or path


def _partition_paths(paths: list[str]) -> list[list[str]]:
    if not paths:
        return []
    grouped: dict[str, list[str]] = {}
    for path in paths:
        grouped.setdefault(_bucket_key(path), []).append(path)
    buckets = [sorted(bucket) for _key, bucket in sorted(grouped.items())]
    if len(buckets) <= 3:
        return buckets
    flattened = sorted(paths)
    chunk_size = max((len(flattened) + 2) // 3, 1)
    out: list[list[str]] = []
    for start in range(0, len(flattened), chunk_size):
        out.append(flattened[start : start + chunk_size])
        if len(out) == 3:
            break
    if len(flattened) > chunk_size * 3:
        out[-1].extend(flattened[chunk_size * 3 :])
        out[-1] = sorted(set(out[-1]))
    return out


def _group_label(paths: list[str]) -> str:
    if not paths:
        return "core"
    prefixes = sorted({_bucket_key(path) for path in paths})
    if len(prefixes) == 1:
        return prefixes[0]
    return prefixes[0]


def _package_test_command(root: Path, files: list[str]) -> str | None:
    packages = configured_packages(root)
    matched = infer_task_package(files, packages)
    if not matched:
        return None
    for package in packages:
        if str(package.get("path", "")).strip() != matched:
            continue
        commands = package.get("commands")
        if not isinstance(commands, dict):
            break
        for key in ("test", "lint", "typecheck"):
            command = commands.get(key)
            if isinstance(command, str) and command.strip():
                return scope_package_command(matched, command.strip())
    return None


def _fallback_verify_command(feature: str, files: list[str]) -> str:
    suffixes = {Path(path).suffix.lower() for path in files if Path(path).suffix}
    if suffixes & {".py"}:
        return "pytest -q --tb=short"
    if suffixes & {".go"}:
        return "go test ./... -short"
    if suffixes & {".rs"}:
        return "cargo test --quiet"
    if suffixes & {".ts", ".tsx", ".js", ".jsx"}:
        return "npm test --silent"
    if suffixes & {".java", ".kt"}:
        return "mvn -q test -DskipITs"
    if suffixes and suffixes <= {".json", ".md", ".toml", ".yaml", ".yml"}:
        return f"python3 .cnogo/scripts/workflow_validate.py --feature {feature}"
    return f"python3 .cnogo/scripts/workflow_validate.py --feature {feature}"


def _task_verify_commands(root: Path, feature: str, files: list[str]) -> list[str]:
    package_command = _package_test_command(root, files)
    if package_command:
        return [package_command]
    return [_fallback_verify_command(feature, files)]


def _task_tdd(files: list[str], verify: list[str]) -> dict[str, Any]:
    suffixes = {Path(path).suffix.lower() for path in files if Path(path).suffix}
    if suffixes and suffixes <= {".json", ".md", ".toml", ".yaml", ".yml"}:
        return {
            "required": False,
            "reason": "Task is configuration or documentation scoped and is verified structurally.",
        }
    return {
        "required": True,
        "failingVerify": list(verify),
        "passingVerify": list(verify),
    }


def _task_micro_steps(label: str, verify: list[str], *, tdd_required: bool, feature_name: str) -> list[str]:
    verify_label = verify[0] if verify else "[verify command]"
    if tdd_required:
        return [
            f"write failing invalid-input or error-path coverage for {label}",
            f"implement {feature_name} in {label} while preserving the scoped context links",
            f"run {verify_label}",
        ]
    return [
        f"apply the scoped {feature_name} change in {label}",
        f"run {verify_label}",
    ]


def _goal(feature_contract: dict[str, Any]) -> str:
    display_name = str(feature_contract.get("displayName") or feature_contract.get("feature") or "feature").strip()
    user_outcome = str(feature_contract.get("userOutcome", "")).strip()
    scope_summary = str(feature_contract.get("scopeSummary", "")).strip()
    if user_outcome:
        return f"Deliver {display_name}: {user_outcome}"
    if scope_summary:
        return f"Deliver {display_name}: {scope_summary}"
    return f"Deliver {display_name}."


def _commit_message(feature: str, feature_contract: dict[str, Any], profile_name: str) -> str:
    display_name = str(feature_contract.get("displayName") or feature).strip().lower().replace(" ", "-")
    prefix = "feat"
    if profile_name == "debug-fix":
        prefix = "fix"
    elif profile_name == "release-cut":
        prefix = "chore"
    return f"{prefix}({feature}): implement {display_name}"


def _build_plan_contract(
    root: Path,
    *,
    feature: str,
    feature_contract: dict[str, Any],
    context_contract: dict[str, Any],
    plan_number: str,
    profile_name: str,
) -> dict[str, Any]:
    related_code = _normalize_paths(context_contract.get("relatedCode", []))
    if not related_code:
        raise ValueError("CONTEXT.json must include non-empty relatedCode[] for deterministic plan generation.")
    context_links = _collect_context_links(context_contract, feature_contract)
    buckets = _partition_paths(related_code)
    display_name = str(feature_contract.get("displayName") or feature).strip()
    tasks: list[dict[str, Any]] = []
    for index, bucket in enumerate(buckets):
        label = _group_label(bucket)
        verify = _task_verify_commands(root, feature, bucket)
        tdd = _task_tdd(bucket, verify)
        tasks.append(
            {
                "name": f"{display_name}: {label}",
                "files": bucket,
                "contextLinks": context_links[: min(len(context_links), 3)],
                "microSteps": _task_micro_steps(
                    label,
                    verify,
                    tdd_required=bool(tdd.get("required") is True),
                    feature_name=display_name.lower(),
                ),
                "action": (
                    f"Implement {display_name.lower()} behavior in `{label}` and satisfy the linked "
                    "constraints or decisions from CONTEXT.json."
                ),
                "verify": verify,
                "tdd": tdd,
                "blockedBy": [index - 1] if index > 0 else [],
            }
        )
    plan_verify: list[str] = []
    seen_verify: set[str] = set()
    for task in tasks:
        for command in task.get("verify", []) if isinstance(task.get("verify"), list) else []:
            if not isinstance(command, str) or not command.strip() or command in seen_verify:
                continue
            seen_verify.add(command)
            plan_verify.append(command)
    return {
        "schemaVersion": 3,
        "feature": feature,
        "planNumber": normalize_plan_number(plan_number),
        "goal": _goal(feature_contract),
        "profile": profile_name,
        "parallelizable": len(tasks) > 1 and all(not task.get("blockedBy") for task in tasks),
        "tasks": tasks,
        "planVerify": plan_verify,
        "commitMessage": _commit_message(feature, feature_contract, profile_name),
        "timestamp": _now_iso(),
    }


def _run_plan_validation(root: Path, contract: dict[str, Any], path: Path) -> list[dict[str, str]]:
    cfg = load_workflow_config(root)
    findings: list[_PlanFactoryFinding] = []
    _validate_plan_contracts.validate_plan_contract(
        contract,
        findings,
        path,
        tdd_mode_level=_validate_repo_policy.get_tdd_mode_level(cfg),
        operating_principles_level=_validate_repo_policy.get_operating_principles_level(cfg),
        is_positive_int=_validate_common.is_positive_int,
        finding_type=_PlanFactoryFinding,
    )
    return [
        {
            "level": finding.level,
            "message": finding.message,
            "path": str(finding.path or path),
        }
        for finding in findings
    ]


def _resolve_mode(profile: dict[str, Any], recommendation: dict[str, Any]) -> str:
    preference = profile_mode_preference(profile)
    if preference == "team":
        return "team"
    if preference == "serial":
        return "serial"
    return "team" if recommendation.get("recommended") else "serial"


def _load_feature_contracts(root: Path, feature: str) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    sync = _sync_ready_dossier(root, feature)
    feature_dir = _feature_dir(root, feature)
    context_path = feature_dir / "CONTEXT.json"
    feature_path = feature_dir / "FEATURE.json"
    if not context_path.exists():
        raise FileNotFoundError(f"Missing CONTEXT.json for feature {feature!r}: {context_path}")
    if not feature_path.exists():
        raise FileNotFoundError(f"Missing FEATURE.json for feature {feature!r}: {feature_path}")
    context_contract = _load_contract(context_path)
    feature_contract = _load_contract(feature_path)
    return feature_dir, feature_contract, context_contract, sync


def resolve_feature_plan_policy(
    root: Path,
    *,
    feature: str,
    requested_profile_name: str | None = None,
) -> dict[str, Any]:
    feature_dir, feature_contract, context_contract, sync = _load_feature_contracts(root, feature)
    suggestion = suggest_profile(root, feature_slug=feature, context_contract=context_contract)
    resolved_profile = resolve_profile(
        root,
        requested_name=requested_profile_name or suggestion["name"],
    )
    return {
        "feature": feature,
        "featureDir": str(feature_dir),
        "planningRoot": str(root),
        "sourceRoot": str(sync["sourceRoot"]),
        "syncedArtifacts": list(sync["syncedArtifacts"]),
        "featureContract": feature_contract,
        "contextContract": context_contract,
        "profile": resolved_profile,
        "profileSuggestion": suggestion,
        "autoPlanAllowed": profile_auto_plan(resolved_profile),
        "autoAdvanceAllowed": profile_auto_advance(resolved_profile),
    }


def ensure_feature_plan(
    root: Path,
    *,
    feature: str,
    plan_number: str | None = None,
    requested_profile_name: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    policy = resolve_feature_plan_policy(
        root,
        feature=feature,
        requested_profile_name=requested_profile_name,
    )
    feature_dir = Path(str(policy["featureDir"]))
    context_contract = dict(policy["contextContract"])
    feature_contract = dict(policy["featureContract"])
    existing_path = _existing_or_target_plan_path(feature_dir, plan_number)
    created = False
    if existing_path is not None and existing_path.exists() and not force:
        contract = _load_contract(existing_path)
        validation = _run_plan_validation(root, contract, existing_path)
        if any(item["level"] == "ERROR" for item in validation):
            raise ValueError(
                f"Existing plan {existing_path.name} is invalid; repair it or rerun with force."
            )
        resolved_profile = resolve_profile(root, plan_contract=contract, requested_name=requested_profile_name)
        plan_path = existing_path
        suggestion = suggest_profile(root, feature_slug=feature, plan_contract=contract, context_contract=context_contract)
    else:
        target_number = normalize_plan_number(plan_number or _next_plan_number(feature_dir))
        suggestion = dict(policy["profileSuggestion"])
        resolved_profile = dict(policy["profile"])
        contract = _build_plan_contract(
            root,
            feature=feature,
            feature_contract=feature_contract,
            context_contract=context_contract,
            plan_number=target_number,
            profile_name=str(resolved_profile.get("name", "feature-delivery")),
        )
        plan_path = feature_dir / f"{target_number}-PLAN.json"
        validation = _run_plan_validation(root, contract, plan_path)
        if any(item["level"] == "ERROR" for item in validation):
            raise ValueError(
                "Deterministic plan factory generated an invalid plan: "
                + "; ".join(item["message"] for item in validation if item["level"] == "ERROR")
            )
        write_json(plan_path, contract)
        write(plan_path.with_suffix(".md"), render_plan(contract).strip() + "\n")
        created = True

    from scripts.memory.bridge import plan_to_task_descriptions, recommend_team_mode  # noqa: lazy to break circular import
    taskdescs = plan_to_task_descriptions(plan_path, root, profile=resolved_profile)
    recommendation = recommend_team_mode(taskdescs, profile=resolved_profile)
    return {
        "feature": feature,
        "planNumber": str(contract.get("planNumber", "")),
        "planPath": str(plan_path),
        "markdownPath": str(plan_path.with_suffix(".md")),
        "planningRoot": str(root),
        "sourceRoot": str(policy["sourceRoot"]),
        "syncedArtifacts": list(policy["syncedArtifacts"]),
        "createdPlan": created,
        "reusedPlan": not created,
        "profile": resolved_profile,
        "profileSuggestion": suggestion,
        "autoPlanAllowed": profile_auto_plan(resolved_profile),
        "autoAdvanceAllowed": profile_auto_advance(resolved_profile),
        "planContract": contract,
        "taskDescriptions": taskdescs,
        "recommendation": recommendation,
        "mode": _resolve_mode(resolved_profile, recommendation),
        "validation": validation,
    }


def auto_plan_feature(
    root: Path,
    *,
    feature: str,
    plan_number: str | None = None,
    requested_profile_name: str | None = None,
    force: bool = False,
    start_run: bool | None = None,
) -> dict[str, Any]:
    payload = ensure_feature_plan(
        root,
        feature=feature,
        plan_number=plan_number,
        requested_profile_name=requested_profile_name,
        force=force,
    )
    profile = payload.get("profile", {})
    should_start_run = profile_auto_advance(profile) if start_run is None else bool(start_run)
    payload["startedRun"] = False
    if should_start_run:
        from scripts.memory import ensure_delivery_run, set_phase

        run = ensure_delivery_run(
            feature=feature,
            plan_number=str(payload["planNumber"]),
            plan_path=Path(str(payload["planPath"])),
            task_descriptions=list(payload["taskDescriptions"]),
            mode=str(payload["mode"]),
            recommendation=dict(payload["recommendation"]),
            profile=dict(profile),
            root=root,
        )
        set_phase(feature, "implement", root=root)
        payload["startedRun"] = True
        payload["deliveryRun"] = run.to_dict()
    else:
        from scripts.memory import set_phase

        set_phase(feature, "plan", root=root)
    return payload
