"""Workflow checks configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import load_workflow_config as _shared_load_workflow
from scripts.workflow.shared.config import workflow_packages as _shared_workflow_packages


def load_workflow(root: Path | None = None) -> dict[str, Any]:
    return _shared_load_workflow(root)


def packages_from_workflow(wf: dict[str, Any]) -> list[dict[str, Any]]:
    return _shared_workflow_packages(wf, sort_longest_first=False)


def invariants_cfg(wf: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "enabled": True,
        "scanScope": "changed",
        "maxFileLines": 800,
        "maxFileLinesExceptions": [],
        "maxLineLength": 140,
        "todoRequiresTicket": True,
        "pythonBareExcept": "warn",
        "forbiddenImportPatterns": [
            {
                "pattern": r"^\s*from\s+\S+\s+import\s+\*",
                "mode": "regex",
                "severity": "warn",
                "message": "Avoid wildcard imports.",
            }
        ],
    }
    raw = wf.get("invariants")
    if not isinstance(raw, dict):
        return defaults
    cfg = dict(defaults)
    if isinstance(raw.get("enabled"), bool):
        cfg["enabled"] = raw["enabled"]
    if raw.get("scanScope") in {"changed", "repo"}:
        cfg["scanScope"] = raw["scanScope"]
    for key in ("maxFileLines", "maxLineLength"):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            cfg[key] = value
    exceptions = raw.get("maxFileLinesExceptions")
    if isinstance(exceptions, list):
        normalized_exceptions: list[str] = []
        for item in exceptions:
            if isinstance(item, str) and item.strip():
                normalized_exceptions.append(item.strip())
        cfg["maxFileLinesExceptions"] = normalized_exceptions
    if isinstance(raw.get("todoRequiresTicket"), bool):
        cfg["todoRequiresTicket"] = raw["todoRequiresTicket"]
    if raw.get("pythonBareExcept") in {"off", "warn", "fail"}:
        cfg["pythonBareExcept"] = raw["pythonBareExcept"]
    forbidden_import_patterns = raw.get("forbiddenImportPatterns")
    if isinstance(forbidden_import_patterns, list):
        normalized: list[dict[str, str]] = []
        for item in forbidden_import_patterns:
            if not isinstance(item, dict):
                continue
            pattern = item.get("pattern")
            if not isinstance(pattern, str) or not pattern.strip():
                continue
            mode = item.get("mode", "substring")
            if mode not in {"substring", "regex"}:
                mode = "substring"
            severity = item.get("severity", "warn")
            if severity not in {"warn", "fail"}:
                severity = "warn"
            message = item.get("message")
            normalized.append(
                {
                    "pattern": pattern,
                    "mode": mode,
                    "severity": severity,
                    "message": message if isinstance(message, str) and message.strip() else "Forbidden import pattern matched.",
                }
            )
        cfg["forbiddenImportPatterns"] = normalized
    return cfg


def entropy_cfg(wf: dict[str, Any]) -> dict[str, Any]:
    defaults = {"enabled": True, "mode": "background", "maxFilesPerTask": 3, "maxTasksPerRun": 3}
    raw = wf.get("entropy")
    if not isinstance(raw, dict):
        return defaults
    cfg = dict(defaults)
    if isinstance(raw.get("enabled"), bool):
        cfg["enabled"] = raw["enabled"]
    if raw.get("mode") in {"background", "manual"}:
        cfg["mode"] = raw["mode"]
    for key in ("maxFilesPerTask", "maxTasksPerRun"):
        value = raw.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            cfg[key] = value
    return cfg


def checks_runtime_cfg(
    wf: dict[str, Any],
    *,
    default_command_timeout_sec: int,
    default_output_compact_max_lines: int,
    default_output_compact_fail_tail_lines: int,
    default_output_compact_pass_lines: int,
    default_tee_min_chars: int,
    default_tee_max_files: int,
    default_tee_max_file_size: int,
) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "checkScope": "auto",
        "changedFilesFallback": "none",
        "commandTimeoutSec": default_command_timeout_sec,
        "outputCompaction": {
            "enabled": True,
            "maxLines": default_output_compact_max_lines,
            "failTailLines": default_output_compact_fail_tail_lines,
            "passLines": default_output_compact_pass_lines,
            "dedupe": True,
        },
        "outputRecovery": {
            "enabled": True,
            "mode": "failures",
            "minChars": default_tee_min_chars,
            "maxFiles": default_tee_max_files,
            "maxFileSize": default_tee_max_file_size,
            "directory": ".cnogo/tee",
        },
        "tokenTelemetry": {"enabled": True},
        "hookOptimization": {
            "enabled": True,
            "mode": "suggest",
            "showSuggestions": True,
            "logFile": ".cnogo/command-usage.jsonl",
        },
    }
    perf = wf.get("performance")
    if not isinstance(perf, dict):
        return defaults

    cfg = dict(defaults)
    scope = perf.get("checkScope")
    if scope in {"auto", "changed", "all"}:
        cfg["checkScope"] = scope
    fallback = perf.get("changedFilesFallback")
    if fallback in {"none", "head"}:
        cfg["changedFilesFallback"] = fallback
    timeout = perf.get("commandTimeoutSec")
    if isinstance(timeout, int) and not isinstance(timeout, bool) and timeout > 0:
        cfg["commandTimeoutSec"] = timeout

    compact_raw = perf.get("outputCompaction")
    if isinstance(compact_raw, dict):
        compact = dict(defaults["outputCompaction"])
        enabled = compact_raw.get("enabled")
        if isinstance(enabled, bool):
            compact["enabled"] = enabled
        for key in ("maxLines", "failTailLines", "passLines"):
            value = compact_raw.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                compact[key] = value
        dedupe = compact_raw.get("dedupe")
        if isinstance(dedupe, bool):
            compact["dedupe"] = dedupe
        cfg["outputCompaction"] = compact

    recovery_raw = perf.get("outputRecovery")
    if isinstance(recovery_raw, dict):
        recovery = dict(defaults["outputRecovery"])
        enabled = recovery_raw.get("enabled")
        if isinstance(enabled, bool):
            recovery["enabled"] = enabled
        mode = recovery_raw.get("mode")
        if mode in {"failures", "always", "never"}:
            recovery["mode"] = mode
        for key in ("minChars", "maxFiles", "maxFileSize"):
            value = recovery_raw.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                recovery[key] = value
        directory = recovery_raw.get("directory")
        if isinstance(directory, str) and directory.strip():
            recovery["directory"] = directory.strip()
        cfg["outputRecovery"] = recovery

    telemetry_raw = perf.get("tokenTelemetry")
    if isinstance(telemetry_raw, dict):
        telemetry = dict(defaults["tokenTelemetry"])
        enabled = telemetry_raw.get("enabled")
        if isinstance(enabled, bool):
            telemetry["enabled"] = enabled
        cfg["tokenTelemetry"] = telemetry

    hook_raw = perf.get("hookOptimization")
    if isinstance(hook_raw, dict):
        hook_cfg = dict(defaults["hookOptimization"])
        enabled = hook_raw.get("enabled")
        if isinstance(enabled, bool):
            hook_cfg["enabled"] = enabled
        mode = hook_raw.get("mode")
        if mode in {"suggest", "enforce", "off"}:
            hook_cfg["mode"] = mode
        show = hook_raw.get("showSuggestions")
        if isinstance(show, bool):
            hook_cfg["showSuggestions"] = show
        log_file = hook_raw.get("logFile")
        if isinstance(log_file, str) and log_file.strip():
            hook_cfg["logFile"] = log_file.strip()
        cfg["hookOptimization"] = hook_cfg

    return cfg
