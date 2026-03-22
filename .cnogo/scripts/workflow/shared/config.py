"""Shared workflow configuration helpers.

These helpers centralize parsing of ``docs/planning/WORKFLOW.json`` so the
runtime, validator, and memory engine stop re-implementing the same policy
lookups in different files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.workflow_utils import load_workflow as _load_workflow_util

DEFAULT_TOKEN_BUDGETS = {
    "enabled": True,
    "commandWordMax": 430,
    "commandsTotalWordMax": 8000,
    "contextWordMax": 1300,
    "planWordMax": 1200,
    "summaryWordMax": 900,
    "reviewWordMax": 1400,
    "researchWordMax": 2200,
    "shapeWordMax": 1600,
    "brainstormWordMax": 1400,
}

DEFAULT_BOOTSTRAP_CONTEXT = {
    "enabled": True,
    "rootClaudeWordMax": 500,
    "workflowClaudeWordMax": 450,
    "commandSetWordMax": 7300,
}

DEFAULT_WATCH_SETTINGS = {
    "enabled": True,
    "patrolIntervalMinutes": 15,
    "historyLimit": 25,
    "attentionLimit": 50,
}

DEFAULT_SCHEDULER_SETTINGS = {
    "enabled": True,
    "mode": "hybrid",
    "tickIntervalMinutes": 15,
    "opportunisticCommands": [
        "session-status",
        "run-list",
        "run-attention",
        "work-list",
        "work-show",
        "work-next",
    ],
}

DEFAULT_DISPATCHER_SETTINGS = {
    "enabled": True,
    "defaultWipLimit": 2,
    "overlapPolicy": "allow",
    "autonomy": "high",
    "leaseTimeoutMinutes": 45,
}


def _is_positive_int(val: Any, *, allow_zero: bool = False) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and (val >= 0 if allow_zero else val > 0)


def load_workflow_config(root: Path | None = None) -> dict[str, Any]:
    cfg = _load_workflow_util(root)
    return cfg if isinstance(cfg, dict) else {}


def workflow_packages(cfg: dict[str, Any], *, sort_longest_first: bool = True) -> list[dict[str, Any]]:
    packages = cfg.get("packages")
    if not isinstance(packages, list):
        return []
    out: list[dict[str, Any]] = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        path = package.get("path")
        if isinstance(path, str) and path.strip():
            out.append(package)
    if sort_longest_first:
        out.sort(key=lambda item: len(str(item.get("path") or "")), reverse=True)
    return out


def enforcement_level(cfg: dict[str, Any], key: str, default: str = "error") -> str:
    enforcement = cfg.get("enforcement")
    if not isinstance(enforcement, dict):
        return default
    level = enforcement.get(key, default)
    if level not in {"off", "warn", "error"}:
        return default
    return level


def freshness_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": True,
        "contextMaxAgeDays": 30,
        "planMaxAgeDaysWithoutSummary": 14,
        "summaryMaxAgeDaysWithoutReview": 7,
    }
    raw = cfg.get("freshness")
    if not isinstance(raw, dict):
        return defaults
    out = dict(defaults)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled
    for key in (
        "contextMaxAgeDays",
        "planMaxAgeDaysWithoutSummary",
        "summaryMaxAgeDaysWithoutReview",
    ):
        val = raw.get(key)
        if _is_positive_int(val, allow_zero=True):
            out[key] = val
    return out


def token_budgets_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    perf = cfg.get("performance")
    if not isinstance(perf, dict):
        return dict(DEFAULT_TOKEN_BUDGETS)
    raw = perf.get("tokenBudgets")
    if not isinstance(raw, dict):
        return dict(DEFAULT_TOKEN_BUDGETS)

    out = dict(DEFAULT_TOKEN_BUDGETS)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled

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
        val = raw.get(key)
        if _is_positive_int(val):
            out[key] = val

    return out


def bootstrap_context_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    perf = cfg.get("performance")
    if not isinstance(perf, dict):
        return dict(DEFAULT_BOOTSTRAP_CONTEXT)
    raw = perf.get("bootstrapContext")
    if not isinstance(raw, dict):
        return dict(DEFAULT_BOOTSTRAP_CONTEXT)

    out = dict(DEFAULT_BOOTSTRAP_CONTEXT)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled
    for key in ("rootClaudeWordMax", "workflowClaudeWordMax", "commandSetWordMax"):
        val = raw.get(key)
        if _is_positive_int(val):
            out[key] = val
    return out


def watch_settings_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("watch")
    if not isinstance(raw, dict):
        return dict(DEFAULT_WATCH_SETTINGS)

    out = dict(DEFAULT_WATCH_SETTINGS)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled
    for key in ("patrolIntervalMinutes", "historyLimit", "attentionLimit"):
        value = raw.get(key)
        if _is_positive_int(value):
            out[key] = value
    return out


def scheduler_settings_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("scheduler")
    if not isinstance(raw, dict):
        return dict(DEFAULT_SCHEDULER_SETTINGS)

    out = dict(DEFAULT_SCHEDULER_SETTINGS)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled
    mode = raw.get("mode")
    if mode in {"hybrid", "supervisor"}:
        out["mode"] = mode
    tick = raw.get("tickIntervalMinutes")
    if _is_positive_int(tick):
        out["tickIntervalMinutes"] = tick
    commands = raw.get("opportunisticCommands")
    if isinstance(commands, list):
        parsed = []
        seen: set[str] = set()
        for value in commands:
            if not isinstance(value, str) or not value.strip():
                continue
            command = value.strip()
            if command in seen:
                continue
            seen.add(command)
            parsed.append(command)
        if parsed:
            out["opportunisticCommands"] = parsed
    return out


def dispatcher_settings_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    raw = cfg.get("dispatcher")
    if not isinstance(raw, dict):
        return dict(DEFAULT_DISPATCHER_SETTINGS)

    out = dict(DEFAULT_DISPATCHER_SETTINGS)
    enabled = raw.get("enabled")
    if isinstance(enabled, bool):
        out["enabled"] = enabled
    wip = raw.get("defaultWipLimit")
    if _is_positive_int(wip):
        out["defaultWipLimit"] = wip
    overlap = raw.get("overlapPolicy")
    if overlap in {"allow", "block"}:
        out["overlapPolicy"] = overlap
    autonomy = raw.get("autonomy")
    if autonomy in {"low", "medium", "high"}:
        out["autonomy"] = autonomy
    lease_timeout = raw.get("leaseTimeoutMinutes")
    if _is_positive_int(lease_timeout):
        out["leaseTimeoutMinutes"] = lease_timeout
    return out


def agent_team_settings(cfg: dict[str, Any]) -> dict[str, int]:
    defaults = {
        "staleIndicatorMinutes": 10,
        "maxTakeoversPerTask": 2,
    }
    teams = cfg.get("agentTeams")
    if not isinstance(teams, dict):
        return defaults

    out = dict(defaults)
    stale = teams.get("staleIndicatorMinutes")
    if _is_positive_int(stale):
        out["staleIndicatorMinutes"] = stale
    max_takeovers = teams.get("maxTakeoversPerTask")
    if isinstance(max_takeovers, int) and not isinstance(max_takeovers, bool) and max_takeovers >= 0:
        out["maxTakeoversPerTask"] = max_takeovers
    return out
