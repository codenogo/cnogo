"""Memory policy and evidence helpers.

This module holds policy lookups and completion-evidence validation so the
memory facade can stay focused on public lifecycle APIs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.workflow.shared.config import agent_team_settings as _agent_team_settings_cfg
from scripts.workflow.shared.config import enforcement_level as _enforcement_level
from scripts.workflow.shared.config import load_workflow_config
from scripts.workflow.shared.timestamps import parse_iso_timestamp

_RATIONALIZATION_PATTERNS = [
    re.compile(r"\btoo\s+small\b", re.IGNORECASE),
    re.compile(r"\btoo\s+simple\b", re.IGNORECASE),
    re.compile(r"\bskip(?:ping)?\s+tdd\b", re.IGNORECASE),
    re.compile(r"\bdo(?:n'?t| not)\s+need\s+tests?\b", re.IGNORECASE),
    re.compile(r"\balready\s+works\b", re.IGNORECASE),
    re.compile(r"\bprobably\s+fine\b", re.IGNORECASE),
    re.compile(r"\bseems?\s+fine\b", re.IGNORECASE),
    re.compile(r"\bno\s+time\b", re.IGNORECASE),
    re.compile(r"\blater\b", re.IGNORECASE),
]


def load_enforcement_levels(root: Path) -> dict[str, str]:
    cfg = load_workflow_config(root)
    return {
        "tddMode": _enforcement_level(cfg, "tddMode", "error"),
        "verificationBeforeCompletion": _enforcement_level(cfg, "verificationBeforeCompletion", "error"),
        "taskOwnership": _enforcement_level(cfg, "taskOwnership", "error"),
    }


def load_agent_team_settings(root: Path) -> dict[str, int]:
    return _agent_team_settings_cfg(load_workflow_config(root))


def contains_rationalization(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in _RATIONALIZATION_PATTERNS)


def _is_nonempty_cmd_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(v, str) and v.strip() for v in value
    )


def _outputs_dict(metadata: dict[str, Any]) -> dict[str, Any]:
    outputs = metadata.get("outputs")
    return outputs if isinstance(outputs, dict) else {}


def _verification_evidence(outputs: dict[str, Any]) -> dict[str, Any] | None:
    verification = outputs.get("verification") or outputs.get("verificationEvidence")
    return verification if isinstance(verification, dict) else None


def verification_timestamp(outputs: dict[str, Any]) -> str:
    verification = _verification_evidence(outputs)
    if not isinstance(verification, dict):
        return ""
    ts = verification.get("timestamp")
    return ts.strip() if isinstance(ts, str) else ""


def completion_evidence_findings(
    issue: Any,
    *,
    verification_level: str,
    tdd_level: str,
) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    metadata = issue.metadata if isinstance(issue.metadata, dict) else {}
    requires_evidence = bool(metadata.get("requiresCompletionEvidence"))
    if not requires_evidence and _is_nonempty_cmd_list(metadata.get("verify")):
        requires_evidence = True
    if not requires_evidence:
        return findings

    outputs_dict = _outputs_dict(metadata)

    if verification_level != "off":
        verification = _verification_evidence(outputs_dict)
        if not isinstance(verification, dict):
            findings.append((verification_level, "Missing verification evidence object in TASK_EVIDENCE."))
        else:
            commands = verification.get("commands")
            timestamp = verification.get("timestamp")
            if not _is_nonempty_cmd_list(commands):
                findings.append((verification_level, "Verification evidence must include non-empty commands[]."))
            if not isinstance(timestamp, str) or not timestamp.strip():
                findings.append((verification_level, "Verification evidence must include non-empty timestamp."))

    expected_tdd = metadata.get("tdd") if isinstance(metadata.get("tdd"), dict) else None
    has_tdd_contract = isinstance(expected_tdd, dict) and isinstance(expected_tdd.get("required"), bool)

    if tdd_level != "off" and has_tdd_contract:
        tdd = outputs_dict.get("tdd") or outputs_dict.get("tddEvidence")
        if not isinstance(tdd, dict):
            findings.append((tdd_level, "Missing TDD evidence object in TASK_EVIDENCE."))
            return findings

        required = tdd.get("required")
        if not isinstance(required, bool):
            findings.append((tdd_level, "TDD evidence must include required=true|false."))
            return findings

        expected_required = expected_tdd.get("required") if isinstance(expected_tdd, dict) else None
        if isinstance(expected_required, bool) and expected_required != required:
            findings.append((tdd_level, "TDD evidence required flag does not match plan contract."))

        if required:
            if not _is_nonempty_cmd_list(tdd.get("failingVerify")):
                findings.append((tdd_level, "TDD evidence must include non-empty failingVerify[]."))
            if not _is_nonempty_cmd_list(tdd.get("passingVerify")):
                findings.append((tdd_level, "TDD evidence must include non-empty passingVerify[]."))
        else:
            reason = tdd.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                findings.append((tdd_level, "TDD evidence with required=false must include non-empty reason."))
            elif contains_rationalization(reason):
                findings.append((tdd_level, "TDD exemption reason appears rationalized."))

    return findings
