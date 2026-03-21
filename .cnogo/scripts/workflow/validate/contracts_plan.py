"""Plan contract validation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

MEMORY_ID_RE = re.compile(r"^cn-[a-z0-9]+(\.\d+)*$")
_RATIONALIZATION_PATTERNS = [
    re.compile(r"\btoo\s+small\b", re.IGNORECASE),
    re.compile(r"\btrivial\b", re.IGNORECASE),
    re.compile(r"\bjust\s+(?:a\s+)?rename\b", re.IGNORECASE),
    re.compile(r"\bjust\s+(?:a\s+)?refactor\b", re.IGNORECASE),
    re.compile(r"\bobvious\b", re.IGNORECASE),
    re.compile(r"\bdo(?:n'?t| not)\s+need\s+tests?\b", re.IGNORECASE),
    re.compile(r"\balready\s+works\b", re.IGNORECASE),
    re.compile(r"\bprobably\s+fine\b", re.IGNORECASE),
    re.compile(r"\bseems?\s+fine\b", re.IGNORECASE),
    re.compile(r"\bno\s+time\b", re.IGNORECASE),
    re.compile(r"\blater\b", re.IGNORECASE),
    re.compile(r"\bmanual\s+only\b", re.IGNORECASE),
]
_FAILURE_SCENARIO_RE = re.compile(
    r"\b(error|fail|invalid|unauthori[sz]ed|forbidden|timeout|duplicate|conflict|nil|null|empty body|not found)\b",
    re.IGNORECASE,
)


def validate_memory_id(value: Any, field_name: str, findings: list[Any], path: Path, *, finding_type: Any) -> None:
    """Validate optional memory ID fields (memoryEpicId, memoryId)."""
    if value is None:
        return
    if not isinstance(value, str) or not MEMORY_ID_RE.match(value):
        findings.append(
            finding_type(
                "WARN",
                f"{field_name} has invalid format (expected cn-<base36>[.N]): {value!r}",
                str(path),
            )
        )


def contains_rationalization(text: str) -> bool:
    return any(pattern.search(text) for pattern in _RATIONALIZATION_PATTERNS)


def policy_level_to_finding(level: str) -> str:
    return "ERROR" if level == "error" else "WARN"


def validate_plan_contract(
    contract: Any,
    findings: list[Any],
    path: Path,
    *,
    tdd_mode_level: str = "error",
    operating_principles_level: str = "warn",
    is_positive_int: Any,
    finding_type: Any,
) -> None:
    if not isinstance(contract, dict):
        findings.append(finding_type("ERROR", "Plan contract must be a JSON object.", str(path)))
        return

    if "schemaVersion" not in contract:
        findings.append(finding_type("WARN", "Plan contract missing schemaVersion (recommended).", str(path)))
    schema_version_raw = contract.get("schemaVersion", 1)
    schema_version = schema_version_raw if is_positive_int(schema_version_raw, allow_zero=True) else 1

    validate_memory_id(contract.get("memoryEpicId"), "memoryEpicId", findings, path, finding_type=finding_type)

    parallelizable = contract.get("parallelizable")
    if parallelizable is not None and not isinstance(parallelizable, bool):
        findings.append(finding_type("WARN", "Plan contract: 'parallelizable' should be a boolean if present.", str(path)))

    formula = contract.get("formula")
    if formula is not None:
        if isinstance(formula, str):
            if not formula.strip():
                findings.append(finding_type("WARN", "Plan contract formula should be a non-empty string.", str(path)))
        elif isinstance(formula, dict):
            name = formula.get("name")
            if not isinstance(name, str) or not name.strip():
                findings.append(
                    finding_type(
                        "WARN",
                        "Plan contract formula object should include non-empty 'name'.",
                        str(path),
                    )
                )
        else:
            findings.append(
                finding_type(
                    "WARN",
                    "Plan contract formula should be a string or object with name.",
                    str(path),
                )
            )

    tasks = contract.get("tasks")
    if not isinstance(tasks, list):
        findings.append(finding_type("ERROR", "Plan contract must include 'tasks' array.", str(path)))
        return

    if len(tasks) == 0:
        findings.append(finding_type("ERROR", "Plan must include at least 1 task.", str(path)))
    if len(tasks) > 3:
        findings.append(finding_type("ERROR", "Plan has >3 tasks. Split into multiple plans to keep context fresh.", str(path)))

    for idx, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            findings.append(finding_type("ERROR", f"Task {idx} must be an object.", str(path)))
            continue
        name = task.get("name")
        if not isinstance(name, str) or not name.strip():
            findings.append(finding_type("ERROR", f"Task {idx} missing non-empty 'name'.", str(path)))
        files = task.get("files")
        if not isinstance(files, list) or not files:
            findings.append(finding_type("ERROR", f"Task {idx} must include non-empty 'files' array.", str(path)))
        else:
            for file_path in files:
                if not isinstance(file_path, str) or not file_path.strip():
                    findings.append(finding_type("ERROR", f"Task {idx} has empty file path.", str(path)))
                    continue
                if "*" in file_path or "…" in file_path or file_path.endswith("/"):
                    findings.append(finding_type("WARN", f"Task {idx} file path looks ambiguous: {file_path!r}", str(path)))
        verify = task.get("verify")
        if not isinstance(verify, list) or not verify or not all(isinstance(item, str) and item.strip() for item in verify):
            findings.append(finding_type("ERROR", f"Task {idx} must include non-empty 'verify' array of commands.", str(path)))

        validate_memory_id(task.get("memoryId"), f"Task {idx} memoryId", findings, path, finding_type=finding_type)
        deletions = task.get("deletions")
        if deletions is not None and (not isinstance(deletions, list) or not all(isinstance(item, str) for item in deletions)):
            findings.append(finding_type("WARN", f"Task {idx} 'deletions' must be a list of strings.", str(path)))

        if schema_version >= 2 and tdd_mode_level != "off":
            policy_level = policy_level_to_finding(tdd_mode_level)

            micro_steps = task.get("microSteps")
            if not isinstance(micro_steps, list) or not micro_steps:
                findings.append(
                    finding_type(
                        policy_level,
                        f"Task {idx} schemaVersion>=2 requires non-empty 'microSteps' array.",
                        str(path),
                    )
                )
            elif not all(isinstance(step, str) and step.strip() for step in micro_steps):
                findings.append(
                    finding_type(
                        policy_level,
                        f"Task {idx} microSteps entries must be non-empty strings.",
                        str(path),
                    )
                )

            tdd = task.get("tdd")
            if not isinstance(tdd, dict):
                findings.append(
                    finding_type(
                        policy_level,
                        f"Task {idx} schemaVersion>=2 requires 'tdd' object.",
                        str(path),
                    )
                )
            else:
                required = tdd.get("required")
                if not isinstance(required, bool):
                    findings.append(
                        finding_type(
                            policy_level,
                            f"Task {idx} tdd.required must be boolean.",
                            str(path),
                        )
                    )
                elif required:
                    failing_verify = tdd.get("failingVerify")
                    passing_verify = tdd.get("passingVerify")
                    if (
                        not isinstance(failing_verify, list)
                        or not failing_verify
                        or not all(isinstance(value, str) and value.strip() for value in failing_verify)
                    ):
                        findings.append(
                            finding_type(
                                policy_level,
                                f"Task {idx} tdd.required=true requires non-empty failingVerify[] commands.",
                                str(path),
                            )
                        )
                    if (
                        not isinstance(passing_verify, list)
                        or not passing_verify
                        or not all(isinstance(value, str) and value.strip() for value in passing_verify)
                    ):
                        findings.append(
                            finding_type(
                                policy_level,
                                f"Task {idx} tdd.required=true requires non-empty passingVerify[] commands.",
                                str(path),
                            )
                        )
                else:
                    reason = tdd.get("reason")
                    if not isinstance(reason, str) or not reason.strip():
                        findings.append(
                            finding_type(
                                policy_level,
                                f"Task {idx} tdd.required=false requires non-empty tdd.reason.",
                                str(path),
                            )
                        )
                    elif contains_rationalization(reason):
                        findings.append(
                            finding_type(
                                policy_level,
                                f"Task {idx} tdd.reason appears rationalized; provide a concrete non-rationalized exemption reason.",
                                str(path),
                            )
                        )

        if schema_version >= 3 and operating_principles_level != "off":
            contract_level = policy_level_to_finding(operating_principles_level)
            context_links = task.get("contextLinks")
            if not isinstance(context_links, list) or not context_links:
                findings.append(
                    finding_type(
                        contract_level,
                        f"Task {idx} schemaVersion>=3 requires non-empty 'contextLinks' array tracing back to CONTEXT.json constraints or decisions.",
                        str(path),
                    )
                )
            elif not all(isinstance(link, str) and link.strip() for link in context_links):
                findings.append(
                    finding_type(
                        contract_level,
                        f"Task {idx} contextLinks entries must be non-empty strings.",
                        str(path),
                    )
                )

            micro_steps = task.get("microSteps")
            tdd = task.get("tdd")
            if isinstance(tdd, dict) and tdd.get("required") is True:
                scenario_texts: list[str] = []
                if isinstance(micro_steps, list):
                    scenario_texts.extend(step for step in micro_steps if isinstance(step, str) and step.strip())
                failing_verify = tdd.get("failingVerify")
                if isinstance(failing_verify, list):
                    scenario_texts.extend(cmd for cmd in failing_verify if isinstance(cmd, str) and cmd.strip())
                has_failure_scenario = any(_FAILURE_SCENARIO_RE.search(text) for text in scenario_texts)
                if not has_failure_scenario:
                    findings.append(
                        finding_type(
                            contract_level,
                            f"Task {idx} schemaVersion>=3 should name at least one explicit error-path scenario in microSteps[] or failingVerify[].",
                            str(path),
                        )
                    )

    if tasks:
        last_idx = len(tasks)
        last_task = tasks[-1]
        if isinstance(last_task, dict):
            last_deletions = last_task.get("deletions")
            if isinstance(last_deletions, list) and last_deletions:
                findings.append(
                    finding_type(
                        "WARN",
                        f"Task {last_idx} has `deletions` but is the last task in the plan — no subsequent task to receive auto-expanded caller cleanup scope.",
                        str(path),
                    )
                )
