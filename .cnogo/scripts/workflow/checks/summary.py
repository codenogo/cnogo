"""Summary contract generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def load_memory_task_issues(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    normalize_plan_number: Callable[[Any], str],
) -> list[Any]:
    normalized = normalize_plan_number(plan_number)
    try:
        import sys

        sys.path.insert(0, str(root))
        from scripts.memory import is_initialized, list_issues

        if not is_initialized(root):
            return []
        issues = list_issues(issue_type="task", feature_slug=feature, limit=1000, root=root)
        return [
            issue
            for issue in issues
            if normalize_plan_number(getattr(issue, "plan_number", "")) == normalized
        ]
    except Exception:
        return []


def task_outputs(issue: Any) -> dict[str, Any]:
    metadata = getattr(issue, "metadata", {})
    if not isinstance(metadata, dict):
        return {}
    outputs = metadata.get("outputs")
    return outputs if isinstance(outputs, dict) else {}


def task_verification_payload(issue: Any) -> dict[str, Any] | None:
    outputs = task_outputs(issue)
    verification = outputs.get("verification") or outputs.get("verificationEvidence")
    return verification if isinstance(verification, dict) else None


def build_task_verification_entries(
    root: Path,
    feature: str,
    plan_number: str,
    plan_path: Path,
    *,
    normalize_plan_number: Callable[[Any], str],
    load_memory_task_issues_fn: Callable[[Path, str, str], list[Any]],
) -> tuple[list[dict[str, Any]], str]:
    try:
        import sys

        sys.path.insert(0, str(root))
        from scripts.memory.bridge import plan_to_task_descriptions
    except Exception as exc:
        raise RuntimeError(f"Failed to load bridge helpers for summary generation: {exc}") from exc

    taskdescs = plan_to_task_descriptions(plan_path, root, ensure_memory_issues=False)
    issues = load_memory_task_issues_fn(root, feature, plan_number)
    issues_by_id = {getattr(issue, "id", ""): issue for issue in issues if getattr(issue, "id", "")}
    issues_by_title: dict[str, list[Any]] = {}
    for issue in issues:
        title = str(getattr(issue, "title", "") or "").strip()
        if title:
            issues_by_title.setdefault(title, []).append(issue)

    entries: list[dict[str, Any]] = []
    evidence_sources: set[str] = set()

    for task in taskdescs:
        title = str(task.get("title") or f"Task {task.get('plan_task_index', '?')}").strip()
        issue = None
        task_id = str(task.get("task_id") or "").strip()
        if task_id and task_id in issues_by_id:
            issue = issues_by_id.pop(task_id)
            bucket = issues_by_title.get(title) or []
            if issue in bucket:
                bucket.remove(issue)
        else:
            bucket = issues_by_title.get(title) or []
            if bucket:
                issue = bucket.pop(0)

        verification = task_verification_payload(issue) if issue is not None else None
        commands = task.get("commands", {}).get("verify", [])
        if isinstance(verification, dict):
            raw_commands = verification.get("commands")
            if isinstance(raw_commands, list) and raw_commands:
                commands = [str(cmd).strip() for cmd in raw_commands if isinstance(cmd, str) and cmd.strip()]
        timestamp = ""
        if isinstance(verification, dict):
            raw_timestamp = verification.get("timestamp")
            if isinstance(raw_timestamp, str) and raw_timestamp.strip():
                timestamp = raw_timestamp.strip()
        if not timestamp and issue is not None:
            raw_updated = getattr(issue, "updated_at", "")
            if isinstance(raw_updated, str) and raw_updated.strip():
                timestamp = raw_updated.strip()

        if isinstance(verification, dict):
            source = "task-evidence"
        elif issue is not None:
            source = "memory"
        else:
            source = "plan-contract"
        evidence_sources.add(source)

        issue_state = str(getattr(issue, "state", "") or "").strip()
        issue_status = str(getattr(issue, "status", "") or "").strip()
        if issue is not None and issue_state not in {"", "done_by_worker", "verified", "closed", "ready_to_close"} and issue_status != "closed":
            result = "pending"
        else:
            result = "pass"

        entry = {
            "scope": "task",
            "name": title,
            "result": result,
            "commands": commands if isinstance(commands, list) else [],
            "source": source,
        }
        if timestamp:
            entry["timestamp"] = timestamp
        if task_id:
            entry["taskId"] = task_id
        entries.append(entry)

    if not evidence_sources:
        return entries, "plan-contract"
    if len(evidence_sources) == 1:
        return entries, next(iter(evidence_sources))
    return entries, "mixed"


def build_plan_verification_entries(plan: dict[str, Any]) -> list[dict[str, Any]]:
    plan_verify = plan.get("planVerify")
    commands = [
        str(cmd).strip()
        for cmd in plan_verify
        if isinstance(cmd, str) and cmd.strip()
    ] if isinstance(plan_verify, list) else []
    if not commands:
        return []
    return [
        {
            "scope": "plan",
            "name": "planVerify",
            "result": "pass",
            "commands": commands,
            "source": "plan-contract",
        }
    ]


def build_summary_changes(changed_files: list[str], plan: dict[str, Any]) -> list[dict[str, str]]:
    task_file_map: dict[str, list[str]] = {}
    tasks = plan.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            title = str(task.get("name") or "").strip()
            files = task.get("files")
            if not title or not isinstance(files, list):
                continue
            for file_path in files:
                if isinstance(file_path, str) and file_path.strip():
                    task_file_map.setdefault(file_path.strip(), []).append(title)

    changes: list[dict[str, str]] = []
    for file_path in changed_files:
        owners = sorted(set(task_file_map.get(file_path, [])))
        change = "; ".join(owners) if owners else "Updated during plan execution."
        changes.append({"file": file_path, "change": change})
    return changes


def filter_summary_changed_files(changed_files: list[str], plan: dict[str, Any]) -> list[str]:
    """Limit SUMMARY changes to files explicitly owned by the plan contract."""
    planned_files: set[str] = set()
    tasks = plan.get("tasks")
    if isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            files = task.get("files")
            if not isinstance(files, list):
                continue
            for file_path in files:
                if isinstance(file_path, str) and file_path.strip():
                    planned_files.add(file_path.strip())
    if not planned_files:
        return changed_files
    return [file_path for file_path in changed_files if file_path in planned_files]


def resolve_summary_outcome(
    requested: str,
    *,
    changed_files: list[str],
    commit: dict[str, str],
    verification: list[dict[str, Any]],
) -> str:
    if requested in {"complete", "partial", "failed"}:
        return requested
    if any(entry.get("result") == "fail" for entry in verification if isinstance(entry, dict)):
        return "failed"
    if any(entry.get("result") == "pending" for entry in verification if isinstance(entry, dict)):
        return "partial"
    if not changed_files and not commit.get("hash"):
        return "partial"
    return "complete"


def write_summary(
    root: Path,
    feature: str,
    plan_number: str,
    *,
    outcome: str = "auto",
    notes: list[str] | None = None,
    normalize_plan_number: Callable[[Any], str],
    load_plan_contract: Callable[[Path, str, str], tuple[Path, dict[str, Any]]],
    summary_changed_files: Callable[[Path], tuple[list[str], str]],
    head_commit_metadata: Callable[[Path], dict[str, str]],
    load_memory_task_issues_fn: Callable[[Path, str, str], list[Any]],
    relative_display_path: Callable[[Path, Path], str],
    now_iso: Callable[[], str],
    write_json: Callable[[Path, dict[str, Any]], None],
    write_text: Callable[[Path, str], None],
    render_summary: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    normalized_plan = normalize_plan_number(plan_number)
    plan_path, plan = load_plan_contract(root, feature, normalized_plan)
    timestamp = now_iso()
    changed_files, changed_files_source = summary_changed_files(root)
    changed_files = filter_summary_changed_files(changed_files, plan)
    commit = head_commit_metadata(root)
    task_entries, task_evidence_source = build_task_verification_entries(
        root,
        feature,
        normalized_plan,
        plan_path,
        normalize_plan_number=normalize_plan_number,
        load_memory_task_issues_fn=load_memory_task_issues_fn,
    )
    plan_entries = build_plan_verification_entries(plan)
    verification = task_entries + plan_entries
    notes_list = [
        str(note).strip()
        for note in (notes or [])
        if isinstance(note, str) and note.strip()
    ]
    contract = {
        "schemaVersion": 2,
        "feature": feature,
        "planNumber": normalized_plan,
        "outcome": resolve_summary_outcome(
            outcome,
            changed_files=changed_files,
            commit=commit,
            verification=verification,
        ),
        "changes": build_summary_changes(changed_files, plan),
        "verification": verification,
        "commit": commit,
        "generatedFrom": {
            "kind": "workflow_checks.summarize",
            "planPath": relative_display_path(plan_path, root),
            "changedFilesSource": changed_files_source,
            "taskEvidenceSource": task_evidence_source,
            "generatedAt": timestamp,
        },
        "notes": notes_list,
        "timestamp": timestamp,
    }

    feature_dir = root / "docs" / "planning" / "work" / "features" / feature
    summary_json = feature_dir / f"{normalized_plan}-SUMMARY.json"
    summary_md = feature_dir / f"{normalized_plan}-SUMMARY.md"
    write_json(summary_json, contract)
    write_text(summary_md, render_summary(contract))
    return contract
