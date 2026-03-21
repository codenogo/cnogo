"""Workflow formula catalog and resolution helpers."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import load_workflow_config

DEFAULT_FORMULA_SETTINGS = {
    "default": "feature-delivery",
    "catalogPath": ".cnogo/formulas",
    "allowPlanOverride": True,
}

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

_BUILTIN_FORMULAS = {
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


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def formula_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("formulas")
    if not isinstance(raw, dict):
        return dict(DEFAULT_FORMULA_SETTINGS)
    out = dict(DEFAULT_FORMULA_SETTINGS)
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


def formula_catalog_dir(root: Path, cfg: dict[str, Any] | None = None) -> Path:
    settings = formula_settings(cfg or load_workflow_config(root))
    return root / str(settings["catalogPath"])


def _normalize_formula_contract(raw: dict[str, Any], *, source: str) -> dict[str, Any]:
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"Formula from {source} is missing non-empty name")
    defaults = raw.get("defaults")
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError(f"Formula {name!r} defaults must be an object")
    resolved_policy = _deep_merge(_DEFAULT_POLICY, defaults if isinstance(defaults, dict) else {})
    return {
        "schemaVersion": raw.get("schemaVersion", 1),
        "name": name.strip(),
        "version": str(raw.get("version", "1.0.0")).strip() or "1.0.0",
        "description": str(raw.get("description", "")).strip(),
        "source": source,
        "resolvedPolicy": resolved_policy,
    }


def load_formula_catalog(root: Path, *, cfg: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    catalog = {
        name: _normalize_formula_contract(contract, source="builtin")
        for name, contract in _BUILTIN_FORMULAS.items()
    }
    catalog_dir = formula_catalog_dir(root, cfg)
    if not catalog_dir.is_dir():
        return catalog
    for path in sorted(catalog_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        try:
            normalized = _normalize_formula_contract(raw, source=str(path.relative_to(root)))
        except ValueError:
            continue
        catalog[normalized["name"]] = normalized
    return catalog


def formula_name_from_plan(plan_contract: dict[str, Any] | None) -> str | None:
    if not isinstance(plan_contract, dict):
        return None
    raw = plan_contract.get("formula")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if isinstance(raw, dict):
        name = raw.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def resolve_formula(
    root: Path,
    *,
    cfg: dict[str, Any] | None = None,
    plan_contract: dict[str, Any] | None = None,
    requested_name: str | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = formula_settings(workflow_cfg)
    resolved_name = requested_name or (
        formula_name_from_plan(plan_contract) if settings.get("allowPlanOverride", True) else None
    ) or str(settings["default"])
    catalog = load_formula_catalog(root, cfg=workflow_cfg)
    resolved = catalog.get(resolved_name) or catalog.get(str(settings["default"])) or catalog["feature-delivery"]
    return {
        "name": resolved["name"],
        "version": resolved["version"],
        "source": resolved["source"],
        "description": resolved["description"],
        "resolvedPolicy": deepcopy(resolved["resolvedPolicy"]),
    }


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


def suggest_formula(
    root: Path,
    *,
    feature_slug: str = "",
    plan_contract: dict[str, Any] | None = None,
    context_contract: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_cfg = cfg or load_workflow_config(root)
    settings = formula_settings(workflow_cfg)
    catalog = load_formula_catalog(root, cfg=workflow_cfg)
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
        candidates.append(
            {
                "name": name,
                "matchedTerms": matched,
                "score": len(matched),
            }
        )
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


def formula_mode_preference(formula: dict[str, Any] | None) -> str:
    if not isinstance(formula, dict):
        return "auto"
    resolved = formula.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return "auto"
    execution = resolved.get("execution")
    if not isinstance(execution, dict):
        return "auto"
    mode = execution.get("modePreference", "auto")
    if mode not in {"auto", "serial", "team"}:
        return "auto"
    return mode


def formula_required_reviewers(formula: dict[str, Any] | None) -> list[str]:
    if not isinstance(formula, dict):
        return []
    resolved = formula.get("resolvedPolicy")
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


def formula_auto_spawn_configured_reviewers(formula: dict[str, Any] | None) -> bool:
    if not isinstance(formula, dict):
        return True
    resolved = formula.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    review = resolved.get("review")
    if not isinstance(review, dict):
        return True
    auto_spawn = review.get("autoSpawnConfiguredReviewers")
    return auto_spawn if isinstance(auto_spawn, bool) else True


def formula_require_package_checks(formula: dict[str, Any] | None) -> bool:
    if not isinstance(formula, dict):
        return True
    resolved = formula.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    verify = resolved.get("verify")
    if not isinstance(verify, dict):
        return True
    required = verify.get("requirePackageChecks")
    return required if isinstance(required, bool) else True


def formula_required_package_commands(formula: dict[str, Any] | None) -> list[str]:
    default = ["lint", "typecheck", "test"]
    if not isinstance(formula, dict):
        return default
    resolved = formula.get("resolvedPolicy")
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


def formula_ship_require_tracking(formula: dict[str, Any] | None) -> bool:
    if not isinstance(formula, dict):
        return True
    resolved = formula.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    ship = resolved.get("ship")
    if not isinstance(ship, dict):
        return True
    required = ship.get("requireTracking")
    return required if isinstance(required, bool) else True


def formula_ship_require_pull_request(formula: dict[str, Any] | None) -> bool:
    if not isinstance(formula, dict):
        return True
    resolved = formula.get("resolvedPolicy")
    if not isinstance(resolved, dict):
        return True
    ship = resolved.get("ship")
    if not isinstance(ship, dict):
        return True
    required = ship.get("requirePullRequest")
    return required if isinstance(required, bool) else True


def formula_watch_thresholds(
    formula: dict[str, Any] | None,
    *,
    stale_minutes: int = 10,
    review_stale_minutes: int = 60,
) -> dict[str, int]:
    out = {
        "staleMinutes": stale_minutes,
        "reviewStaleMinutes": review_stale_minutes,
    }
    if not isinstance(formula, dict):
        return out
    resolved = formula.get("resolvedPolicy")
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
