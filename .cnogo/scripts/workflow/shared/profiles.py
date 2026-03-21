"""Workflow profile catalog and compatibility helpers.

Canonical product language is ``profile``. Legacy ``formula`` naming remains
accepted during the migration window via aliases and fallback loaders.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import load_workflow_config

DEFAULT_PROFILE_SETTINGS = {
    "default": "feature-delivery",
    "catalogPath": ".cnogo/profiles",
    "allowPlanOverride": True,
}
DEFAULT_FORMULA_SETTINGS = DEFAULT_PROFILE_SETTINGS

_DEFAULT_POLICY = {
    "execution": {
        "modePreference": "auto",
        "preferTeamWhenSafe": True,
    },
    "verify": {
        "requirePackageChecks": True,
        "requiredPackageCommands": ["lint", "typecheck", "test"],
    },
    "review": {
        "autoSpawnConfiguredReviewers": True,
        "requiredReviewers": [],
    },
    "ship": {
        "requireTracking": True,
        "requirePullRequest": True,
    },
    "watch": {
        "staleMinutes": 10,
        "reviewStaleMinutes": 60,
    },
}

_BUILTIN_PROFILES = {
    "feature-delivery": {
        "schemaVersion": 1,
        "name": "feature-delivery",
        "version": "1.0.0",
        "description": "Default feature flow for product work with team execution when safe, adversarial review, and tracked ship completion.",
        "defaults": {
            "execution": {"modePreference": "auto", "preferTeamWhenSafe": True},
            "verify": {"requirePackageChecks": True, "requiredPackageCommands": ["lint", "typecheck", "test"]},
            "review": {
                "autoSpawnConfiguredReviewers": True,
                "requiredReviewers": ["code-reviewer", "security-scanner", "perf-analyzer"],
            },
            "ship": {"requireTracking": True, "requirePullRequest": True},
            "watch": {"staleMinutes": 10, "reviewStaleMinutes": 60},
        },
    },
    "migration-rollout": {
        "schemaVersion": 1,
        "name": "migration-rollout",
        "version": "1.0.0",
        "description": "Safer rollout profile for schema, backfill, and data-moving changes that should bias toward serial execution and explicit review evidence.",
        "defaults": {
            "execution": {"modePreference": "serial", "preferTeamWhenSafe": False},
            "verify": {"requirePackageChecks": True, "requiredPackageCommands": ["lint", "typecheck", "test"]},
            "review": {
                "autoSpawnConfiguredReviewers": True,
                "requiredReviewers": ["code-reviewer", "security-scanner"],
            },
            "ship": {"requireTracking": True, "requirePullRequest": True},
            "watch": {"staleMinutes": 5, "reviewStaleMinutes": 30},
        },
    },
    "release-cut": {
        "schemaVersion": 1,
        "name": "release-cut",
        "version": "1.0.0",
        "description": "Release-focused profile with serial preference, reviewer rigor, and tracked ship completion for coordinated branch and PR work.",
        "defaults": {
            "execution": {"modePreference": "serial", "preferTeamWhenSafe": False},
            "verify": {"requirePackageChecks": True, "requiredPackageCommands": ["lint", "typecheck", "test"]},
            "review": {
                "autoSpawnConfiguredReviewers": True,
                "requiredReviewers": ["code-reviewer", "perf-analyzer"],
            },
            "ship": {"requireTracking": True, "requirePullRequest": True},
            "watch": {"staleMinutes": 10, "reviewStaleMinutes": 30},
        },
    },
    "debug-fix": {
        "schemaVersion": 1,
        "name": "debug-fix",
        "version": "1.0.0",
        "description": "Fast-but-governed debugging profile for bug fixes that still need review and ship tracking, while allowing auto execution when task safety is clear.",
        "defaults": {
            "execution": {"modePreference": "auto", "preferTeamWhenSafe": True},
            "verify": {"requirePackageChecks": True, "requiredPackageCommands": ["lint", "typecheck", "test"]},
            "review": {
                "autoSpawnConfiguredReviewers": True,
                "requiredReviewers": ["code-reviewer"],
            },
            "ship": {"requireTracking": True, "requirePullRequest": True},
            "watch": {"staleMinutes": 10, "reviewStaleMinutes": 45},
        },
    },
}

_SUGGESTION_KEYWORDS = {
    "migration-rollout": [
        "migration",
        "migrate",
        "schema",
        "backfill",
        "database",
        "sql",
        "table",
        "column",
        "index",
        "rollout",
        "data",
    ],
    "release-cut": [
        "release",
        "version",
        "tag",
        "changelog",
        "cut release",
        "publish",
    ],
    "debug-fix": [
        "bug",
        "fix",
        "debug",
        "regression",
        "hotfix",
        "incident",
        "failure",
        "broken",
        "repair",
    ],
}

_SUGGESTION_PRIORITY = {
    "migration-rollout": 0,
    "release-cut": 1,
    "debug-fix": 2,
}
_PROFILE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _legacy_formula_settings(cfg: dict[str, Any]) -> dict[str, Any] | None:
    raw = cfg.get("formulas")
    return raw if isinstance(raw, dict) else None


def profile_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("profiles")
    if not isinstance(raw, dict):
        raw = _legacy_formula_settings(cfg)
    if not isinstance(raw, dict):
        return dict(DEFAULT_PROFILE_SETTINGS)
    out = dict(DEFAULT_PROFILE_SETTINGS)
    default_name = raw.get("default")
    if isinstance(default_name, str) and default_name.strip():
        out["default"] = default_name.strip()
    catalog_path = raw.get("catalogPath")
    if isinstance(catalog_path, str) and catalog_path.strip():
        out["catalogPath"] = catalog_path.strip()
    allow_plan_override = raw.get("allowPlanOverride")
    if isinstance(allow_plan_override, bool):
        out["allowPlanOverride"] = allow_plan_override
    return out


def formula_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    return profile_settings(cfg)


def profile_catalog_dir(root: Path, cfg: dict[str, Any] | None = None) -> Path:
    settings = profile_settings(cfg or load_workflow_config(root))
    return root / str(settings["catalogPath"])


def legacy_formula_catalog_dir(root: Path, cfg: dict[str, Any] | None = None) -> Path:
    workflow_cfg = cfg or load_workflow_config(root)
    legacy = _legacy_formula_settings(workflow_cfg)
    if isinstance(legacy, dict):
        catalog_path = legacy.get("catalogPath")
        if isinstance(catalog_path, str) and catalog_path.strip():
            return root / catalog_path.strip()
    return root / ".cnogo" / "formulas"


def formula_catalog_dir(root: Path, cfg: dict[str, Any] | None = None) -> Path:
    return legacy_formula_catalog_dir(root, cfg)


def _normalize_profile_contract(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Profile from {source} is missing non-empty name")
    defaults = raw.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError(f"Profile {name!r} defaults must be an object")
    resolved_policy = _deep_merge(_DEFAULT_POLICY, defaults if isinstance(defaults, dict) else {})
    return {
        "schemaVersion": raw.get("schemaVersion", 1),
        "name": name.strip(),
        "version": str(raw.get("version", "1.0.0")).strip() or "1.0.0",
        "description": str(raw.get("description", "")).strip(),
        "source": source,
        "resolvedPolicy": resolved_policy,
    }


def _load_catalog_from_dir(
    catalog: dict[str, dict[str, Any]],
    root: Path,
    catalog_dir: Path,
) -> None:
    if not catalog_dir.is_dir():
        return
    for path in sorted(catalog_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        try:
            normalized = _normalize_profile_contract(raw, source=str(path.relative_to(root)))
        except ValueError:
            continue
        catalog[normalized["name"]] = normalized


def load_profile_catalog(root: Path, *, cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    workflow_cfg = cfg or load_workflow_config(root)
    catalog = {
        name: _normalize_profile_contract(contract, source="builtin")
        for name, contract in _BUILTIN_PROFILES.items()
    }
    legacy_dir = legacy_formula_catalog_dir(root, workflow_cfg)
    canonical_dir = profile_catalog_dir(root, workflow_cfg)
    if legacy_dir != canonical_dir:
        _load_catalog_from_dir(catalog, root, legacy_dir)
    _load_catalog_from_dir(catalog, root, canonical_dir)
    return catalog


def load_formula_catalog(root: Path, *, cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    return load_profile_catalog(root, cfg=cfg)


def profile_name_from_plan(plan_contract: dict[str, Any] | None) -> str | None:
    if not isinstance(plan_contract, dict):
        return None
    for key in ("profile", "formula"):
        raw = plan_contract.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        if isinstance(raw, dict):
            name = raw.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def formula_name_from_plan(plan_contract: dict[str, Any] | None) -> str | None:
    return profile_name_from_plan(plan_contract)


def resolve_profile(
    root: Path,
    *,
    cfg: dict[str, Any] | None = None,
    plan_contract: dict[str, Any] | None = None,
    requested_name: str | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = profile_settings(workflow_cfg)
    resolved_name = requested_name or (
        profile_name_from_plan(plan_contract) if settings.get("allowPlanOverride", True) else None
    ) or str(settings["default"])
    catalog = load_profile_catalog(root, cfg=workflow_cfg)
    resolved = catalog.get(resolved_name) or catalog.get(str(settings["default"])) or catalog["feature-delivery"]
    return {
        "name": resolved["name"],
        "version": resolved["version"],
        "source": resolved["source"],
        "description": resolved["description"],
        "resolvedPolicy": deepcopy(resolved["resolvedPolicy"]),
    }


def resolve_formula(
    root: Path,
    *,
    cfg: dict[str, Any] | None = None,
    plan_contract: dict[str, Any] | None = None,
    requested_name: str | None = None,
) -> dict[str, Any]:
    return resolve_profile(
        root,
        cfg=cfg,
        plan_contract=plan_contract,
        requested_name=requested_name,
    )


def is_profile_name(value: str) -> bool:
    return bool(isinstance(value, str) and _PROFILE_NAME_RE.match(value.strip()))


def is_formula_name(value: str) -> bool:
    return is_profile_name(value)


def scaffold_profile_contract(
    name: str,
    *,
    base_profile: dict[str, Any] | None = None,
    description: str = "",
) -> dict[str, Any]:
    if not is_profile_name(name):
        raise ValueError(
            "Profile names must be lowercase slug strings like 'feature-delivery' or 'migration-rollout'."
        )
    base_policy = deepcopy(_DEFAULT_POLICY)
    if isinstance(base_profile, dict):
        resolved = base_profile.get("resolvedPolicy")
        if isinstance(resolved, dict):
            base_policy = deepcopy(resolved)
    return {
        "schemaVersion": 1,
        "name": name.strip(),
        "version": "1.0.0",
        "description": description.strip() or f"Custom workflow policy for `{name.strip()}`.",
        "defaults": base_policy,
    }


def scaffold_formula_contract(
    name: str,
    *,
    base_formula: dict[str, Any] | None = None,
    description: str = "",
) -> dict[str, Any]:
    return scaffold_profile_contract(name, base_profile=base_formula, description=description)


def _collect_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return [trimmed] if trimmed else []
    if isinstance(value, dict):
        out: list[str] = []
        for nested in value.values():
            out.extend(_collect_strings(nested))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for nested in value:
            out.extend(_collect_strings(nested))
        return out
    return []


def _keyword_present(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def suggest_profile(
    root: Path,
    *,
    feature_slug: str = "",
    plan_contract: dict[str, Any] | None = None,
    context_contract: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = profile_settings(workflow_cfg)
    catalog = load_profile_catalog(root, cfg=workflow_cfg)
    text_parts = [feature_slug]
    text_parts.extend(_collect_strings(plan_contract))
    text_parts.extend(_collect_strings(context_contract))
    haystack = " ".join(part.lower() for part in text_parts if isinstance(part, str))
    candidates: list[dict[str, Any]] = []
    for name, keywords in _SUGGESTION_KEYWORDS.items():
        if name not in catalog:
            continue
        matched = [keyword for keyword in keywords if _keyword_present(haystack, keyword)]
        if not matched:
            continue
        candidates.append({"name": name, "matchedTerms": matched, "score": len(matched)})
    if candidates:
        candidates.sort(key=lambda item: (-int(item["score"]), _SUGGESTION_PRIORITY.get(str(item["name"]), 99)))
        chosen = candidates[0]
        score = int(chosen["score"])
        confidence = 0.95 if score >= 3 else 0.8 if score == 2 else 0.65
        return {
            "name": str(chosen["name"]),
            "confidence": confidence,
            "matchedTerms": list(chosen["matchedTerms"]),
            "reason": "Matched workflow signals for "
            + f"`{chosen['name']}`: "
            + ", ".join(f"`{term}`" for term in chosen["matchedTerms"]),
        }
    default_name = str(settings["default"])
    if default_name not in catalog:
        default_name = "feature-delivery"
    return {
        "name": default_name,
        "confidence": 0.5,
        "matchedTerms": [],
        "reason": f"No stronger migration/release/debug signals found; using repo default `{default_name}`.",
    }


def suggest_formula(
    root: Path,
    *,
    feature_slug: str = "",
    plan_contract: dict[str, Any] | None = None,
    context_contract: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return suggest_profile(
        root,
        feature_slug=feature_slug,
        plan_contract=plan_contract,
        context_contract=context_contract,
        cfg=cfg,
    )


def profile_mode_preference(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return "auto"
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return "auto"
    execution = resolved.get("execution")
    if not isinstance(execution, dict):
        return "auto"
    mode = execution.get("modePreference", "auto")
    if mode not in {"auto", "serial", "team"}:
        return "auto"
    return mode


def formula_mode_preference(formula: dict[str, Any] | None) -> str:
    return profile_mode_preference(formula)


def profile_required_reviewers(profile: dict[str, Any] | None) -> list[str]:
    if not isinstance(profile, dict):
        return []
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return []
    review = resolved.get("review")
    if not isinstance(review, dict):
        return []
    required = review.get("requiredReviewers")
    if not isinstance(required, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for reviewer in required:
        if not isinstance(reviewer, str) or not reviewer.strip():
            continue
        value = reviewer.strip()
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def formula_required_reviewers(formula: dict[str, Any] | None) -> list[str]:
    return profile_required_reviewers(formula)


def profile_auto_spawn_configured_reviewers(profile: dict[str, Any] | None) -> bool:
    if not isinstance(profile, dict):
        return True
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    review = resolved.get("review")
    if not isinstance(review, dict):
        return True
    auto_spawn = review.get("autoSpawnConfiguredReviewers")
    return auto_spawn if isinstance(auto_spawn, bool) else True


def formula_auto_spawn_configured_reviewers(formula: dict[str, Any] | None) -> bool:
    return profile_auto_spawn_configured_reviewers(formula)


def profile_require_package_checks(profile: dict[str, Any] | None) -> bool:
    if not isinstance(profile, dict):
        return True
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    verify = resolved.get("verify")
    if not isinstance(verify, dict):
        return True
    required = verify.get("requirePackageChecks")
    return required if isinstance(required, bool) else True


def formula_require_package_checks(formula: dict[str, Any] | None) -> bool:
    return profile_require_package_checks(formula)


def profile_required_package_commands(profile: dict[str, Any] | None) -> list[str]:
    default = ["lint", "typecheck", "test"]
    if not isinstance(profile, dict):
        return default
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return default
    verify = resolved.get("verify")
    if not isinstance(verify, dict):
        return default
    required = verify.get("requiredPackageCommands")
    if not isinstance(required, list):
        return default
    out: list[str] = []
    seen: set[str] = set()
    for command_name in required:
        if not isinstance(command_name, str):
            continue
        value = command_name.strip()
        if value not in {"lint", "typecheck", "test"} or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out or default


def formula_required_package_commands(formula: dict[str, Any] | None) -> list[str]:
    return profile_required_package_commands(formula)


def profile_ship_require_tracking(profile: dict[str, Any] | None) -> bool:
    if not isinstance(profile, dict):
        return True
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    ship = resolved.get("ship")
    if not isinstance(ship, dict):
        return True
    required = ship.get("requireTracking")
    return required if isinstance(required, bool) else True


def formula_ship_require_tracking(formula: dict[str, Any] | None) -> bool:
    return profile_ship_require_tracking(formula)


def profile_ship_require_pull_request(profile: dict[str, Any] | None) -> bool:
    if not isinstance(profile, dict):
        return True
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    ship = resolved.get("ship")
    if not isinstance(ship, dict):
        return True
    required = ship.get("requirePullRequest")
    return required if isinstance(required, bool) else True


def formula_ship_require_pull_request(formula: dict[str, Any] | None) -> bool:
    return profile_ship_require_pull_request(formula)


def profile_watch_thresholds(
    profile: dict[str, Any] | None,
    *,
    stale_minutes: int = 10,
    review_stale_minutes: int = 60,
) -> dict[str, int]:
    out = {"staleMinutes": stale_minutes, "reviewStaleMinutes": review_stale_minutes}
    if not isinstance(profile, dict):
        return out
    resolved = profile.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return out
    watch = resolved.get("watch")
    if not isinstance(watch, dict):
        return out
    stale = watch.get("staleMinutes")
    if isinstance(stale, int) and not isinstance(stale, bool) and stale > 0:
        out["staleMinutes"] = stale
    review_stale = watch.get("reviewStaleMinutes")
    if isinstance(review_stale, int) and not isinstance(review_stale, bool) and review_stale > 0:
        out["reviewStaleMinutes"] = review_stale
    return out


def formula_watch_thresholds(
    formula: dict[str, Any] | None,
    *,
    stale_minutes: int = 10,
    review_stale_minutes: int = 60,
) -> dict[str, int]:
    return profile_watch_thresholds(
        formula,
        stale_minutes=stale_minutes,
        review_stale_minutes=review_stale_minutes,
    )
