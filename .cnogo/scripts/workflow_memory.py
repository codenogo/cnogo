#!/usr/bin/env python3
"""CLI wrapper for the cnogo memory engine.

Usage:
    python3 .cnogo/scripts/workflow_memory.py <command> [options]

Commands:
    init                Initialize memory engine in .cnogo/
    create              Create a new issue
    show <id>           Show issue details
    update <id>         Update issue fields
    claim <id>          Claim an issue
    release <id>        Release an in-progress issue
    close <id>          Close an issue
    report-done <id>    Worker reports task done
    takeover <id>       Leader reassigns a stalled task
    stalled             List stale in-progress tasks
    verify-close <id>   Leader verifies and closes a task
    reopen <id>         Reopen a closed issue
    ready               List ready (unblocked) issues
    list                List issues with filters
    stats               Show aggregate statistics
    dep-add             Add a dependency
    dep-remove          Remove a dependency
    blockers <id>       Show what blocks an issue
    blocks <id>         Show what an issue blocks
    export              Export to JSONL
    import              Import from JSONL
    sync                Export JSONL memory state (optionally stage it)
    prime               Generate context summary
    checkpoint          Generate compact objective/progress checkpoint
    history <id>        Show recent event history for an issue
    phase-get <feature> Get current workflow phase for feature
    phase-set <feature> Set workflow phase for feature
    plan-auto          Generate or reuse a deterministic plan for a ready feature
    run-create          Create or resume a durable delivery run
    run-list            List delivery runs across features
    run-show            Show a delivery run
    work-show           Show the feature-level Work Order
    work-list           List Work Orders across features
    work-sync           Rebuild Work Order rollups
    work-next           Show the next feature-level action
    lane-list           List feature lanes across the repo
    lane-show           Show one feature lane
    dispatch-ready      Lease ready features into feature lanes
    feedback-sync       Sync downstream feedback back into SHAPE.json
    initiative-show     Show an initiative rollup from SHAPE.json
    initiative-list     List initiatives with SHAPE.json artifacts
    initiative-current  Show initiative context for the current or specified feature
    run-watch           Inspect delivery-run health and next actions
    run-watch-status    Show recurring watch schedule status and patrol state
    run-watch-tick      Run the recurring watch patrol only when due (or when forced)
    run-watch-patrol    Refresh watch artifacts, archive a patrol snapshot, and show deltas
    run-watch-history   Show archived watch patrol snapshots
    run-attention       Show the persisted needs-attention queue
    scheduler-status    Show hybrid scheduler state
    scheduler-run-once  Run due scheduler jobs one time
    scheduler-start     Start the optional local scheduler supervisor
    scheduler-stop      Stop the optional local scheduler supervisor
    run-refresh         Refresh task frontier for a delivery run
    run-next            Show the next ready tasks for a delivery run
    run-task-begin      Claim memory ownership and mark a task in progress
    run-task-complete   Report memory completion and mark a task done
    run-task-fail       Mark a delivery-run task as failed
    run-task-set        Update a delivery-run task state
    run-task-prompt     Render a stable implementer prompt for one run task
    run-plan-verify     Record plan verification outcome for a delivery run
    run-review-ready    Finalize integration and mark a delivery run review-ready
    run-review-start    Start or resume review state for a delivery run
    run-review-stage-set Update one review stage on a delivery run
    run-review-verdict  Set the final review verdict on a delivery run
    run-review-sync     Sync a delivery run from REVIEW.json
    run-ship-start      Start ship state for a delivery run
    run-ship-complete   Record successful ship completion on a delivery run
    run-ship-fail       Record a failed ship attempt on a delivery run
    run-ship-draft      Compute ship draft for a feature (commit surface, PR body, etc.)
    verify-import       Verify that a Python module (and optional symbols) import cleanly
    run-sync-session    Sync a delivery run from worktree-session state
    graph <feature>     Show dependency graph
    session-status      Show active worktree session status
    session-apply       Apply active worktree session outputs into the leader branch
    session-merge       Merge active worktree session branches
    session-cleanup     Cleanup active worktree session
    session-reconcile   Fix orphaned issues after compaction
    profile-suggest     Suggest the best workflow profile for a feature/plan
    profile-list        List available workflow profiles
    profile-init        Create a repo-local profile scaffold
    profile-stamp       Stamp a profile onto a plan and rerender it
    graph-index         Index codebase into context graph
    graph-query <name>  Search for symbols by name
    graph-impact <file> Analyze change impact (BFS blast radius)
    graph-context <id>  Show node neighborhood (callers, callees, etc.)
    graph-blast-radius  Compute blast-radius impact for changed files
    graph-search <q>    Full-text search over symbols (BM25 + porter stemming)
    graph-viz           Generate graph visualization (Mermaid or DOT)

No external dependencies. Python 3.9+ required.
"""

from __future__ import annotations

try:
    import _bootstrap  # noqa: F401
except ImportError:
    pass  # imported as module; caller manages sys.path

import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Ensure scripts/ is on the path when run directly
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))


def _ensure_graph_venv() -> None:
    """Re-exec under .cnogo/.venv/bin/python3 for graph commands."""
    root = _root()
    venv_python = root / ".cnogo" / ".venv" / "bin" / "python3"
    venv_dir = (root / ".cnogo" / ".venv").resolve()
    if Path(sys.prefix).resolve() == venv_dir:
        return  # already in this venv
    if not venv_python.exists():
        req_file = root / ".cnogo" / "requirements-graph.txt"
        print(
            "Graph dependencies not installed.\n"
            "Run:\n"
            f"  python3 -m venv {root / '.cnogo' / '.venv'}\n"
            f"  {venv_python} -m pip install -r {req_file}\n",
            file=sys.stderr,
        )
        raise SystemExit(1)
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)


from scripts.memory import (  # noqa: E402
    auto_plan_feature,
    begin_delivery_run_task,
    blocks,
    blockers,
    build_delivery_run_attention_queue,
    build_work_order,
    apply_session,
    checkpoint,
    claim,
    cleanup_session,
    close,
    complete_delivery_run_task,
    complete_delivery_run_ship,
    create,
    describe_feature_lane,
    delivery_run_watch_schedule_status,
    dispatch_ready_features,
    ensure_delivery_run,
    dep_add,
    dep_remove,
    fail_delivery_run_task,
    fail_delivery_run_ship,
    filter_delivery_run_attention_queue,
    export_jsonl,
    get_cost_summary,
    import_jsonl,
    init,
    is_initialized,
    history,
    latest_delivery_run,
    list_feature_lane_snapshots,
    load_delivery_run_attention_queue,
    load_delivery_run_watch_history,
    list_delivery_runs,
    list_feature_lanes,
    list_issues,
    list_work_orders,
    load_delivery_run,
    load_delivery_run_watch_report,
    load_feature_lane,
    load_work_order,
    load_session,
    next_delivery_run_action,
    next_work_order_action,
    plan_to_task_descriptions,
    prepare_delivery_run_review_ready,
    persist_delivery_run_watch_report,
    get_phase,
    merge_session,
    prime,
    ready,
    record_delivery_run_plan_verification,
    refresh_delivery_run,
    reconcile_session,
    recommend_team_mode,
    generate_implement_prompt,
    record_cost_event,
    run_delivery_run_watch_tick,
    run_scheduler_once,
    release,
    reopen,
    report_done,
    scheduler_status,
    set_delivery_run_review_verdict,
    start_scheduler_supervisor,
    sync_delivery_run_integration,
    sync_delivery_run_review,
    sync_delivery_run_with_session,
    show,
    show_graph,
    stalled_tasks,
    start_delivery_run_ship,
    start_delivery_run_review,
    stats,
    set_phase,
    summarize_delivery_run,
    sync,
    sync_all_work_orders,
    sync_shape_feedback,
    sync_work_order,
    takeover_task,
    stop_scheduler_supervisor,
    update,
    update_delivery_run_review_stage,
    update_delivery_task_status,
    verify_and_close,
    watch_delivery_runs,
)
from scripts.workflow.orchestration.initiative_rollup import (
    build_initiative_rollup,
    current_initiative_rollup,
    list_initiatives,
)
from scripts.workflow.orchestration.ship_draft import build_ship_draft
from scripts.workflow.orchestration import (
    DELIVERY_REVIEW_STAGE_STATUSES,
    DELIVERY_REVIEW_STAGES,
    DELIVERY_REVIEW_VERDICTS,
    SCHEDULER_JOB_NAMES,
    scheduler_worker_loop,
    DELIVERY_TASK_STATUSES,
)
from scripts.workflow.shared.config import load_workflow_config, scheduler_settings_cfg, watch_settings_cfg
from scripts.workflow.shared.profiles import (
    load_profile_catalog,
    is_profile_name,
    profile_auto_spawn_configured_reviewers,
    profile_name_from_plan,
    profile_required_reviewers,
    resolve_profile,
    scaffold_profile_contract,
    suggest_profile,
)
from scripts.workflow.shared.plans import normalize_plan_number


def _root() -> Path:
    """Find repo root by walking up from cwd looking for .git."""
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".git").exists():
            return p
    return cwd


def _git_branch(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _plan_contract_path(root: Path, feature: str, plan_number: str) -> Path:
    normalized = normalize_plan_number(plan_number)
    return root / "docs" / "planning" / "work" / "features" / feature / f"{normalized}-PLAN.json"


def _context_contract_path(root: Path, feature: str) -> Path:
    return root / "docs" / "planning" / "work" / "features" / feature / "CONTEXT.json"


def _load_json_contract(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_run(root: Path, feature: str, run_id: str | None):
    if run_id:
        return load_delivery_run(feature, run_id, root=root)
    return latest_delivery_run(feature, root=root)


def _run_plan_path(root: Path, run) -> Path:
    raw_path = str(getattr(run, "plan_path", "") or "").strip()
    if not raw_path:
        raise FileNotFoundError(f"Delivery Run {run.run_id} is missing planPath.")
    plan_path = Path(raw_path)
    if not plan_path.is_absolute():
        plan_path = root / plan_path
    return plan_path


def _resolve_task_description_for_run(root: Path, run, task_index: int) -> dict[str, object]:
    plan_path = _run_plan_path(root, run)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan contract not found: {plan_path}")
    taskdescs = plan_to_task_descriptions(
        plan_path,
        root,
        profile=run.profile if isinstance(getattr(run, "profile", None), dict) else None,
    )
    for taskdesc in taskdescs:
        if int(taskdesc.get("plan_task_index", -1)) == task_index:
            return taskdesc
    raise ValueError(f"Unknown task index {task_index} for plan {run.plan_number}.")


def _plan_verify_commands_for_run(root: Path, run) -> list[str]:
    plan_path = _run_plan_path(root, run)
    contract = _load_json_contract(plan_path) or {}
    raw = contract.get("planVerify")
    if not isinstance(raw, list):
        return []
    return [str(command).strip() for command in raw if isinstance(command, str) and str(command).strip()]


def _print_run(run) -> None:
    status_counts: dict[str, int] = {}
    for task in run.tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
    print(f"Run: {run.run_id}")
    print(f"Feature: {run.feature}")
    print(f"Plan: {run.plan_number}")
    print(f"Mode: {run.mode}")
    print(f"Status: {run.status}")
    profile = run.profile if isinstance(getattr(run, "profile", None), dict) else {}
    if profile:
        profile_name = str(profile.get("name", "")).strip() or "unknown"
        profile_version = str(profile.get("version", "")).strip()
        version_suffix = f" v{profile_version}" if profile_version else ""
        print(f"Profile: {profile_name}{version_suffix}")
    if run.branch:
        print(f"Branch: {run.branch}")
    integration = run.integration if isinstance(getattr(run, "integration", None), dict) else {}
    review = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    if integration:
        print(
            "Integration: "
            f"{integration.get('status', 'pending')} "
            f"(merged={len(integration.get('mergedTaskIndices', []))}, "
            f"awaiting_merge={len(integration.get('awaitingMergeTaskIndices', []))})"
        )
        if integration.get("conflictTaskIndex") is not None or integration.get("conflictFiles"):
            print(
                "Integration conflicts: "
                f"task={integration.get('conflictTaskIndex')} "
                f"files={integration.get('conflictFiles', [])}"
            )
    if review:
        print(
            "Review readiness: "
            f"{review.get('status', 'pending')} "
            f"(plan_verify={review.get('planVerifyPassed')})"
        )
    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    if review_state:
        print(
            "Review: "
            f"{review_state.get('status', 'pending')} "
            f"(automated={review_state.get('automatedVerdict', 'pending')}, "
            f"final={review_state.get('finalVerdict', 'pending')})"
        )
        reviewers = review_state.get("reviewers", [])
        if isinstance(reviewers, list) and reviewers:
            print(f"Reviewers: {reviewers}")
        for stage in review_state.get("stages", []) if isinstance(review_state.get("stages"), list) else []:
            if not isinstance(stage, dict):
                continue
            print(
                f"  - {stage.get('stage')}: {stage.get('status', 'pending')} "
                f"(findings={len(stage.get('findings', [])) if isinstance(stage.get('findings'), list) else 0}, "
                f"evidence={len(stage.get('evidence', [])) if isinstance(stage.get('evidence'), list) else 0})"
            )
    ship_state = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    if ship_state:
        print(
            "Ship: "
            f"{ship_state.get('status', 'pending')} "
            f"(attempts={ship_state.get('attempts', 0)}, "
            f"commit={ship_state.get('commit', '') or 'n/a'})"
        )
        if ship_state.get("prUrl"):
            print(f"Ship PR: {ship_state.get('prUrl')}")
    if status_counts:
        print(f"Task status counts: {status_counts}")
    for task in run.tasks:
        suffix = f" @{task.assignee}" if task.assignee else ""
        print(f"- Task {task.task_index}: {task.title} [{task.status}{suffix}]")


def _print_run_list(entries: list[dict]) -> None:
    if not entries:
        print("No delivery runs found")
        return
    for entry in entries:
        updated = entry.get("minutesSinceUpdate")
        updated_label = f"{updated}m" if updated is not None else "n/a"
        print(
            f"{entry['feature']} {entry['runId']} "
            f"[{entry['status']}/{entry['mode']}] "
            f"profile={entry.get('profileName', 'unknown')} "
            f"integration={entry['integrationStatus']} "
            f"review={entry['reviewReadiness']} "
            f"review_state={entry.get('reviewStatus', 'pending')} "
            f"ship={entry.get('shipStatus', 'pending')} "
            f"updated={updated_label}"
        )
        if entry.get("workOrderId"):
            print(f"  work-order={entry['workOrderId']}")
        if entry.get("attentionKinds"):
            print(
                "  attention="
                f"{entry.get('attentionMaxSeverity', 'warn')}:"
                + ",".join(str(kind) for kind in entry.get("attentionKinds", []))
            )
            if entry.get("attentionNextAction"):
                print(f"  next={entry['attentionNextAction']}")


def _print_watch_report(report: dict) -> None:
    summary = report.get("summary", {})
    print(
        f"Delivery Runs: {summary.get('totalRuns', 0)} "
        f"status_counts={summary.get('statusCounts', {})} "
        f"work_orders={summary.get('totalWorkOrders', 0)}"
    )
    findings = report.get("findings", [])
    if not findings:
        print("No watch findings")
    else:
        print("Findings:")
        for finding in findings:
            location = ""
            if finding.get("feature") and finding.get("runId"):
                location = f"{finding['feature']}/{finding['runId']} "
            print(
                f"- {finding.get('severity', 'warn').upper()} "
                f"{location}{finding.get('kind')}: {finding.get('message')}"
            )
            print(f"  next: {finding.get('nextAction')}")
    paths = report.get("paths", {})
    if isinstance(paths, dict):
        if paths.get("report"):
            print(f"Report: {paths['report']}")
        if paths.get("attention"):
            print(f"Attention: {paths['attention']}")


def _print_work_order(order: dict) -> None:
    print(f"Work Order: {order.get('workOrderId', '')}")
    print(f"Feature: {order.get('feature', '')}")
    print(f"Status: {order.get('status', '')}")
    print(f"Phase: {order.get('currentPhase', '')}")
    if order.get("queuePosition"):
        print(f"Queue Position: {order['queuePosition']}")
    lane = order.get("lane", {})
    if isinstance(lane, dict) and lane.get("laneId"):
        print(
            "Lane: "
            f"{lane.get('laneId', '')} "
            f"(status={lane.get('status', '')}, owner={lane.get('leaseOwner', '') or 'n/a'})"
        )
        if lane.get("worktreePath"):
            print(f"Lane Worktree: {lane['worktreePath']}")
    profile = order.get("profile", {})
    if isinstance(profile, dict) and profile.get("name"):
        version = str(profile.get("version", "")).strip()
        suffix = f" v{version}" if version else ""
        print(f"Profile: {profile.get('name')}{suffix}")
    if order.get("currentRunId"):
        print(f"Current Run: {order['currentRunId']}")
    attention = order.get("attentionSummary", {})
    if isinstance(attention, dict):
        print(
            "Attention: "
            f"items={attention.get('itemCount', 0)} "
            f"highest={attention.get('highestSeverity', 'ok')}"
        )
    review = order.get("reviewSummary", {})
    if isinstance(review, dict):
        print(
            "Review: "
            f"{review.get('status', 'pending')} "
            f"(final={review.get('finalVerdict', 'pending')})"
        )
    ship = order.get("shipSummary", {})
    if isinstance(ship, dict):
        print(
            "Ship: "
            f"{ship.get('status', 'pending')} "
            f"(attempts={ship.get('attempts', 0)})"
        )
    memory_sync = order.get("memorySync", {})
    if isinstance(memory_sync, dict) and memory_sync.get("status"):
        status = str(memory_sync.get("status", "unknown"))
        if status == "ok":
            print(
                "Memory Sync: "
                f"ok obs={memory_sync.get('observations', 0)} "
                f"contradictions={memory_sync.get('contradictions', 0)} "
                f"cards={memory_sync.get('cards', 0)}"
            )
        elif status == "error":
            print(f"Memory Sync: error ({memory_sync.get('error', 'unknown error')})")
        else:
            print(f"Memory Sync: {status} ({memory_sync.get('reason', 'not run')})")
    automation_state = order.get("automationState", {})
    if isinstance(automation_state, dict) and automation_state.get("state"):
        print(
            "Automation State: "
            f"{automation_state.get('state')} "
            f"(owner={automation_state.get('owner', 'system')})"
        )
        if automation_state.get("reason"):
            print(f"Automation Reason: {automation_state['reason']}")
    next_action = order.get("nextAction", {})
    if isinstance(next_action, dict) and next_action.get("summary"):
        print(f"Next: {next_action['summary']}")
        if next_action.get("command"):
            print(f"Command: {next_action['command']}")
        automation = next_action.get("automation", {})
        if isinstance(automation, dict) and automation.get("state"):
            print(f"Automation: {automation.get('state')} ({automation.get('reason', '')})")


def _print_work_order_list(entries: list[dict]) -> None:
    if not entries:
        print("No work orders found")
        return
    for entry in entries:
        print(
            f"{entry.get('workOrderId', '')} "
            f"[{entry.get('status', '')}/{entry.get('currentPhase', '')}] "
            f"profile={entry.get('profile', {}).get('name', 'unknown') if isinstance(entry.get('profile'), dict) else 'unknown'} "
            f"run={entry.get('currentRunId', '') or 'n/a'} "
            f"queue={entry.get('queuePosition', 0) or '-'} "
            f"lane={entry.get('lane', {}).get('status', 'n/a') if isinstance(entry.get('lane'), dict) else 'n/a'}"
        )
        attention = entry.get("attentionSummary", {})
        if isinstance(attention, dict) and attention.get("itemCount", 0):
            print(
                "  attention="
                f"{attention.get('highestSeverity', 'warn')}:"
                f"{attention.get('itemCount', 0)}"
            )
        memory_sync = entry.get("memorySync", {})
        if isinstance(memory_sync, dict) and memory_sync.get("status") == "error":
            print(f"  memory=error:{memory_sync.get('error', 'unknown error')}")
        automation_state = entry.get("automationState", {})
        if isinstance(automation_state, dict) and automation_state.get("state"):
            print(f"  automation={automation_state['state']}")
        next_action = entry.get("nextAction", {})
        if isinstance(next_action, dict) and next_action.get("command"):
            print(f"  next={next_action['command']}")


def _print_lane(payload: dict) -> None:
    print(f"Lane: {payload.get('laneId', '')}")
    print(f"Feature: {payload.get('feature', '')}")
    print(f"Status: {payload.get('status', '')}")
    print(f"Work Order: {payload.get('workOrderId', '')}")
    print(f"Owner: {payload.get('leaseOwner', '') or 'n/a'}")
    if payload.get("branch"):
        print(f"Branch: {payload['branch']}")
    if payload.get("worktreePath"):
        print(f"Worktree: {payload['worktreePath']}")
    if payload.get("currentPlanNumber"):
        print(f"Current Plan: {payload['currentPlanNumber']}")
    if payload.get("currentRunId"):
        print(f"Current Run: {payload['currentRunId']}")
    if payload.get("sessionPath"):
        print(f"Session: {payload['sessionPath']}")
    health = payload.get("health", {})
    if isinstance(health, dict):
        print(
            "Health: "
            f"stale={health.get('stale', False)} "
            f"reclaimable={health.get('reclaimable', False)} "
            f"reason={health.get('reason', '') or 'ok'}"
        )
        if health.get("heartbeatAt"):
            print(f"Heartbeat: {health['heartbeatAt']}")
        if health.get("leaseExpiresAt"):
            print(f"Lease Expires: {health['leaseExpiresAt']}")


def _print_lane_list(entries: list[dict]) -> None:
    if not entries:
        print("No feature lanes found")
        return
    for entry in entries:
        print(
            f"{entry.get('feature', '')} "
            f"[{entry.get('status', '')}] "
            f"owner={entry.get('leaseOwner', '') or 'n/a'} "
            f"stale={entry.get('health', {}).get('stale', False) if isinstance(entry.get('health'), dict) else False} "
            f"branch={entry.get('branch', '') or 'n/a'} "
            f"worktree={entry.get('worktreePath', '') or 'n/a'}"
        )


def _print_watch_schedule(payload: dict) -> None:
    print(
        "Watch schedule: "
        f"enabled={payload.get('enabled')} "
        f"due={payload.get('due')} "
        f"interval={payload.get('patrolIntervalMinutes')}m"
    )
    if payload.get("reason"):
        print(f"Reason: {payload['reason']}")
    if payload.get("lastPatrolAt"):
        print(f"Last patrol: {payload['lastPatrolAt']}")
    if payload.get("nextPatrolAt"):
        print(f"Next patrol: {payload['nextPatrolAt']}")
    if payload.get("lastResult"):
        print(f"Last result: {payload['lastResult']}")
    summary = payload.get("lastAttentionSummary", {})
    if isinstance(summary, dict):
        print(
            "Attention summary: "
            f"total={summary.get('totalItems', 0)} "
            f"highest={summary.get('highestSeverity', 'ok')}"
        )
    if payload.get("statePath"):
        print(f"State: {payload['statePath']}")
    if payload.get("reportPath"):
        print(f"Report: {payload['reportPath']}")
    if payload.get("attentionPath"):
        print(f"Attention: {payload['attentionPath']}")


def _print_attention_queue(queue: dict) -> None:
    summary = queue.get("summary", {})
    print(
        f"Attention Queue: {summary.get('totalItems', 0)} "
        f"severity_counts={summary.get('severityCounts', {})} "
        f"matched={summary.get('matchedItems', summary.get('totalItems', 0))}"
    )
    items = queue.get("items", [])
    if not items:
        print("No attention items")
        return
    for item in items:
        location = ""
        if item.get("feature") and item.get("runId"):
            location = f"{item['feature']}/{item['runId']} "
        stale = item.get("minutesStale")
        stale_label = f" ({stale:.1f}m stale)" if isinstance(stale, (int, float)) else ""
        print(
            f"- {item.get('severity', 'warn').upper()} "
            f"{location}{item.get('kind')}{stale_label}: {item.get('message')}"
        )
        print(f"  next: {item.get('nextAction')}")


def _print_profile_suggestion(suggestion: dict) -> None:
    confidence = suggestion.get("confidence")
    confidence_label = f"{float(confidence):.2f}" if isinstance(confidence, (int, float)) else "n/a"
    print(f"Suggested profile: {suggestion.get('name', 'feature-delivery')}")
    print(f"Confidence: {confidence_label}")
    if suggestion.get("reason"):
        print(f"Reason: {suggestion['reason']}")
    matched_terms = suggestion.get("matchedTerms", [])
    if isinstance(matched_terms, list) and matched_terms:
        print("Matched terms: " + ", ".join(str(term) for term in matched_terms))


def _print_watch_patrol(payload: dict) -> None:
    report = payload.get("report", {})
    delta = payload.get("delta", {})
    _print_watch_report(report if isinstance(report, dict) else {})
    summary = delta.get("summary", {}) if isinstance(delta, dict) else {}
    print(
        "Patrol delta: "
        f"new={summary.get('new', 0)} "
        f"resolved={summary.get('resolved', 0)} "
        f"ongoing={summary.get('ongoing', 0)}"
    )


def _print_watch_history(entries: list[dict]) -> None:
    if not entries:
        print("No watch history snapshots")
        return
    for entry in entries:
        attention = entry.get("attentionSummary", {})
        delta = entry.get("deltaSummary", {})
        print(
            f"{entry.get('checkedAt', 'unknown')} "
            f"attention={attention.get('totalItems', 0)} "
            f"new={delta.get('new', 0)} "
            f"resolved={delta.get('resolved', 0)} "
            f"path={entry.get('path', '')}"
        )


def _print_profile_catalog(entries: list[dict]) -> None:
    if not entries:
        print("No profiles available")
        return
    for entry in entries:
        print(
            f"- {entry.get('name', 'unknown')} "
            f"(v{entry.get('version', '1.0.0')}, source={entry.get('source', 'builtin')})"
        )
        if entry.get("description"):
            print(f"  {entry['description']}")


def _print_run_next(payload: dict) -> None:
    print(
        f"Run: {payload.get('feature', '')}/{payload.get('runId', '')} "
        f"[{payload.get('status', '')}/{payload.get('mode', '')}]"
    )
    next_action = payload.get("nextAction", {})
    if isinstance(next_action, dict) and next_action.get("kind"):
        print(f"Next action: {next_action.get('kind')}")
        if next_action.get("reason"):
            print(f"Reason: {next_action.get('reason')}")
        if next_action.get("command"):
            print(f"Command: {next_action.get('command')}")
    ready_tasks = payload.get("readyTasks", [])
    if not isinstance(ready_tasks, list) or not ready_tasks:
        print("No ready tasks")
        return
    for task in ready_tasks:
        if not isinstance(task, dict):
            continue
        print(f"- Task {task.get('taskIndex')}: {task.get('title')} [{task.get('status')}]")
        if task.get("memoryId"):
            print(f"  memory: {task['memoryId']}")
        if task.get("cwd"):
            print(f"  cwd: {task['cwd']}")
        begin_cmd = task.get("beginCommand")
        if begin_cmd:
            print(f"  begin: {begin_cmd}")


def _print_scheduler_status(payload: dict) -> None:
    print(
        "Scheduler: "
        f"enabled={payload.get('enabled')} "
        f"mode={payload.get('mode')} "
        f"due={payload.get('due')} "
        f"interval={payload.get('tickIntervalMinutes')}m"
    )
    if payload.get("reason"):
        print(f"Reason: {payload['reason']}")
    if payload.get("supervisorActive"):
        print(f"Supervisor PID: {payload.get('workerPid')}")
    if payload.get("lastRunAt"):
        print(f"Last run: {payload['lastRunAt']}")
    if payload.get("nextRunAt"):
        print(f"Next run: {payload['nextRunAt']}")
    if payload.get("lastJobs"):
        print("Last jobs: " + ", ".join(str(job) for job in payload["lastJobs"]))


def _print_scheduler_run(payload: dict) -> None:
    _print_scheduler_status(payload.get("status", {}))
    if payload.get("executed"):
        print("Executed jobs:")
        for name, result in payload.get("jobs", {}).items():
            if name == "work_order_sync":
                print(f"- {name}: {result.get('count', 0)} work orders synced")
            elif name == "watch_patrol":
                attention = result.get("attention", {}) if isinstance(result, dict) else {}
                items = attention.get("items", []) if isinstance(attention, dict) else []
                print(f"- {name}: {len(items) if isinstance(items, list) else 0} attention items")
            else:
                print(f"- {name}")
    elif payload.get("reason"):
        print(f"Skipped: {payload['reason']}")


def _find_run_task(run, task_index: int):
    return next((task for task in run.tasks if task.task_index == task_index), None)


def _ready_run_tasks(run) -> list:
    return [task for task in run.tasks if getattr(task, "status", "") == "ready"]


def _print_issue(issue, *, verbose: bool = False) -> None:
    """Print an issue in human-readable format."""
    status = issue.status
    assignee = f" @{issue.assignee}" if issue.assignee else ""
    prio = f"P{issue.priority}"
    print(f"  [{prio}] {issue.id}  {issue.title}  ({status}{assignee})")
    if verbose:
        if issue.description:
            print(f"        desc: {issue.description[:120]}")
        if issue.feature_slug:
            print(f"        feature: {issue.feature_slug}")
        if getattr(issue, "phase", ""):
            print(f"        phase: {issue.phase}")
        if issue.labels:
            print(f"        labels: {', '.join(issue.labels)}")
        if issue.close_reason:
            print(f"        reason: {issue.close_reason}")


def _print_json(data) -> None:
    """Print as formatted JSON."""
    print(json.dumps(data, indent=2, default=str, sort_keys=True))


def _parse_metadata(raw: str | None) -> dict | None:
    """Parse --metadata JSON and enforce object shape."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid --metadata JSON: {e.msg}") from e
    if not isinstance(parsed, dict):
        raise ValueError("Invalid --metadata JSON: expected an object")
    return parsed


def cmd_init(args: argparse.Namespace) -> int:
    root = _root()
    init(root)
    print(f"Memory engine initialized at {root / '.cnogo'}")
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    root = _root()
    labels = args.labels.split(",") if args.labels else None
    try:
        metadata = _parse_metadata(args.metadata)
        issue = create(
            args.title,
            issue_type=args.type,
            parent=args.parent,
            feature_slug=args.feature,
            plan_number=args.plan,
            priority=args.priority,
            labels=labels,
            description=args.description,
            metadata=metadata,
            actor=args.actor,
            root=root,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(issue.to_dict())
    else:
        print(f"Created {issue.issue_type}: {issue.id}")
        _print_issue(issue, verbose=True)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    root = _root()
    issue = show(args.id, root=root)
    if not issue:
        print(f"Issue {args.id} not found", file=sys.stderr)
        return 1
    if args.json:
        _print_json(issue.to_dict())
    else:
        _print_issue(issue, verbose=True)
        if issue.deps:
            print("    depends on:")
            for d in issue.deps:
                print(f"      - {d.depends_on_id} ({d.dep_type})")
        if issue.blocks_issues:
            print(f"    blocks: {', '.join(issue.blocks_issues)}")
        if issue.recent_events:
            print("    recent events:")
            for e in issue.recent_events[:5]:
                print(f"      [{e.event_type}] {e.actor} at {e.created_at}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    root = _root()
    try:
        metadata = _parse_metadata(args.metadata)
        issue = update(
            args.id,
            title=args.title,
            description=args.description,
            priority=args.priority,
            metadata=metadata,
            comment=args.comment,
            actor=args.actor,
            root=root,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(f"Updated: {issue.id}")
    _print_issue(issue, verbose=True)
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    root = _root()
    try:
        issue = claim(args.id, actor=args.actor, root=root)
        print(f"Claimed: {issue.id} by {issue.assignee}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_release(args: argparse.Namespace) -> int:
    root = _root()
    try:
        issue = release(args.id, actor=args.actor, actor_role="leader", root=root)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(issue.to_dict())
    else:
        print(f"Released: {issue.id} (status={issue.status})")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    root = _root()
    try:
        issue = close(
            args.id, reason=args.reason, comment=args.comment,
            actor=args.actor, root=root,
        )
        print(f"Closed: {issue.id} ({issue.close_reason})")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_report_done(args: argparse.Namespace) -> int:
    root = _root()
    try:
        outputs = None
        if args.outputs:
            outputs = json.loads(args.outputs)
        issue = report_done(
            args.id, actor=args.actor, outputs=outputs, root=root,
        )
        print(f"Reported done: {issue.id} (state={issue.state})")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_takeover(args: argparse.Namespace) -> int:
    root = _root()
    try:
        payload = takeover_task(
            args.id,
            to_actor=args.to_actor,
            reason=args.reason,
            actor=args.actor,
            root=root,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(payload)
    else:
        print(
            "Takeover:"
            f" {payload['id']} {payload.get('from_actor', '')!r} -> {payload.get('to_actor', '')!r}"
            f" (attempt {payload.get('attempt')}/{payload.get('max_attempts')})"
        )
    return 0


def cmd_stalled(args: argparse.Namespace) -> int:
    root = _root()
    items = stalled_tasks(
        feature_slug=args.feature,
        stale_minutes=args.minutes,
        root=root,
    )
    if args.json:
        _print_json(items)
    elif not items:
        print("No stalled tasks.")
    else:
        print(f"Stalled tasks ({len(items)}):")
        for item in items:
            feature = item.get("feature") or "-"
            print(
                f"  {item['id']}  {item['title']}  "
                f"(stale={item['minutesStale']}m assignee={item.get('assignee') or '-'} feature={feature})"
            )
    return 0


def cmd_verify_close(args: argparse.Namespace) -> int:
    root = _root()
    try:
        issue = verify_and_close(
            args.id, reason=args.reason, actor=args.actor, root=root,
        )
        print(f"Verified and closed: {issue.id} (state={issue.state})")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_reopen(args: argparse.Namespace) -> int:
    root = _root()
    try:
        issue = reopen(args.id, actor=args.actor, root=root)
        print(f"Reopened: {issue.id}")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_ready(args: argparse.Namespace) -> int:
    root = _root()
    issues = ready(
        feature_slug=args.feature,
        label=args.label,
        limit=args.limit,
        root=root,
    )
    if args.json:
        _print_json([i.to_dict() for i in issues])
    elif not issues:
        print("No ready issues.")
    else:
        print(f"Ready issues ({len(issues)}):")
        for i in issues:
            _print_issue(i)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = _root()
    issues = list_issues(
        status=args.status,
        issue_type=args.type,
        feature_slug=args.feature,
        parent=args.parent,
        assignee=args.assignee,
        label=args.label,
        limit=args.limit,
        root=root,
    )
    if args.json:
        _print_json([i.to_dict() for i in issues])
    elif not issues:
        print("No issues found.")
    else:
        print(f"Issues ({len(issues)}):")
        for i in issues:
            _print_issue(i)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    root = _root()
    s = stats(root=root)
    if args.json:
        _print_json(s)
    else:
        print(f"Total: {s.get('total', 0)}")
        print(f"  Open: {s.get('open', 0)}")
        print(f"  In Progress: {s.get('in_progress', 0)}")
        print(f"  Closed: {s.get('closed', 0)}")
        print(f"  Ready: {s.get('ready', 0)}")
        print(f"  Blocked: {s.get('blocked', 0)}")
        by_type = s.get("by_type", {})
        if by_type:
            print("  By type:")
            for t, c in sorted(by_type.items()):
                print(f"    {t}: {c}")
        by_feature = s.get("by_feature", {})
        if by_feature:
            print("  By feature:")
            for f, c in sorted(by_feature.items()):
                print(f"    {f}: {c}")
    return 0


def cmd_dep_add(args: argparse.Namespace) -> int:
    root = _root()
    try:
        dep_add(
            args.issue, args.depends_on,
            dep_type=args.type, actor=args.actor, root=root,
        )
        print(f"Dependency added: {args.issue} -> {args.depends_on} ({args.type})")
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_dep_remove(args: argparse.Namespace) -> int:
    root = _root()
    dep_remove(args.issue, args.depends_on, actor=args.actor, root=root)
    print(f"Dependency removed: {args.issue} -> {args.depends_on}")
    return 0


def cmd_blockers(args: argparse.Namespace) -> int:
    root = _root()
    issues = blockers(args.id, root=root)
    if not issues:
        print(f"No blockers for {args.id}")
    else:
        print(f"Blockers for {args.id}:")
        for i in issues:
            _print_issue(i)
    return 0


def cmd_blocks(args: argparse.Namespace) -> int:
    root = _root()
    issues = blocks(args.id, root=root)
    if not issues:
        print(f"{args.id} blocks nothing")
    else:
        print(f"{args.id} blocks:")
        for i in issues:
            _print_issue(i)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    root = _root()
    path = export_jsonl(root)
    print(f"Exported to {path}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    root = _root()
    count = import_jsonl(root)
    print(f"Imported {count} issues")
    return 0


def cmd_sync_fn(args: argparse.Namespace) -> int:
    root = _root()
    path = sync(root, stage=args.stage)
    if args.stage:
        print(f"Synced: exported JSONL and staged for git ({path})")
    else:
        print(f"Synced: exported JSONL ({path})")
    return 0


def cmd_prime(args: argparse.Namespace) -> int:
    root = _root()
    feature = getattr(args, "feature", None) or None
    output = prime(feature=feature, limit=args.limit, verbose=args.verbose, root=root)
    print(output)
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    root = _root()
    output = checkpoint(
        feature_slug=args.feature,
        limit=args.limit,
        root=root,
    )
    print(output)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    root = _root()
    output = history(args.id, limit=args.limit, root=root)
    print(output)
    return 0


def cmd_phase_get(args: argparse.Namespace) -> int:
    root = _root()
    phase = get_phase(args.feature, root=root)
    if args.json:
        _print_json({"feature": args.feature, "phase": phase})
    else:
        print(f"{args.feature}: {phase}")
    return 0


def cmd_phase_set(args: argparse.Namespace) -> int:
    print(
        "[cnogo] Note: manual phase-set is deprecated. "
        "Phase now auto-advances from work order status on every work-sync.",
        file=sys.stderr,
    )
    root = _root()
    try:
        count = set_phase(args.feature, args.phase, root=root)
        sync_work_order(args.feature, root=root)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    if args.json:
        _print_json({"feature": args.feature, "phase": args.phase, "updated": count})
    else:
        print(f"Set phase for {args.feature}: {args.phase} ({count} issues updated)")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    root = _root()
    output = show_graph(args.feature, root=root)
    print(output)
    return 0


def cmd_session_status(args: argparse.Namespace) -> int:
    root = _root()
    session = load_session(root)
    linked_run = None
    if session and session.feature:
        if session.run_id:
            linked_run = load_delivery_run(session.feature, session.run_id, root=root)
        if linked_run is None:
            linked_run = latest_delivery_run(session.feature, root=root)
    if args.json:
        if not session:
            _print_json({"session": None})
            return 0
        payload = session.to_dict()
        payload["deliveryRun"] = linked_run.to_dict() if linked_run else None
        _print_json(payload)
        return 0
    if not session:
        print("No active worktree session")
        return 0
    total = len(session.worktrees)
    done = sum(1 for w in session.worktrees if w.status in {"completed", "merged", "cleaned"})
    print(f"Feature: {session.feature}")
    print(f"Plan: {session.plan_number}")
    print(f"Phase: {session.phase}")
    if session.run_id:
        if linked_run and linked_run.run_id == session.run_id:
            print(f"Delivery Run: {linked_run.run_id} [{linked_run.status}, {linked_run.mode}]")
        else:
            print(f"Delivery Run: {session.run_id} [missing]")
    elif linked_run:
        print(f"Delivery Run: {linked_run.run_id} [{linked_run.status}, {linked_run.mode}]")
    if linked_run:
        integration = linked_run.integration if isinstance(linked_run.integration, dict) else {}
        review = linked_run.review_readiness if isinstance(linked_run.review_readiness, dict) else {}
        review_state = linked_run.review if isinstance(getattr(linked_run, "review", None), dict) else {}
        if integration:
            print(
                "Integration: "
                f"{integration.get('status', 'pending')} "
                f"(merged={len(integration.get('mergedTaskIndices', []))}, "
                f"awaiting_merge={len(integration.get('awaitingMergeTaskIndices', []))})"
            )
        if review:
            print(
                "Review readiness: "
                f"{review.get('status', 'pending')} "
                f"(plan_verify={review.get('planVerifyPassed')})"
            )
        if review_state:
            print(
                "Review: "
                f"{review_state.get('status', 'pending')} "
                f"(automated={review_state.get('automatedVerdict', 'pending')}, "
                f"final={review_state.get('finalVerdict', 'pending')})"
            )
    print(f"Progress: {done}/{total}")
    for wt in session.worktrees:
        print(f"- Task {wt.task_index}: {wt.name} [{wt.status}]")
    return 0


def cmd_session_merge(args: argparse.Namespace) -> int:
    root = _root()
    session = load_session(root)
    if not session:
        payload = {"success": False, "error": "No active worktree session"}
        if args.json:
            _print_json(payload)
        else:
            print(payload["error"])
        return 1
    result = merge_session(session, root)
    updated_session = load_session(root) or session
    linked_run = None
    if session.feature:
        if session.run_id:
            linked_run = load_delivery_run(session.feature, session.run_id, root=root)
        if linked_run is None:
            linked_run = latest_delivery_run(session.feature, root=root)
    if linked_run is not None:
        linked_run = sync_delivery_run_with_session(linked_run, updated_session, root=root)
        linked_run = sync_delivery_run_integration(
            linked_run,
            session=updated_session,
            merge_result=result,
            root=root,
        )
    tiers = {}
    for wt in session.worktrees:
        if wt.task_index in result.merged_indices:
            tiers[str(wt.task_index)] = wt.resolved_tier or "unknown"
    payload = {
        "success": result.success,
        "merged": result.merged_indices,
        "conflictIndex": result.conflict_index,
        "conflictFiles": result.conflict_files,
        "error": "",
        "tiers": tiers,
    }
    if linked_run is not None:
        payload["deliveryRun"] = linked_run.to_dict()
    if args.json:
        _print_json(payload)
    else:
        if result.success:
            print(f"Merged tasks: {result.merged_indices}")
        else:
            print(f"Merge stopped at task {result.conflict_index}: {result.conflict_files}")
        tier_counts = {}
        for t in tiers.values():
            tier_counts[t] = tier_counts.get(t, 0) + 1
        if tier_counts:
            print(f"Resolution tiers: {tier_counts}")
        if linked_run is not None:
            print(
                "Delivery Run integration: "
                f"{linked_run.integration.get('status', 'pending')} "
                f"(merged={len(linked_run.integration.get('mergedTaskIndices', []))})"
            )
            print(
                "Delivery Run review readiness: "
                f"{linked_run.review_readiness.get('status', 'pending')} "
                f"(plan_verify={linked_run.review_readiness.get('planVerifyPassed')})"
            )
    return 0 if result.success else 1


def cmd_session_apply(args: argparse.Namespace) -> int:
    root = _root()
    session = load_session(root)
    if not session:
        payload = {"success": False, "error": "No active worktree session"}
        if args.json:
            _print_json(payload)
        else:
            print(payload["error"])
        return 1
    linked_run = None
    if session.feature:
        if session.run_id:
            linked_run = load_delivery_run(session.feature, session.run_id, root=root)
        if linked_run is None:
            linked_run = latest_delivery_run(session.feature, root=root)
    task_scopes: dict[int, list[str]] = {}
    if linked_run is not None:
        for task in linked_run.tasks:
            task_scopes[task.task_index] = list(task.file_paths)
    result = apply_session(session, root, task_file_scopes=task_scopes)
    updated_session = load_session(root) or session
    if linked_run is not None:
        linked_run = sync_delivery_run_with_session(linked_run, updated_session, root=root)
        linked_run = sync_delivery_run_integration(
            linked_run,
            session=updated_session,
            root=root,
        )
    payload = {
        "success": result.success,
        "applied": result.applied_indices,
        "appliedFiles": result.applied_files,
        "conflictIndex": result.conflict_index,
        "conflictFiles": result.conflict_files,
        "error": "",
    }
    if linked_run is not None:
        payload["deliveryRun"] = linked_run.to_dict()
    if args.json:
        _print_json(payload)
    else:
        if result.success:
            print(f"Applied tasks: {result.applied_indices}")
            if result.applied_files:
                print(f"Files: {result.applied_files}")
        else:
            print(f"Apply stopped at task {result.conflict_index}: {result.conflict_files}")
        if linked_run is not None:
            print(
                "Delivery Run integration: "
                f"{linked_run.integration.get('status', 'pending')} "
                f"(merged={len(linked_run.integration.get('mergedTaskIndices', []))})"
            )
            print(
                "Delivery Run review readiness: "
                f"{linked_run.review_readiness.get('status', 'pending')} "
                f"(plan_verify={linked_run.review_readiness.get('planVerifyPassed')})"
            )
    return 0 if result.success else 1


def cmd_session_cleanup(args: argparse.Namespace) -> int:
    root = _root()
    session = load_session(root)
    if not session:
        print("No active worktree session")
        return 0
    linked_run = None
    if session.feature:
        if session.run_id:
            linked_run = load_delivery_run(session.feature, session.run_id, root=root)
        if linked_run is None:
            linked_run = latest_delivery_run(session.feature, root=root)
    cleanup_session(session, root)
    if linked_run is not None:
        linked_run = sync_delivery_run_with_session(linked_run, session, root=root)
        sync_delivery_run_integration(linked_run, session=session, root=root)
    print("Worktrees cleaned")
    return 0


def cmd_session_reconcile(args: argparse.Namespace) -> int:
    from scripts.memory.reconcile import reconcile_session
    root = _root()
    result = reconcile_session(root)
    if getattr(args, 'json', False):
        _print_json(result)
    else:
        for entry in result.get("reconciled", []):
            print(f"Closed: {entry['id']} ({entry.get('status', '')})")
        for entry in result.get("skipped", []):
            print(f"Skipped: {entry['id']} ({entry.get('reason', '')})")
        for entry in result.get("errors", []):
            print(f"Error: {entry['id']}: {entry.get('error', '')}")
        total = len(result.get("reconciled", [])) + len(result.get("skipped", [])) + len(result.get("errors", []))
        if total == 0:
            print("No orphaned issues found")
        else:
            print(f"\nTotal: {len(result.get('reconciled', []))} closed, {len(result.get('skipped', []))} skipped, {len(result.get('errors', []))} errors")
    return 0


def cmd_run_create(args: argparse.Namespace) -> int:
    root = _root()
    plan_path = _plan_contract_path(root, args.feature, args.plan)
    if not plan_path.exists():
        print(f"Plan contract not found: {plan_path}", file=sys.stderr)
        return 1
    try:
        plan_contract = json.loads(plan_path.read_text(encoding="utf-8"))
        if not isinstance(plan_contract, dict):
            raise ValueError("plan contract must be a JSON object")
        profile = resolve_profile(root, plan_contract=plan_contract)
        taskdescs = plan_to_task_descriptions(plan_path, root, profile=profile)
    except Exception as exc:
        print(f"Error: failed to load plan tasks: {exc}", file=sys.stderr)
        return 1
    recommendation = recommend_team_mode(taskdescs, profile=profile)
    mode = args.mode
    if mode == "auto":
        mode = "team" if recommendation.get("recommended") else "serial"
    run = ensure_delivery_run(
        feature=args.feature,
        plan_number=normalize_plan_number(args.plan),
        plan_path=plan_path,
        task_descriptions=taskdescs,
        mode=mode,
        run_id=args.run_id,
        started_by=args.actor,
        branch=args.branch or _git_branch(root),
        recommendation=recommendation,
        profile=profile,
        resume_latest=not args.no_resume_latest,
        root=root,
    )
    set_phase(args.feature, "implement", root=root)
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_list(args: argparse.Namespace) -> int:
    root = _root()
    statuses = set(args.status or []) if args.status else None
    runs = list_delivery_runs(
        feature_slug=args.feature,
        statuses=statuses,
        mode=args.mode,
        include_terminal=args.all,
        root=root,
    )
    payload = [summarize_delivery_run(run, root=root) for run in runs]
    if args.needs_attention:
        queue = load_delivery_run_attention_queue(root=root)
        if queue is None:
            report = watch_delivery_runs(
                feature_slug=args.feature,
                root=root,
            )
            queue = build_delivery_run_attention_queue(report)
        if args.feature:
            queue = filter_delivery_run_attention_queue(queue, feature_slug=args.feature, root=root)
        attention_by_run: dict[tuple[str, str], list[dict]] = {}
        run_priority: dict[tuple[str, str], int] = {}
        for item in queue.get("items", []) if isinstance(queue.get("items"), list) else []:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("feature", "")), str(item.get("runId", "")))
            attention_by_run.setdefault(key, []).append(item)
            run_priority.setdefault(key, len(run_priority))
        filtered_payload: list[dict] = []
        for entry in payload:
            key = (str(entry.get("feature", "")), str(entry.get("runId", "")))
            if key not in attention_by_run:
                continue
            entry = dict(entry)
            items = attention_by_run[key]
            entry["attentionKinds"] = [str(item.get("kind", "")) for item in items]
            entry["attentionMaxSeverity"] = "fail" if any(item.get("severity") == "fail" for item in items) else "warn"
            entry["attentionNextAction"] = str(items[0].get("nextAction", "")).strip() if items else ""
            entry["workOrderId"] = str(items[0].get("workOrderId", entry.get("feature", ""))).strip() if items else str(entry.get("feature", ""))
            stale_minutes = [
                float(item.get("minutesStale"))
                for item in items
                if isinstance(item.get("minutesStale"), (int, float))
            ]
            if stale_minutes:
                entry["attentionMinutesStale"] = max(stale_minutes)
            filtered_payload.append(entry)
        payload = sorted(
            filtered_payload,
            key=lambda entry: run_priority.get((str(entry.get("feature", "")), str(entry.get("runId", ""))), len(run_priority)),
        )
    if args.json:
        _print_json(payload)
    else:
        _print_run_list(payload)
    return 0


def cmd_run_show(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    run = refresh_delivery_run(run, root=root)
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_work_show(args: argparse.Namespace) -> int:
    root = _root()
    order = sync_work_order(args.feature, root=root)
    payload = order.to_dict()
    if args.json:
        _print_json(payload)
    else:
        _print_work_order(payload)
    return 0


def cmd_work_list(args: argparse.Namespace) -> int:
    root = _root()
    entries = [order.to_dict() for order in sync_all_work_orders(feature_slug=args.feature, root=root)]
    if args.needs_attention:
        entries = [
            entry
            for entry in entries
            if isinstance(entry.get("attentionSummary"), dict)
            and int(entry["attentionSummary"].get("itemCount", 0) or 0) > 0
        ]
        entries.sort(
            key=lambda entry: (
                0 if str(entry.get("attentionSummary", {}).get("highestSeverity", "ok")) == "fail" else 1,
                -int(entry.get("attentionSummary", {}).get("itemCount", 0) or 0),
                str(entry.get("workOrderId", "")),
            )
        )
    if args.json:
        _print_json(entries)
    else:
        _print_work_order_list(entries)
    return 0


def cmd_work_sync(args: argparse.Namespace) -> int:
    root = _root()
    if args.feature:
        order = sync_work_order(args.feature, root=root)
        payload = order.to_dict()
    else:
        payload = [order.to_dict() for order in sync_all_work_orders(root=root)]
    if args.json:
        _print_json(payload)
    else:
        if isinstance(payload, list):
            _print_work_order_list(payload)
        else:
            _print_work_order(payload)
    return 0


def cmd_work_next(args: argparse.Namespace) -> int:
    root = _root()
    payload = {
        "feature": args.feature,
        "nextAction": next_work_order_action(args.feature, root=root),
        "workOrder": sync_work_order(args.feature, root=root).to_dict(),
    }
    if args.json:
        _print_json(payload)
    else:
        next_action = payload["nextAction"]
        print(f"Work Order: {args.feature}")
        print(f"Next action: {next_action.get('kind', '')}")
        if next_action.get("summary"):
            print(f"Summary: {next_action['summary']}")
        if next_action.get("command"):
            print(f"Command: {next_action['command']}")
    return 0


def cmd_plan_auto(args: argparse.Namespace) -> int:
    root = _root()
    try:
        payload = auto_plan_feature(
            args.feature,
            plan_number=args.plan,
            requested_profile_name=args.profile,
            force=args.force,
            start_run=False if args.no_run else None,
            root=root,
        )
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(payload)
    else:
        status = "created" if payload.get("createdPlan") else "reused"
        print(f"Plan auto: {payload.get('feature', args.feature)} {payload.get('planNumber', '')} ({status})")
        profile = payload.get("profile", {})
        if isinstance(profile, dict) and profile.get("name"):
            print(f"Profile: {profile['name']}")
        if payload.get("planningRoot"):
            print(f"Planning root: {payload['planningRoot']}")
        print(f"Plan path: {payload.get('planPath', '')}")
        if payload.get("mode"):
            print(f"Mode: {payload['mode']}")
        if payload.get("startedRun") and isinstance(payload.get("deliveryRun"), dict):
            print(f"Delivery Run: {payload['deliveryRun'].get('runId', '')}")
        suggestion = payload.get("profileSuggestion", {})
        if isinstance(suggestion, dict) and suggestion.get("reason"):
            print(f"Reason: {suggestion['reason']}")
        warnings = [
            item
            for item in payload.get("validation", [])
            if isinstance(item, dict) and str(item.get("level", "")).upper() != "ERROR"
        ]
        if warnings:
            print(f"Validation findings: {len(warnings)} warning(s)")
    return 0


def cmd_lane_show(args: argparse.Namespace) -> int:
    root = _root()
    payload = describe_feature_lane(args.feature, root=root)
    if payload is None:
        print(f"No feature lane found for {args.feature!r}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(payload)
    else:
        _print_lane(payload)
    return 0


def cmd_lane_list(args: argparse.Namespace) -> int:
    root = _root()
    payload = list_feature_lane_snapshots(
        feature_slug=args.feature,
        include_terminal=args.all,
        root=root,
    )
    if args.json:
        _print_json(payload)
    else:
        _print_lane_list(payload)
    return 0


def cmd_dispatch_ready(args: argparse.Namespace) -> int:
    root = _root()
    payload = dispatch_ready_features(
        feature_slug=args.feature,
        lease_owner=args.owner,
        root=root,
    )
    if args.json:
        _print_json(payload)
    else:
        leased = payload.get("leased", []) if isinstance(payload.get("leased"), list) else []
        auto_planned = payload.get("autoPlanned", []) if isinstance(payload.get("autoPlanned"), list) else []
        auto_plan_skipped = payload.get("autoPlanSkipped", []) if isinstance(payload.get("autoPlanSkipped"), list) else []
        plan_errors = payload.get("planErrors", []) if isinstance(payload.get("planErrors"), list) else []
        reclaimed = payload.get("reclaimed", []) if isinstance(payload.get("reclaimed"), list) else []
        skipped = payload.get("skipped", []) if isinstance(payload.get("skipped"), list) else []
        print(
            "Dispatch ready: "
            f"leased={len(leased)} "
            f"auto-planned={len(auto_planned)} "
            f"plan-errors={len(plan_errors)} "
            f"reclaimed={len(reclaimed)} "
            f"skipped={len(skipped)} "
            f"active={payload.get('activeLaneCount', 0)}"
        )
        for entry in reclaimed:
            print(
                f"- reclaimed {entry.get('feature', '')} "
                f"from {entry.get('laneId', '')} "
                f"({entry.get('releaseReason', '') or entry.get('health', {}).get('reason', 'unknown')})"
            )
        for entry in leased:
            print(
                f"- leased {entry.get('feature', '')} "
                f"into {entry.get('laneId', '')} "
                f"({entry.get('worktreePath', '')})"
            )
        for entry in auto_planned:
            created = "created" if entry.get("createdPlan") else "reused"
            run = entry.get("deliveryRun", {}) if isinstance(entry.get("deliveryRun"), dict) else {}
            run_fragment = f", run={run.get('runId', '')}" if run.get("runId") else ""
            print(
                f"- auto-planned {entry.get('feature', '')} "
                f"plan={entry.get('planNumber', '')} "
                f"({created}{run_fragment})"
            )
        for entry in auto_plan_skipped:
            print(
                f"- auto-plan skipped {entry.get('feature', '')} "
                f"({entry.get('reason', 'unknown')})"
            )
        for entry in plan_errors:
            print(
                f"- auto-plan failed {entry.get('feature', '')} "
                f"({entry.get('error', 'unknown error')})"
            )
        for entry in skipped:
            print(f"- skipped {entry.get('feature', '')}: {entry.get('reason', 'unknown')}")
    return 0


def cmd_feedback_sync(args: argparse.Namespace) -> int:
    root = _root()
    payload = sync_shape_feedback(feature_slug=args.feature, root=root)
    if args.json:
        _print_json(payload)
    else:
        print(f"Shape feedback synced: {payload.get('itemsAdded', 0)} item(s)")
        for entry in payload.get("updatedShapes", []) if isinstance(payload.get("updatedShapes"), list) else []:
            print(f"- {entry.get('shapePath', '')}: +{entry.get('itemsAdded', 0)}")
    return 0


def cmd_initiative_show(args: argparse.Namespace) -> int:
    root = _root()
    slug = args.slug
    shape_path = root / "docs" / "planning" / "work" / "ideas" / slug / "SHAPE.json"
    if not shape_path.exists():
        print(f"No SHAPE.json found for initiative '{slug}'", file=sys.stderr)
        return 1
    rollup = build_initiative_rollup(root, shape_path)
    if "error" in rollup:
        print(f"Error: {rollup['error']}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps(rollup, indent=2))
        return 0
    # Compact table output
    print(f"## Initiative: {rollup['initiative']} ({rollup['slug']})")
    print(f"Progress: {rollup['completedFeatures']}/{rollup['totalFeatures']} completed\n")
    print(f"{'Feature':<30} {'Status':<15} {'Review':<10}")
    print("-" * 55)
    for f in rollup.get("features", []):
        print(f"{f['slug']:<30} {f['status']:<15} {f.get('reviewVerdict', 'pending'):<10}")
    feedback = rollup.get("pendingFeedback", [])
    if feedback:
        print(f"\nPending feedback: {len(feedback)} item(s)")
    next_action = rollup.get("nextAction", {})
    if next_action:
        print(f"\nNext: {next_action.get('summary', '')}")
        cmd = next_action.get("command", "")
        if cmd:
            print(f"  -> {cmd}")
    return 0


def cmd_initiative_list(args: argparse.Namespace) -> int:
    root = _root()
    initiatives = list_initiatives(root)
    if getattr(args, "json", False):
        print(json.dumps(initiatives, indent=2))
        return 0
    if not initiatives:
        print("No initiatives found.")
        return 0
    print(f"{'Initiative':<30} {'Slug':<25} {'Candidates':<10}")
    print("-" * 65)
    for init in initiatives:
        print(f"{init.get('initiative', ''):<30} {init.get('slug', ''):<25} {init.get('candidateCount', 0):<10}")
    return 0


def cmd_initiative_current(args: argparse.Namespace) -> int:
    root = _root()
    payload = current_initiative_rollup(
        root,
        feature_slug=getattr(args, "feature", None),
        branch_name=args.branch or _git_branch(root),
    )
    if args.json:
        _print_json(payload)
        return 0
    if not payload.get("found"):
        print("No initiative context found.")
        return 0
    rollup = payload.get("rollup", {}) if isinstance(payload.get("rollup"), dict) else {}
    print(
        f"Initiative: {rollup.get('initiative', '')} "
        f"({rollup.get('completedFeatures', 0)}/{rollup.get('totalFeatures', 0)} completed)"
    )
    print(f"Feature: {payload.get('feature', '')}")
    print(f"Shape: {payload.get('shapePath', '')}")
    next_action = rollup.get("nextAction", {}) if isinstance(rollup.get("nextAction"), dict) else {}
    if next_action.get("summary"):
        print(f"Next: {next_action['summary']}")
    return 0


def cmd_run_watch(args: argparse.Namespace) -> int:
    root = _root()
    report = watch_delivery_runs(
        feature_slug=args.feature,
        stale_minutes=args.stale_minutes,
        review_stale_minutes=args.review_stale_minutes,
        include_terminal=args.all,
        root=root,
    )
    if not args.no_write:
        report = persist_delivery_run_watch_report(report, root=root)["report"]
    if args.json:
        _print_json(report)
    else:
        _print_watch_report(report)
    findings = report.get("findings", [])
    return 1 if any(finding.get("severity") == "fail" for finding in findings) else 0


def cmd_run_watch_status(args: argparse.Namespace) -> int:
    root = _root()
    payload = delivery_run_watch_schedule_status(root=root)
    if args.json:
        _print_json(payload)
    else:
        _print_watch_schedule(payload)
    summary = payload.get("lastAttentionSummary", {})
    if isinstance(summary, dict) and summary.get("highestSeverity") == "fail":
        return 1
    return 0


def cmd_run_watch_tick(args: argparse.Namespace) -> int:
    root = _root()
    payload = run_scheduler_once(
        jobs=["watch_patrol"],
        force=args.force,
        triggered_by="manual-watch",
        root=root,
    )
    jobs = payload.get("jobs", {}) if isinstance(payload.get("jobs"), dict) else {}
    watch_payload = jobs.get("watch_patrol", {}) if isinstance(jobs.get("watch_patrol"), dict) else {}
    display_payload = dict(watch_payload) if isinstance(watch_payload, dict) else {}
    display_payload.setdefault("scheduler", payload.get("status", {}))
    display_payload.setdefault("executed", payload.get("executed", False))
    display_payload.setdefault("schedule", delivery_run_watch_schedule_status(root=root))
    if payload.get("reason") and "reason" not in display_payload:
        display_payload["reason"] = payload["reason"]
    if args.json:
        _print_json(display_payload)
    else:
        _print_watch_schedule(display_payload.get("schedule", {}))
        if display_payload.get("executed"):
            _print_watch_patrol(display_payload)
        elif display_payload.get("reason"):
            print(f"Tick skipped: {display_payload['reason']}")
    attention = watch_payload.get("attention", {}) if isinstance(watch_payload, dict) else {}
    items = attention.get("items", []) if isinstance(attention, dict) else []
    if isinstance(items, list) and any(
        isinstance(item, dict) and item.get("severity") == "fail" for item in items
    ):
        return 1
    return 0


def cmd_run_attention(args: argparse.Namespace) -> int:
    root = _root()
    effective_limit = args.limit
    if effective_limit is None:
        effective_limit = watch_settings_cfg(load_workflow_config(root)).get("attentionLimit")
    force_refresh = bool(args.refresh or args.stale_minutes or args.review_stale_minutes or args.all)
    queue = None if force_refresh else load_delivery_run_attention_queue(root=root)
    if queue is None and not force_refresh:
        report = load_delivery_run_watch_report(root=root)
        if report is not None:
            queue = build_delivery_run_attention_queue(report)
    if queue is None:
        report = watch_delivery_runs(
            feature_slug=args.feature,
            stale_minutes=args.stale_minutes,
            review_stale_minutes=args.review_stale_minutes,
            include_terminal=args.all,
            root=root,
        )
        if args.no_write:
            queue = build_delivery_run_attention_queue(report)
        else:
            queue = persist_delivery_run_watch_report(report, root=root)["attention"]
    queue = filter_delivery_run_attention_queue(
        queue,
        feature_slug=args.feature,
        severities=set(args.severity or []) if args.severity else None,
        kinds=set(args.kind or []) if args.kind else None,
        limit=effective_limit,
        root=root,
    )
    if args.json:
        _print_json(queue)
    else:
        _print_attention_queue(queue)
    items = queue.get("items", [])
    if isinstance(items, list) and any(
        isinstance(item, dict) and item.get("severity") == "fail" for item in items
    ):
        return 1
    return 0


def cmd_run_watch_patrol(args: argparse.Namespace) -> int:
    root = _root()
    report = watch_delivery_runs(
        feature_slug=args.feature,
        stale_minutes=args.stale_minutes,
        review_stale_minutes=args.review_stale_minutes,
        include_terminal=args.all,
        root=root,
    )
    persisted = persist_delivery_run_watch_report(report, root=root)
    payload = {
        "report": persisted["report"],
        "attention": persisted["attention"],
        "delta": persisted.get("delta", {}),
        "snapshot": persisted.get("snapshot", {}),
    }
    if args.feature:
        payload["attention"] = filter_delivery_run_attention_queue(
            payload["attention"],
            feature_slug=args.feature,
            root=root,
        )
    payload["workOrders"] = [
        order.to_dict()
        for order in sync_all_work_orders(feature_slug=args.feature, root=root)
    ]
    payload["dispatch"] = dispatch_ready_features(feature_slug=args.feature, root=root)
    payload["feedbackSync"] = sync_shape_feedback(feature_slug=args.feature, root=root)
    if args.json:
        _print_json(payload)
    else:
        _print_watch_patrol(payload)
        dispatch_payload = payload.get("dispatch", {})
        leased = dispatch_payload.get("leased", []) if isinstance(dispatch_payload, dict) else []
        if leased:
            print(f"Dispatch: leased {len(leased)} ready feature(s)")
        feedback_payload = payload.get("feedbackSync", {})
        items_added = feedback_payload.get("itemsAdded", 0) if isinstance(feedback_payload, dict) else 0
        if items_added:
            print(f"Feedback sync: added {items_added} item(s) to SHAPE inboxes")
    items = payload.get("attention", {}).get("items", [])
    if isinstance(items, list) and any(
        isinstance(item, dict) and item.get("severity") == "fail" for item in items
    ):
        return 1
    return 0


def cmd_run_watch_history(args: argparse.Namespace) -> int:
    root = _root()
    history = load_delivery_run_watch_history(limit=args.limit, root=root)
    if args.json:
        _print_json(history)
    else:
        _print_watch_history(history)
    return 0


def cmd_scheduler_status(args: argparse.Namespace) -> int:
    root = _root()
    payload = scheduler_status(root=root)
    if args.json:
        _print_json(payload)
    else:
        _print_scheduler_status(payload)
    return 0


def cmd_scheduler_run_once(args: argparse.Namespace) -> int:
    root = _root()
    payload = run_scheduler_once(
        jobs=list(args.job or []) or None,
        force=args.force,
        triggered_by="manual",
        root=root,
    )
    if args.json:
        _print_json(payload)
    else:
        _print_scheduler_run(payload)
    jobs = payload.get("jobs", {})
    watch_result = jobs.get("watch_patrol", {}) if isinstance(jobs, dict) else {}
    attention = watch_result.get("attention", {}) if isinstance(watch_result, dict) else {}
    items = attention.get("items", []) if isinstance(attention, dict) else []
    if isinstance(items, list) and any(isinstance(item, dict) and item.get("severity") == "fail" for item in items):
        return 1
    return 0


def cmd_scheduler_start(args: argparse.Namespace) -> int:
    root = _root()
    payload = start_scheduler_supervisor(root=root)
    if args.json:
        _print_json(payload)
    else:
        _print_scheduler_status(payload)
    return 0


def cmd_scheduler_stop(args: argparse.Namespace) -> int:
    root = _root()
    payload = stop_scheduler_supervisor(root=root)
    if args.json:
        _print_json(payload)
    else:
        _print_scheduler_status(payload)
    return 0


def cmd_scheduler_worker(args: argparse.Namespace) -> int:
    return scheduler_worker_loop(_root())


def cmd_run_refresh(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    run = refresh_delivery_run(run, root=root)
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_next(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    run = refresh_delivery_run(run, root=root)
    next_action = next_delivery_run_action(run)
    ready_tasks = []
    for task in _ready_run_tasks(run):
        ready_tasks.append(
            {
                "taskIndex": task.task_index,
                "title": task.title,
                "status": task.status,
                "memoryId": task.memory_id,
                "cwd": task.cwd,
                "verifyCommands": list(task.verify_commands),
                "packageVerifyCommands": list(task.package_verify_commands),
                "beginCommand": f"python3 .cnogo/scripts/workflow_memory.py run-task-begin {run.feature} {task.task_index} --run-id {run.run_id}",
            }
        )
    payload = {
        "feature": run.feature,
        "runId": run.run_id,
        "mode": run.mode,
        "status": run.status,
        "profile": run.profile if isinstance(getattr(run, "profile", None), dict) else {},
        "integrationStatus": run.integration.get("status", "pending"),
        "reviewReadiness": run.review_readiness.get("status", "pending"),
        "reviewStatus": run.review.get("status", "pending"),
        "shipStatus": run.ship.get("status", "pending"),
        "nextAction": next_action,
        "readyTasks": ready_tasks,
        "readyCount": len(ready_tasks),
    }
    if args.json:
        _print_json(payload)
    else:
        _print_run_next(payload)
    return 0


def cmd_run_task_prompt(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    try:
        taskdesc = _resolve_task_description_for_run(root, run, args.task_index)
        prompt = generate_implement_prompt(taskdesc, actor_name=args.actor)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    payload = {
        "feature": run.feature,
        "planNumber": run.plan_number,
        "runId": run.run_id,
        "taskIndex": args.task_index,
        "title": str(taskdesc.get("title", "")),
        "taskId": str(taskdesc.get("task_id", "")),
        "actor": args.actor,
        "prompt": prompt,
    }
    if args.json:
        _print_json(payload)
    else:
        print(prompt)
    return 0


def cmd_run_task_begin(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    task = _find_run_task(run, args.task_index)
    if task is None:
        print(f"Unknown task index {args.task_index} for run {run.run_id}", file=sys.stderr)
        return 1
    if task.status not in {"ready", "in_progress", "failed"}:
        print(f"Task {task.task_index} cannot begin from status {task.status!r}.", file=sys.stderr)
        return 1
    if task.memory_id and not args.skip_memory:
        try:
            claim(task.memory_id, actor=args.actor, root=root)
        except Exception as exc:
            print(f"Error: failed to claim memory task {task.memory_id}: {exc}", file=sys.stderr)
            return 1
    try:
        run = begin_delivery_run_task(
            run,
            task_index=args.task_index,
            actor=args.actor,
            branch=args.branch,
            worktree_path=args.worktree_path,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_task_complete(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    task = _find_run_task(run, args.task_index)
    if task is None:
        print(f"Unknown task index {args.task_index} for run {run.run_id}", file=sys.stderr)
        return 1
    if task.status not in {"in_progress", "done", "failed"}:
        print(f"Task {task.task_index} cannot complete from status {task.status!r}.", file=sys.stderr)
        return 1
    if task.memory_id and not args.skip_memory:
        try:
            report_done(
                task.memory_id,
                outputs={"verifyCommands": list(args.verify_command or [])},
                actor=args.actor,
                root=root,
            )
        except Exception as exc:
            print(f"Error: failed to report memory completion for {task.memory_id}: {exc}", file=sys.stderr)
            return 1
    try:
        run = complete_delivery_run_task(
            run,
            task_index=args.task_index,
            actor=args.actor,
            verify_commands=list(args.verify_command or []),
            note=args.note or None,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_task_fail(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    try:
        run = fail_delivery_run_task(
            run,
            task_index=args.task_index,
            actor=args.actor,
            error=args.error,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_task_set(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    try:
        run = update_delivery_task_status(
            run,
            task_index=args.task_index,
            status=args.status,
            assignee=args.assignee,
            branch=args.branch,
            worktree_path=args.worktree_path,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_sync_session(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    session = load_session(root)
    if session is None:
        print("No active worktree session", file=sys.stderr)
        return 1
    if session.feature and session.feature != run.feature:
        print(
            f"Active worktree session is for feature {session.feature!r}, not {run.feature!r}",
            file=sys.stderr,
        )
        return 1
    run = sync_delivery_run_with_session(run, session, root=root)
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_plan_verify(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    commands = [str(command).strip() for command in list(args.verify_command or []) if str(command).strip()]
    if args.use_plan_verify:
        commands.extend(_plan_verify_commands_for_run(root, run))
    if args.command_file:
        command_file = Path(args.command_file)
        if not command_file.is_absolute():
            command_file = root / command_file
        if not command_file.exists():
            print(f"Command file not found: {command_file}", file=sys.stderr)
            return 1
        for line in command_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                commands.append(line)
    deduped_commands: list[str] = []
    seen_commands: set[str] = set()
    for command in commands:
        if command in seen_commands:
            continue
        seen_commands.add(command)
        deduped_commands.append(command)
    run = record_delivery_run_plan_verification(
        run,
        passed=args.result == "pass",
        commands=deduped_commands,
        note=args.note,
        root=root,
    )
    if args.result == "pass" and run.review_readiness.get("status") == "ready":
        set_phase(args.feature, "review", root=root)
    elif args.result == "pass" and not args.json:
        print(
            "Plan verification recorded, but review is not ready yet. "
            "Use `python3 .cnogo/scripts/workflow_memory.py "
            f"run-review-ready {args.feature} --run-id {run.run_id}` "
            "after integration is finalized.",
            file=sys.stderr,
        )
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_review_ready(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    session = load_session(root)
    if session is not None and session.feature == run.feature and (not session.run_id or session.run_id == run.run_id):
        run = sync_delivery_run_with_session(run, session, root=root)
    try:
        run = prepare_delivery_run_review_ready(
            run,
            integration_status=args.integration_status,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if run.review_readiness.get("status") == "ready":
        set_phase(args.feature, "review", root=root)
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def _review_ready_or_started(run) -> bool:
    review_readiness = run.review_readiness if isinstance(getattr(run, "review_readiness", None), dict) else {}
    review_state = run.review if isinstance(getattr(run, "review", None), dict) else {}
    return review_readiness.get("status") == "ready" or review_state.get("status") in {"in_progress", "completed"}


def _ship_ready_or_started(run) -> bool:
    ship_state = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    return ship_state.get("status") in {"ready", "in_progress", "completed", "failed"}


def cmd_run_review_start(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    if not _review_ready_or_started(run):
        print(
            "Review cannot start until reviewReadiness.status == ready "
            f"(current={run.review_readiness.get('status', 'pending')!r}). "
            f"If plan verification already passed, run "
            f"`python3 .cnogo/scripts/workflow_memory.py run-review-ready {args.feature} --run-id {run.run_id}` first.",
            file=sys.stderr,
        )
        return 1
    profile_reviewers = (
        profile_required_reviewers(run.profile)
        if isinstance(getattr(run, "profile", None), dict)
        else []
    )
    configured_profile_reviewers: list[str] = []
    if profile_auto_spawn_configured_reviewers(
        run.profile if isinstance(getattr(run, "profile", None), dict) else {}
    ):
        try:
            from scripts.workflow.checks.review import configured_reviewers

            configured_profile_reviewers = configured_reviewers(root)
        except Exception:
            configured_profile_reviewers = []
    merged_reviewers: list[str] = []
    seen_reviewers: set[str] = set()
    for reviewer in [*configured_profile_reviewers, *(args.reviewer or []), *profile_reviewers]:
        if not isinstance(reviewer, str) or not reviewer.strip():
            continue
        value = reviewer.strip()
        if value in seen_reviewers:
            continue
        seen_reviewers.add(value)
        merged_reviewers.append(value)
    run = start_delivery_run_review(
        run,
        reviewers=merged_reviewers,
        automated_verdict=args.automated_verdict,
        note=args.note,
        root=root,
    )
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_ship_start(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    ship_state = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    if ship_state.get("status") not in {"ready", "failed", "in_progress"}:
        print(
            "Ship cannot start until the Delivery Run is ship-ready "
            f"(current ship.status={ship_state.get('status', 'pending')!r}, "
            f"review.status={run.review.get('status', 'pending')!r}).",
            file=sys.stderr,
        )
        return 1
    try:
        run = start_delivery_run_ship(
            run,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_ship_complete(args: argparse.Namespace) -> int:
    root = _root()
    commit = args.commit
    feature = args.feature

    # Auto-infer commit and branch when not provided
    if commit is None:
        branch = _git_branch(root)
        expected_branch = f"feature/{feature}"
        if branch != expected_branch:
            print(
                f"Auto-infer failed: current branch is '{branch}', expected '{expected_branch}'.\n"
                f"Pass commit SHA explicitly: run-ship-complete {feature} <commit-sha>",
                file=sys.stderr,
            )
            return 1
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, cwd=str(root),
            )
            if result.returncode != 0:
                print("Auto-infer failed: git rev-parse HEAD failed.", file=sys.stderr)
                return 1
            commit = result.stdout.strip()
        except Exception:
            print("Auto-infer failed: could not run git rev-parse HEAD.", file=sys.stderr)
            return 1
        if not commit:
            print("Auto-infer failed: empty commit SHA from git rev-parse HEAD.", file=sys.stderr)
            return 1

    run = _resolve_run(root, feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {feature!r}", file=sys.stderr)
        return 1
    if not _ship_ready_or_started(run):
        print(
            "Ship completion requires a ship-ready or already-started Delivery Run.",
            file=sys.stderr,
        )
        return 1
    try:
        run = complete_delivery_run_ship(
            run,
            commit=commit,
            branch=args.branch or _git_branch(root),
            pr_url=args.pr_url or "",
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_ship_fail(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    ship_state = run.ship if isinstance(getattr(run, "ship", None), dict) else {}
    if ship_state.get("status") not in {"ready", "in_progress", "failed"}:
        print(
            "Ship failure can only be recorded after ship is ready or in progress.",
            file=sys.stderr,
        )
        return 1
    try:
        run = fail_delivery_run_ship(
            run,
            error=args.error or "",
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_ship_draft(args: argparse.Namespace) -> int:
    root = _root()
    feature = args.feature
    draft = build_ship_draft(root, feature)
    if getattr(args, "json", False):
        _print_json(draft)
        return 0
    # Compact table output
    print(f"## Ship Draft: {feature}")
    print(f"\nCommit message: {draft.get('commitMessage', '(none)')}")
    print(f"PR title: {draft.get('prTitle', '(none)')}")
    print(f"Branch: {draft.get('branch', '(none)')}")
    surface = draft.get("commitSurface", [])
    print(f"\nCommit surface ({len(surface)} files):")
    for f in surface:
        print(f"  {f}")
    excluded = draft.get("excludedFiles", [])
    if excluded:
        print(f"\nExcluded ({len(excluded)} files):")
        for f in excluded:
            print(f"  {f}")
    warnings = draft.get("warnings", [])
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  \u26a0 {w}")
    print(f"\n{draft.get('gitAddCommand', '')}")
    return 0


def cmd_verify_import(args: argparse.Namespace) -> int:
    try:
        module = importlib.import_module(args.module)
    except Exception as exc:
        print(f"Import failed for {args.module}: {exc}", file=sys.stderr)
        return 1
    missing: list[str] = []
    for symbol in list(args.symbol or []):
        if not hasattr(module, symbol):
            missing.append(symbol)
    payload = {
        "module": args.module,
        "symbols": list(args.symbol or []),
        "ok": not missing,
        "missing": missing,
    }
    if args.json:
        _print_json(payload)
    else:
        if missing:
            print(f"Imported {args.module}, but missing symbols: {', '.join(missing)}")
        else:
            print(f"Imported {args.module}")
            for symbol in list(args.symbol or []):
                print(f"  - {symbol}")
    return 0 if not missing else 1


def cmd_run_review_stage_set(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    if not _review_ready_or_started(run):
        print(
            "Review stages cannot be updated until review is ready or already started.",
            file=sys.stderr,
        )
        return 1
    try:
        run = update_delivery_run_review_stage(
            run,
            stage=args.stage,
            status=args.status,
            findings=list(args.finding or []),
            evidence=list(args.evidence or []),
            notes=list(args.note or []),
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_review_verdict(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    stages = run.review.get("stages", []) if isinstance(getattr(run, "review", None), dict) else []
    if args.verdict != "pending":
        if not isinstance(stages, list) or any(
            not isinstance(stage, dict) or stage.get("status") not in {"pass", "warn", "fail"}
            for stage in stages
        ):
            print(
                "Final review verdict requires both stage reviews to be completed first.",
                file=sys.stderr,
            )
            return 1
    try:
        run = set_delivery_run_review_verdict(
            run,
            verdict=args.verdict,
            note=args.note,
            root=root,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def cmd_run_review_sync(args: argparse.Namespace) -> int:
    root = _root()
    run = _resolve_run(root, args.feature, args.run_id)
    if run is None:
        print(f"No delivery run found for feature {args.feature!r}", file=sys.stderr)
        return 1
    try:
        run = sync_delivery_run_review(run, root=root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(run.to_dict())
    else:
        _print_run(run)
    return 0


def _profile_suggestion_payload(root: Path, feature: str, plan_number: str | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    plan_contract = None
    if plan_number:
        plan_path = _plan_contract_path(root, feature, plan_number)
        plan_contract = _load_json_contract(plan_path)
        if plan_contract is None:
            raise FileNotFoundError(f"Plan contract not found or invalid: {plan_path}")
    context_contract = _load_json_contract(_context_contract_path(root, feature))
    suggestion = suggest_profile(
        root,
        feature_slug=feature,
        plan_contract=plan_contract,
        context_contract=context_contract,
    )
    if plan_contract is not None:
        current_profile = profile_name_from_plan(plan_contract)
        suggestion["currentProfile"] = current_profile or ""
        suggestion["matchesCurrent"] = bool(current_profile and current_profile == suggestion["name"])
    return suggestion, plan_contract


def cmd_profile_suggest(args: argparse.Namespace) -> int:
    root = _root()
    try:
        suggestion, plan_contract = _profile_suggestion_payload(root, args.feature, args.plan)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        _print_json(suggestion)
    else:
        _print_profile_suggestion(suggestion)
        current_profile = suggestion.get("currentProfile")
        if isinstance(current_profile, str) and current_profile:
            print(f"Current profile: {current_profile}")
    return 0


def cmd_profile_list(args: argparse.Namespace) -> int:
    root = _root()
    catalog = load_profile_catalog(root)
    payload = [
        {
            "name": name,
            "version": contract.get("version", "1.0.0"),
            "source": contract.get("source", "builtin"),
            "description": contract.get("description", ""),
        }
        for name, contract in sorted(catalog.items())
    ]
    if args.json:
        _print_json(payload)
    else:
        _print_profile_catalog(payload)
    return 0


def cmd_profile_init(args: argparse.Namespace) -> int:
    root = _root()
    if not is_profile_name(args.name):
        print(
            "Profile names must be lowercase slug strings like 'feature-delivery' or 'migration-rollout'.",
            file=sys.stderr,
        )
        return 1
    catalog = load_profile_catalog(root)
    base_name = args.base or "feature-delivery"
    base_profile = catalog.get(base_name)
    if base_profile is None:
        print(f"Unknown base profile: {base_name}", file=sys.stderr)
        return 1
    profile_dir = root / ".cnogo" / "profiles"
    profile_path = profile_dir / f"{args.name}.json"
    if profile_path.exists() and not args.force:
        print(f"Profile file already exists: {profile_path}. Use --force to overwrite.", file=sys.stderr)
        return 1
    contract = scaffold_profile_contract(
        args.name,
        base_profile=base_profile,
        description=args.description or "",
    )
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    payload = {
        "name": args.name,
        "base": base_name,
        "path": str(profile_path),
        "profilePath": str(profile_path),
        "contract": contract,
    }
    if args.json:
        _print_json(payload)
    else:
        print(f"Created profile scaffold at {profile_path}")
        print(f"Base: {base_name}")
    return 0


def cmd_profile_stamp(args: argparse.Namespace) -> int:
    root = _root()
    plan_path = _plan_contract_path(root, args.feature, args.plan)
    plan_contract = _load_json_contract(plan_path)
    if plan_contract is None:
        print(f"Plan contract not found or invalid: {plan_path}", file=sys.stderr)
        return 1
    context_contract = _load_json_contract(_context_contract_path(root, args.feature))
    suggestion: dict[str, object] | None = None
    chosen_name = getattr(args, "profile", None)
    if not chosen_name:
        suggestion = suggest_profile(root, feature_slug=args.feature, plan_contract=plan_contract, context_contract=context_contract)
        chosen_name = str(suggestion["name"])
    catalog = load_profile_catalog(root)
    if chosen_name not in catalog:
        print(f"Unknown profile: {chosen_name}", file=sys.stderr)
        return 1
    current_profile = profile_name_from_plan(plan_contract)
    if current_profile and current_profile != chosen_name and not args.force:
        print(
            f"Plan already has profile {current_profile!r}; use --force to replace it.",
            file=sys.stderr,
        )
        return 1
    plan_contract["profile"] = chosen_name
    plan_contract.pop("formula", None)
    plan_path.write_text(json.dumps(plan_contract, indent=2) + "\n", encoding="utf-8")
    try:
        from scripts.workflow_render import render_plan, write

        write(plan_path.with_suffix(".md"), render_plan(plan_contract))
    except Exception as exc:
        print(f"Error: stamped profile but failed to render plan markdown: {exc}", file=sys.stderr)
        return 1
    payload = {
        "feature": args.feature,
        "planNumber": normalize_plan_number(args.plan),
        "profile": chosen_name,
        "replaced": current_profile or "",
        "planPath": str(plan_path),
        "markdownPath": str(plan_path.with_suffix(".md")),
    }
    if suggestion is not None:
        payload["suggestion"] = suggestion
    if args.json:
        _print_json(payload)
    else:
        print(f"Stamped profile `{chosen_name}` on {plan_path.name}")
        if current_profile and current_profile != chosen_name:
            print(f"Replaced: {current_profile}")
        if suggestion is not None and suggestion.get("reason"):
            print(f"Reason: {suggestion['reason']}")
    return 0


def _graph_open(repo: str | None) -> "ContextGraph":
    """Instantiate ContextGraph for the given repo path."""
    from scripts.context import ContextGraph
    return ContextGraph(repo_path=repo or ".")


def _graph_stats(graph: "ContextGraph") -> dict:
    """Get graph stats using available storage methods."""
    node_count = graph._storage.node_count()
    file_count = len(graph._storage.get_indexed_files())
    relationship_count = graph._storage.relationship_count()
    return {"nodes": node_count, "files": file_count, "relationships": relationship_count}


def cmd_graph_index(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    use_json = getattr(args, "json", False)
    use_watch = getattr(args, "watch", False)
    graph = _graph_open(repo)
    try:
        if not use_watch:
            graph.index()
            stats = _graph_stats(graph)
            if use_json:
                print(json.dumps(stats))
            else:
                print(f"Indexed: {stats['nodes']} nodes, {stats['files']} files, {stats['relationships']} relationships")
        else:
            cycle_count = [0]

            def on_cycle(index_stats: dict) -> None:
                cycle_count[0] += 1
                gs = _graph_stats(graph)
                if cycle_count[0] == 1:
                    if use_json:
                        print(json.dumps({"event": "index", **gs}), flush=True)
                        print(json.dumps({"event": "watching"}), flush=True)
                    else:
                        print(f"Indexed: {gs['nodes']} nodes, {gs['files']} files")
                        print("Watching for changes... (Ctrl+C to stop)")
                else:
                    indexed = index_stats.get("files_indexed", 0)
                    removed = index_stats.get("files_removed", 0)
                    changed = indexed + removed
                    if use_json:
                        evt = {"event": "reindex", "files_changed": changed,
                               "files_indexed": indexed, "files_removed": removed,
                               "nodes": gs["nodes"]}
                        print(json.dumps(evt), flush=True)
                    else:
                        print(f"Re-indexed: {changed} files changed, {gs['nodes']} nodes total")

            result = graph.watch(on_cycle=on_cycle)
            if use_json:
                print(json.dumps({"event": "stopped", **result}), flush=True)
            else:
                print("Stopped watching.")
    finally:
        graph.close()
    return 0


def cmd_graph_query(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        results = graph.query(args.name)
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "id": n.id,
                    "name": n.name,
                    "label": n.label.value,
                    "file_path": n.file_path,
                    "start_line": n.start_line,
                    "end_line": n.end_line,
                }
                for n in results
            ]))
            return 0
        if not results:
            print(f"No nodes matching '{args.name}'")
            return 0
        print(f"{'Name':<30} {'Label':<12} {'File':<40} {'Lines'}")
        print("-" * 90)
        for node in results:
            lines = f"{node.start_line}-{node.end_line}" if node.start_line else "-"
            print(f"{node.name:<30} {node.label.value:<12} {node.file_path:<40} {lines}")
    finally:
        graph.close()
    return 0


def cmd_graph_impact(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        results = graph.impact(args.file_path, max_depth=args.depth)
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "name": r.node.name,
                    "label": r.node.label.value,
                    "file_path": r.node.file_path,
                    "edge_type": r.edge_type,
                    "depth": r.depth,
                }
                for r in results
            ]))
            return 0
        if not results:
            print(f"No impact found for '{args.file_path}'")
            return 0
        print(f"Impact analysis for {args.file_path} ({len(results)} affected):")
        current_depth = -1
        for r in results:
            if r.depth != current_depth:
                current_depth = r.depth
                print(f"\n  Depth {current_depth}:")
            print(f"    {r.node.name} ({r.node.label.value}) [{r.edge_type}] — {r.node.file_path}")
    finally:
        graph.close()
    return 0


def cmd_graph_dead(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        graph.index()
        results = graph.dead_code()
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "node_id": r.node_id,
                    "label": r.label.value,
                    "name": r.name,
                    "file_path": r.file_path,
                    "line": r.line,
                }
                for r in results
            ]))
            return 0
        if not results:
            print("0 dead symbols found.")
            return 0
        print(f"{len(results)} dead symbol(s) found:\n")
        for r in results:
            print(f"  DEAD  {r.label.value}:{r.name}  {r.file_path}:{r.line}")
        return 0
    finally:
        graph.close()


def cmd_graph_coupling(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        graph.index()
        threshold = getattr(args, "strength", 0.5)
        results = graph.coupling(threshold=threshold)
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "source_name": r.source_name,
                    "target_name": r.target_name,
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "strength": r.strength,
                    "shared_count": r.shared_count,
                }
                for r in results
            ]))
            return 0
        if not results:
            print("0 coupled symbol pairs found.")
            return 0
        print(f"{len(results)} coupled pair(s) found:\n")
        for r in results:
            print(f"  {r.source_name} <-> {r.target_name}  strength={r.strength} ({r.shared_count} shared)")
        return 0
    finally:
        graph.close()


def cmd_graph_communities(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        min_size = getattr(args, "min_size", 2)
        result = graph.communities(min_size=min_size)
        if getattr(args, "json", False):
            print(json.dumps({
                "communities": [
                    {
                        "community_id": c.community_id,
                        "members": c.members,
                        "member_names": c.member_names,
                        "size": c.size,
                    }
                    for c in result.communities
                ],
                "total_nodes": result.total_nodes,
                "num_communities": result.num_communities,
            }))
            return 0
        if result.num_communities == 0:
            print(f"0 communities found ({result.total_nodes} nodes analyzed).")
            return 0
        print(f"{result.num_communities} community(ies) found ({result.total_nodes} nodes):\n")
        for c in result.communities:
            print(f"  {c.community_id} ({c.size} members):")
            for name in c.member_names:
                print(f"    - {name}")
        return 0
    finally:
        graph.close()


def cmd_graph_flows(args: argparse.Namespace) -> int:
    """Trace execution flows from entry points through forward CALLS edges."""
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        max_depth = getattr(args, "max_depth", 10)
        graph.index()
        flows = graph.flows(max_depth=max_depth)
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "process_id": f.process_id,
                    "entry_point": {
                        "name": f.entry_point.name,
                        "file_path": f.entry_point.file_path,
                        "label": f.entry_point.label.value,
                    },
                    "steps": [
                        {
                            "name": s.node.name,
                            "file_path": s.node.file_path,
                            "label": s.node.label.value,
                            "depth": s.depth,
                        }
                        for s in f.steps
                    ],
                }
                for f in flows
            ]))
            return 0
        if not flows:
            print("0 execution flows found (no entry points detected).")
            return 0
        print(f"{len(flows)} execution flow(s) found:\n")
        for f in flows:
            print(f"  {f.entry_point.name} ({f.entry_point.file_path}) — {len(f.steps)} step(s)")
            for s in f.steps:
                print(f"    {'  ' * (s.depth - 1)}{s.node.name} (depth {s.depth})")
        return 0
    finally:
        graph.close()


def cmd_graph_status(args: argparse.Namespace) -> int:
    """Report graph existence, counts, and staleness."""
    import hashlib
    repo = getattr(args, "repo", None) or "."
    repo_path = Path(repo).resolve()
    db_path = repo_path / ".cnogo" / "graph.db"

    # Venv health
    venv_python = repo_path / ".cnogo" / ".venv" / "bin" / "python3"
    venv_dir = (repo_path / ".cnogo" / ".venv").resolve()
    venv_ok = venv_python.exists()
    in_venv = Path(sys.prefix).resolve() == venv_dir if venv_ok else False

    if not db_path.exists():
        if getattr(args, "json", False):
            print(json.dumps({"exists": False, "venv": venv_ok, "in_venv": in_venv}))
        else:
            venv_label = "ok" if venv_ok else "missing"
            print(f"Not indexed — no graph.db found. (venv: {venv_label})")
        return 0

    graph = _graph_open(repo)
    try:
        node_count = graph._storage.node_count()
        rel_count = graph._storage.relationship_count()
        file_count = graph._storage.file_count()
        indexed_hashes = graph._storage.get_indexed_files()

        # Check for stale files
        stale_count = 0
        for fpath, old_hash in indexed_hashes.items():
            full = repo_path / fpath
            if not full.exists():
                stale_count += 1
            else:
                try:
                    content = full.read_text(encoding="utf-8")
                    cur_hash = hashlib.sha256(content.encode()).hexdigest()
                    if cur_hash != old_hash:
                        stale_count += 1
                except Exception:
                    stale_count += 1

        if getattr(args, "json", False):
            print(json.dumps({
                "exists": True,
                "nodes": node_count,
                "relationships": rel_count,
                "files": file_count,
                "stale_files": stale_count,
                "venv": venv_ok,
                "in_venv": in_venv,
            }))
        else:
            status = "fresh" if stale_count == 0 else f"{stale_count} stale"
            venv_label = "ok" if venv_ok else "missing"
            print(f"Graph: {node_count} nodes, {rel_count} relationships, {file_count} files ({status}, venv: {venv_label})")
        return 0
    finally:
        graph.close()


def cmd_graph_blast_radius(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        # Determine changed files
        files_arg = getattr(args, "files", None)
        if files_arg:
            changed = [f.strip() for f in files_arg.split(",") if f.strip()]
        else:
            # Auto-detect via git diff
            import subprocess
            try:
                proc = subprocess.run(
                    ["git", "diff", "--name-only"],
                    capture_output=True, text=True, cwd=repo,
                )
                changed = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
            except Exception:
                changed = []

        result = graph.review_impact(changed)

        if getattr(args, "json", False):
            print(json.dumps(result))
            return 0

        total = result["total_affected"]
        if total == 0 and not changed:
            print("No changed files detected. 0 affected symbols.")
            return 0

        print(f"Blast radius for {len(changed)} file(s): {total} affected symbol(s)\n")
        for fpath, entries in result["per_file"].items():
            if entries:
                print(f"  {fpath}:")
                for e in entries:
                    print(f"    {e['name']} ({e['label']}) depth={e['depth']} — {e['file_path']}")
            else:
                print(f"  {fpath}: no impact")
        return 0
    finally:
        graph.close()


def cmd_graph_context(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        ctx = graph.context(args.node_id)
    except ValueError as e:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        graph.close()
        return 1
    try:
        node = ctx["node"]
        if getattr(args, "json", False):
            def _nodes_json(nodes):
                return [
                    {"id": n.id, "name": n.name, "label": n.label.value, "file_path": n.file_path}
                    for n in nodes
                ]
            print(json.dumps({
                "node": {"id": node.id, "name": node.name, "label": node.label.value, "file_path": node.file_path},
                "callers": _nodes_json(ctx["callers"]),
                "callees": _nodes_json(ctx["callees"]),
                "importers": _nodes_json(ctx["importers"]),
                "imports": _nodes_json(ctx["imports"]),
                "parent_classes": _nodes_json(ctx["parent_classes"]),
                "child_classes": _nodes_json(ctx["child_classes"]),
            }))
            return 0
        print(f"Node: {node.name} ({node.label.value}) — {node.file_path}")
        for key, label in [
            ("callers", "Callers"),
            ("callees", "Callees"),
            ("importers", "Importers"),
            ("imports", "Imports"),
            ("parent_classes", "Parent classes"),
            ("child_classes", "Child classes"),
        ]:
            items = ctx[key]
            if items:
                print(f"\n  {label} ({len(items)}):")
                for n in items:
                    print(f"    {n.name} ({n.label.value}) — {n.file_path}")
    finally:
        graph.close()
    return 0


def cmd_graph_search(args: argparse.Namespace) -> int:
    repo = getattr(args, "repo", None) or "."
    graph = _graph_open(repo)
    try:
        limit = getattr(args, "limit", 20)
        results = graph.search(args.query, limit=limit)
        if getattr(args, "json", False):
            print(json.dumps([
                {
                    "name": n.name,
                    "label": n.label.value,
                    "file_path": n.file_path,
                    "start_line": n.start_line,
                    "end_line": n.end_line,
                    "score": score,
                }
                for n, score in results
            ]))
            return 0
        if not results:
            print(f"No results for '{args.query}'")
            return 0
        print(f"{'Name':<30} {'Label':<12} {'File':<40} {'Score'}")
        print("-" * 90)
        for node, score in results:
            print(f"{node.name:<30} {node.label.value:<12} {node.file_path:<40} {score:.4f}")
    finally:
        graph.close()
    return 0


def cmd_graph_contract_check(args: argparse.Namespace) -> int:
    """Detect contract (signature) breaks in changed files and find affected callers."""
    from scripts.context.workflow import contract_warnings

    repo = getattr(args, "repo", None) or "."
    files_arg = getattr(args, "files", None)
    if files_arg:
        changed = [f.strip() for f in files_arg.split(",") if f.strip()]
    else:
        import subprocess
        try:
            proc = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True, text=True, cwd=repo,
            )
            changed = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        except Exception:
            changed = []

    result = contract_warnings(repo, changed_files=changed)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    breaks = result.get("breaks", [])
    summary = result.get("summary", {})

    if not breaks:
        print("No contract breaks detected.")
        return 0

    print(f"Contract breaks: {summary.get('total_breaks', 0)} break(s), "
          f"{summary.get('total_affected_callers', 0)} affected caller(s)\n")
    for brk in breaks:
        print(f"  BREAK  {brk['symbol']}  [{brk['change_type']}]")
        print(f"    old: {brk['old_signature']}")
        print(f"    new: {brk['new_signature']}")
        if brk.get("callers"):
            print(f"    callers ({len(brk['callers'])}):")
            for c in brk["callers"]:
                print(f"      {c['name']} — {c['file']} (confidence={c['confidence']:.2f})")
    return 0


def cmd_graph_suggest_scope(args: argparse.Namespace) -> int:
    from scripts.context.workflow import suggest_scope

    repo = getattr(args, "repo", None) or "."
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else []
    related_files = [f.strip() for f in args.files.split(",")] if getattr(args, "files", None) else []

    result = suggest_scope(repo, keywords=keywords, related_files=related_files)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    suggestions = result.get("suggestions", [])
    if not suggestions:
        print("No scope suggestions found.")
        return 0

    print(f"{'Path':<50} {'Reason':<35} {'Confidence'}")
    print("-" * 95)
    for s in suggestions:
        flag = " (low)" if s.get("low_confidence") else ""
        print(f"{s['path']:<50} {s['reason']:<35} {s['confidence']:.2f}{flag}")
    return 0


def cmd_graph_enrich(args: argparse.Namespace) -> int:
    from scripts.context.workflow import enrich_context

    repo = getattr(args, "repo", None) or "."
    keywords = [k.strip() for k in args.keywords.split(",")]

    result = enrich_context(repo, keywords=keywords)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    related = result.get("related_code", [])
    if not related:
        print("No related code found.")
        return 0

    # Group by relationship type
    by_rel: dict[str, list] = {}
    for r in related:
        by_rel.setdefault(r["relationship"], []).append(r)

    for rel_type, items in sorted(by_rel.items()):
        print(f"\n{rel_type.upper()} ({len(items)}):")
        for item in items:
            print(f"  {item['name']:<30} {item['label']:<12} {item['path']}")

    arch = result.get("architecture", {})
    print(f"\nArchitecture: {arch.get('communities_hint', 0)} files touched")
    return 0


def cmd_graph_validate_scope(args: argparse.Namespace) -> int:
    from scripts.context.workflow import validate_scope

    repo = getattr(args, "repo", None) or "."
    declared = [f.strip() for f in args.declared.split(",")]
    changed = [f.strip() for f in args.changed.split(",")] if getattr(args, "changed", None) else None

    result = validate_scope(repo, declared_files=declared, changed_files=changed)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    status = "WITHIN SCOPE" if result["within_scope"] else "SCOPE VIOLATION"
    print(f"Status: {status}")
    if result["violations"]:
        print(f"\nViolations ({len(result['violations'])}):")
        for v in result["violations"]:
            print(f"  - {v['path']}: {v['reason']}")
    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  - {w['path']} (confidence: {w['confidence']:.2f}, low)")
    return 0


def cmd_costs(args: argparse.Namespace) -> int:
    if args.project_slug:
        from scripts.memory.costs import summarize_project_costs
        summary = summarize_project_costs(args.project_slug)
        print(f"Project: {summary['project']}")
        print(f"  Input tokens:         {summary['total_input_tokens']:,}")
        print(f"  Output tokens:        {summary['total_output_tokens']:,}")
        print(f"  Cache read tokens:    {summary['total_cache_read_tokens']:,}")
        print(f"  Cache creation tokens:{summary['total_cache_creation_tokens']:,}")
        print(f"  Estimated cost (USD): ${summary['total_estimated_cost_usd']:.4f}")
        if summary["sessions"]:
            print(f"  Sessions ({len(summary['sessions'])}):")
            for s in summary["sessions"]:
                print(f"    {s['path']}  model={s['model']}  tokens={s['tokens']:,}  cost=${s['cost_usd']:.4f}")
    elif args.feature:
        root = _root()
        summary = get_cost_summary(args.feature, root=root)
        print(f"Feature: {summary['feature_slug']}")
        print(f"  Total tokens:     {summary['total_tokens']:,}")
        print(f"  Total cost (USD): ${summary['total_cost_usd']:.4f}")
        print(f"  Events recorded:  {summary['event_count']}")
    else:
        print("Specify --feature or --project-slug")
        return 1
    return 0


def cmd_cost_record(args: argparse.Namespace) -> int:
    from scripts.memory.costs import parse_transcript, estimate_cost
    session_path = Path(args.session_path)
    if not session_path.exists():
        print(f"Error: {session_path} not found", file=sys.stderr)
        return 1
    usage = parse_transcript(session_path)
    cost = estimate_cost(usage)
    record_cost_event(
        args.issue_id,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cache_tokens=usage.cache_read_tokens + usage.cache_creation_tokens,
        model=usage.model,
        cost_usd=cost,
        root=_root(),
    )
    print(f"Recorded cost event for {args.issue_id}: "
          f"tokens={usage.input_tokens + usage.output_tokens:,}  "
          f"cost=${cost:.4f}  model={usage.model}")
    return 0


def cmd_graph_viz(args: argparse.Namespace) -> int:
    """Generate a graph visualization in Mermaid or DOT format."""
    from scripts.context import ContextGraph

    repo = getattr(args, "repo", None) or "."
    graph = ContextGraph(repo_path=repo)
    try:
        scope = getattr(args, "scope", "full")
        center = getattr(args, "center", None)
        depth = getattr(args, "depth", 3)
        fmt = getattr(args, "format", "mermaid")

        try:
            output = graph.visualize(scope=scope, center=center, depth=depth, format=fmt)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        print(output)
    finally:
        graph.close()
    return 0


def cmd_graph_prioritize(args: argparse.Namespace) -> int:
    """Rank files by graph proximity from focal symbols."""
    from scripts.context.workflow import prioritize_context

    repo = getattr(args, "repo", None) or "."
    symbols_arg = getattr(args, "symbols", None)
    focal_symbols = [s.strip() for s in symbols_arg.split(",")] if symbols_arg else []
    max_files = getattr(args, "max_files", 20)

    result = prioritize_context(repo, focal_symbols=focal_symbols, max_files=max_files)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    ranked = result.get("ranked_files", [])
    if not ranked:
        print("No prioritized files found.")
        return 0

    print(f"{'File':<55} {'Distance':<10} {'Reason'}")
    print("-" * 90)
    for entry in ranked:
        print(f"{entry['path']:<55} {entry['distance']:<10} {entry['reason']}")
    return 0


def cmd_graph_test_coverage(args: argparse.Namespace) -> int:
    """Report test coverage by walking CALLS edges from test file symbols."""
    from scripts.context.workflow import test_coverage_report

    repo = getattr(args, "repo", None) or "."
    result = test_coverage_report(repo)

    if getattr(args, "json", False):
        print(json.dumps(result))
        return 0

    if not result.get("enabled"):
        print(f"Graph unavailable: {result.get('error', 'unknown')}", file=sys.stderr)
        return 1

    summary = result.get("summary", {})
    total = summary.get("total_symbols", 0)
    covered = summary.get("covered", 0)
    uncovered = summary.get("uncovered", 0)
    pct = summary.get("coverage_pct", 0.0)

    print(f"Test coverage: {covered}/{total} symbols ({pct:.1f}%)")
    print(f"  Covered:   {covered}")
    print(f"  Uncovered: {uncovered}")

    by_file = result.get("coverage_by_file", {})
    if by_file:
        print("\nPer file:")
        for fpath, counts in sorted(by_file.items()):
            fc = len(counts.get("covered", []))
            fu = len(counts.get("uncovered", []))
            ftotal = fc + fu
            file_pct = (fc / ftotal * 100.0) if ftotal > 0 else 0.0
            print(f"  {fpath:<50} {fc}/{ftotal} ({file_pct:.0f}%)")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="cnogo Memory Engine CLI",
        prog="workflow_memory",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # init
    sub.add_parser("init", help="Initialize memory engine")

    # create
    p = sub.add_parser("create", help="Create a new issue")
    p.add_argument("title", help="Issue title")
    p.add_argument("--type", default="task",
                   choices=["epic", "task", "subtask", "bug", "quick", "background"])
    p.add_argument("--parent", help="Parent issue ID")
    p.add_argument("--feature", help="Feature slug")
    p.add_argument("--plan", help="Plan number")
    p.add_argument("--priority", type=int, default=2, choices=range(5))
    p.add_argument("--labels", help="Comma-separated labels")
    p.add_argument("--description", help="Description")
    p.add_argument("--metadata", help="JSON metadata")
    p.add_argument("--actor", default="claude")
    p.add_argument("--json", action="store_true")

    # show
    p = sub.add_parser("show", help="Show issue details")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--json", action="store_true")

    # update
    p = sub.add_parser("update", help="Update issue fields")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--title", help="New title")
    p.add_argument("--description", help="New description")
    p.add_argument("--priority", type=int, choices=range(5))
    p.add_argument("--metadata", help="JSON metadata to merge")
    p.add_argument("--comment", help="Add a comment")
    p.add_argument("--actor", default="claude")

    # claim
    p = sub.add_parser("claim", help="Claim an issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--actor", default="claude")

    # release
    p = sub.add_parser("release", help="Release an in-progress issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--actor", default="leader")
    p.add_argument("--json", action="store_true")

    # close
    p = sub.add_parser("close", help="Close an issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--reason", default="completed",
                   choices=["completed", "shipped", "superseded", "wontfix", "cancelled"])
    p.add_argument("--comment", help="Closing comment")
    p.add_argument("--actor", default="claude")

    # report-done
    p = sub.add_parser("report-done", help="Worker reports task done")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--actor", required=True, help="Actor name")
    p.add_argument("--outputs", help="Optional JSON outputs string")

    # takeover
    p = sub.add_parser("takeover", help="Leader takeover/reassignment for a task")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--to", required=True, dest="to_actor", help="Replacement actor")
    p.add_argument("--reason", required=True, help="Why task was taken over")
    p.add_argument("--actor", default="leader")
    p.add_argument("--json", action="store_true")

    # stalled
    p = sub.add_parser("stalled", help="List stale in-progress tasks")
    p.add_argument("--feature", help="Feature slug filter")
    p.add_argument("--minutes", type=int, help="Stale threshold in minutes")
    p.add_argument("--json", action="store_true")

    # verify-close
    p = sub.add_parser("verify-close", help="Leader verifies and closes a task")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--reason", default="completed")
    p.add_argument("--actor", default="claude")

    # reopen
    p = sub.add_parser("reopen", help="Reopen a closed issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--actor", default="claude")

    # ready
    p = sub.add_parser("ready", help="List ready issues")
    p.add_argument("--feature", help="Filter by feature slug")
    p.add_argument("--label", help="Filter by label")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")

    # list
    p = sub.add_parser("list", help="List issues")
    p.add_argument("--status", choices=["open", "in_progress", "closed"])
    p.add_argument("--type", choices=["epic", "task", "subtask", "bug", "quick", "background"])
    p.add_argument("--feature", help="Filter by feature slug")
    p.add_argument("--parent", help="Filter by parent issue ID")
    p.add_argument("--assignee", help="Filter by assignee")
    p.add_argument("--label", help="Filter by label")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--json", action="store_true")

    # stats
    p = sub.add_parser("stats", help="Show statistics")
    p.add_argument("--json", action="store_true")

    # dep-add
    p = sub.add_parser("dep-add", help="Add a dependency")
    p.add_argument("issue", help="Blocked issue ID")
    p.add_argument("depends_on", help="Blocker issue ID")
    p.add_argument("--type", default="blocks",
                   choices=["blocks", "parent-child", "related", "discovered-from"])
    p.add_argument("--actor", default="claude")

    # dep-remove
    p = sub.add_parser("dep-remove", help="Remove a dependency")
    p.add_argument("issue", help="Issue ID")
    p.add_argument("depends_on", help="Dependency to remove")
    p.add_argument("--actor", default="claude")

    # blockers
    p = sub.add_parser("blockers", help="Show blockers")
    p.add_argument("id", help="Issue ID")

    # blocks
    p = sub.add_parser("blocks", help="Show what issue blocks")
    p.add_argument("id", help="Issue ID")

    # export
    sub.add_parser("export", help="Export to JSONL")

    # import
    sub.add_parser("import", help="Import from JSONL")

    # sync
    p = sub.add_parser("sync", help="Export JSONL memory state")
    p.add_argument("--stage", action="store_true", help="Also stage .cnogo/issues.jsonl for git")

    # prime
    p = sub.add_parser("prime", help="Generate context summary")
    p.add_argument("--feature", help="Feature slug to focus on (auto-detect if omitted)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--verbose", action="store_true", help="Include file hints and restore commands")

    # checkpoint
    p = sub.add_parser("checkpoint", help="Generate compact objective/progress checkpoint")
    p.add_argument("--feature", help="Feature slug (auto-detect if omitted)")
    p.add_argument("--limit", type=int, default=3)

    # history
    p = sub.add_parser("history", help="Show event history for an issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--limit", type=int, default=10)

    # phase-get
    p = sub.add_parser("phase-get", help="Get current workflow phase for a feature")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--json", action="store_true")

    # phase-set
    p = sub.add_parser("phase-set", help="Set workflow phase for a feature")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("phase", choices=["discuss", "plan", "implement", "review", "ship"])
    p.add_argument("--json", action="store_true")

    # run-create
    p = sub.add_parser("run-create", help="Create or resume a durable delivery run for a feature plan")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("plan", help="Plan number")
    p.add_argument("--mode", choices=["auto", "serial", "team"], default="auto")
    p.add_argument("--run-id", help="Explicit run ID")
    p.add_argument("--actor", default="claude")
    p.add_argument("--branch", help="Override branch recorded on the run")
    p.add_argument("--no-resume-latest", action="store_true", help="Force creation of a fresh run instead of resuming latest")
    p.add_argument("--json", action="store_true")

    # run-list
    p = sub.add_parser("run-list", help="List delivery runs across features")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--status", action="append", choices=["created", "active", "blocked", "ready_for_review", "completed", "failed", "cancelled"])
    p.add_argument("--mode", choices=["serial", "team"])
    p.add_argument("--needs-attention", action="store_true", help="Only show runs currently present in the attention queue")
    p.add_argument("--all", action="store_true", help="Include terminal runs")
    p.add_argument("--json", action="store_true")

    # run-show
    p = sub.add_parser("run-show", help="Show a delivery run for a feature")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--json", action="store_true")

    # work-show
    p = sub.add_parser("work-show", help="Show the feature-level Work Order")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--json", action="store_true")

    # work-list
    p = sub.add_parser("work-list", help="List Work Orders across features")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--needs-attention", action="store_true", help="Only show Work Orders with attention items")
    p.add_argument("--json", action="store_true")

    # work-sync
    p = sub.add_parser("work-sync", help="Sync Work Orders from current feature artifacts and runs")
    p.add_argument("feature", nargs="?", help="Optional feature slug to sync")
    p.add_argument("--json", action="store_true")

    # work-next
    p = sub.add_parser("work-next", help="Show the next feature-level action for a Work Order")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--json", action="store_true")

    # plan-auto
    p = sub.add_parser("plan-auto", help="Generate or reuse a deterministic plan for a ready feature")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--plan", help="Optional plan number to create or reuse")
    p.add_argument("--profile", help="Override the resolved workflow profile")
    p.add_argument("--force", action="store_true", help="Regenerate the target plan instead of reusing it")
    p.add_argument("--no-run", action="store_true", help="Do not create or resume a Delivery Run after planning")
    p.add_argument("--json", action="store_true")

    # lane-show
    p = sub.add_parser("lane-show", help="Show one feature lane")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--json", action="store_true")

    # lane-list
    p = sub.add_parser("lane-list", help="List feature lanes across the repo")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--all", action="store_true", help="Include completed or released lanes")
    p.add_argument("--json", action="store_true")

    # dispatch-ready
    p = sub.add_parser("dispatch-ready", help="Lease ready features into feature lanes")
    p.add_argument("--feature", help="Specific ready feature to dispatch")
    p.add_argument("--owner", default="dispatcher", help="Lease owner to record on the lane")
    p.add_argument("--json", action="store_true")

    # feedback-sync
    p = sub.add_parser("feedback-sync", help="Sync downstream feature feedback into SHAPE.json inboxes")
    p.add_argument("--feature", help="Specific feature slug to sync")
    p.add_argument("--json", action="store_true")

    # initiative-show
    p = sub.add_parser("initiative-show", help="Show initiative rollup for a shape")
    p.add_argument("slug", help="Initiative slug (matches ideas directory name)")
    p.add_argument("--json", action="store_true")

    # initiative-list
    p = sub.add_parser("initiative-list", help="List all initiatives with SHAPE.json")
    p.add_argument("--json", action="store_true")

    # initiative-current
    p = sub.add_parser("initiative-current", help="Show initiative context for the current or specified feature")
    p.add_argument("--feature", help="Feature slug to inspect instead of inferring from branch")
    p.add_argument("--branch", help="Override branch name used for feature inference")
    p.add_argument("--json", action="store_true")

    # run-watch
    p = sub.add_parser("run-watch", help="Inspect delivery-run health and next actions")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--stale-minutes", type=int, help="Idle threshold for active/merge verification findings")
    p.add_argument("--review-stale-minutes", type=int, help="Ready-for-review stale threshold")
    p.add_argument("--all", action="store_true", help="Include terminal runs")
    p.add_argument("--no-write", action="store_true", help="Do not persist latest watch artifacts")
    p.add_argument("--json", action="store_true")

    # run-watch-status
    p = sub.add_parser("run-watch-status", help="Show recurring watch schedule status and patrol state")
    p.add_argument("--json", action="store_true")

    # run-watch-tick
    p = sub.add_parser("run-watch-tick", help="Run the recurring watch patrol only when due")
    p.add_argument("--stale-minutes", type=int, help="Idle threshold override for active/merge verification findings")
    p.add_argument("--review-stale-minutes", type=int, help="Ready-for-review stale threshold override")
    p.add_argument("--all", action="store_true", help="Include terminal runs")
    p.add_argument("--force", action="store_true", help="Run even when the patrol is not due or watch is disabled")
    p.add_argument("--json", action="store_true")

    # run-watch-patrol
    p = sub.add_parser("run-watch-patrol", help="Refresh watch artifacts, archive a patrol snapshot, and show deltas")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--stale-minutes", type=int, help="Idle threshold for active/merge verification findings")
    p.add_argument("--review-stale-minutes", type=int, help="Ready-for-review stale threshold")
    p.add_argument("--all", action="store_true", help="Include terminal runs")
    p.add_argument("--json", action="store_true")

    # run-watch-history
    p = sub.add_parser("run-watch-history", help="Show archived watch patrol snapshots")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--json", action="store_true")

    # scheduler-status
    p = sub.add_parser("scheduler-status", help="Show hybrid scheduler status")
    p.add_argument("--json", action="store_true")

    # scheduler-run-once
    p = sub.add_parser("scheduler-run-once", help="Run due scheduler jobs once")
    p.add_argument("--job", action="append", choices=list(SCHEDULER_JOB_NAMES), help="Restrict to one or more scheduler jobs")
    p.add_argument("--force", action="store_true", help="Run even when the scheduler is not due")
    p.add_argument("--json", action="store_true")

    # scheduler-start
    p = sub.add_parser("scheduler-start", help="Start the optional local scheduler supervisor")
    p.add_argument("--json", action="store_true")

    # scheduler-stop
    p = sub.add_parser("scheduler-stop", help="Stop the local scheduler supervisor")
    p.add_argument("--json", action="store_true")

    # internal scheduler worker
    sub.add_parser("_scheduler-worker", help=argparse.SUPPRESS)

    # run-attention
    p = sub.add_parser("run-attention", help="Show or refresh the persisted needs-attention queue")
    p.add_argument("--feature", help="Feature slug to filter")
    p.add_argument("--stale-minutes", type=int, help="Idle threshold for active/merge verification findings")
    p.add_argument("--review-stale-minutes", type=int, help="Ready-for-review stale threshold")
    p.add_argument("--all", action="store_true", help="Include terminal runs when refreshing")
    p.add_argument("--refresh", action="store_true", help="Recompute watch findings before showing the queue")
    p.add_argument("--no-write", action="store_true", help="Do not persist refreshed attention artifacts")
    p.add_argument("--severity", action="append", choices=["warn", "fail"], help="Filter queue items by severity")
    p.add_argument("--kind", action="append", help="Filter queue items by finding kind")
    p.add_argument("--limit", type=int, help="Limit the number of returned attention items")
    p.add_argument("--json", action="store_true")

    # run-refresh
    p = sub.add_parser("run-refresh", help="Refresh delivery-run task frontier and save it")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--json", action="store_true")

    # run-next
    p = sub.add_parser("run-next", help="Show the next ready tasks for a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--json", action="store_true")

    # run-task-prompt
    p = sub.add_parser("run-task-prompt", help="Render a stable implementer prompt for one Delivery Run task")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("task_index", type=int, help="Plan task index")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--actor", default="implementer", help="Actor name to embed in memory commands")
    p.add_argument("--json", action="store_true")

    # run-task-set
    p = sub.add_parser("run-task-set", help="Update one delivery-run task status")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("task_index", type=int, help="Plan task index")
    p.add_argument("status", choices=sorted(DELIVERY_TASK_STATUSES))
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--assignee")
    p.add_argument("--branch")
    p.add_argument("--worktree-path")
    p.add_argument("--note")
    p.add_argument("--json", action="store_true")

    # run-task-begin
    p = sub.add_parser("run-task-begin", help="Claim memory ownership and mark a task in_progress")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("task_index", type=int, help="Plan task index")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--actor", default="implementer")
    p.add_argument("--branch")
    p.add_argument("--worktree-path")
    p.add_argument("--skip-memory", action="store_true")
    p.add_argument("--note")
    p.add_argument("--json", action="store_true")

    # run-task-complete
    p = sub.add_parser("run-task-complete", help="Report memory completion and mark a task done")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("task_index", type=int, help="Plan task index")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--actor", default="implementer")
    p.add_argument("--skip-memory", action="store_true")
    p.add_argument("--command", action="append", dest="verify_command", default=[])
    p.add_argument("--note")
    p.add_argument("--json", action="store_true")

    # run-task-fail
    p = sub.add_parser("run-task-fail", help="Mark a task failed on the Delivery Run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("task_index", type=int, help="Plan task index")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--actor", default="implementer")
    p.add_argument("--error")
    p.add_argument("--note")
    p.add_argument("--json", action="store_true")

    # run-plan-verify
    p = sub.add_parser("run-plan-verify", help="Record plan verification outcome for a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("result", choices=["pass", "fail"])
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument(
        "--command",
        action="append",
        dest="verify_command",
        default=[],
        help="Verification command that was run",
    )
    p.add_argument(
        "--use-plan-verify",
        action="store_true",
        help="Also record planVerify[] commands from the linked plan contract",
    )
    p.add_argument(
        "--command-file",
        help="Read additional verification commands from a newline-delimited file",
    )
    p.add_argument("--note", help="Optional note to store with verification state")
    p.add_argument("--json", action="store_true")

    # run-review-ready
    p = sub.add_parser("run-review-ready", help="Finalize integration state and mark a Delivery Run ready for review")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--integration-status", choices=["merged", "cleaned"], help="Explicit integration status to record before recomputing review readiness")
    p.add_argument("--note", help="Optional note to append to review readiness")
    p.add_argument("--json", action="store_true")

    # run-review-start
    p = sub.add_parser("run-review-start", help="Start or resume review state for a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--reviewer", action="append", default=[], help="Reviewer agent/user to record")
    p.add_argument("--automated-verdict", choices=sorted(DELIVERY_REVIEW_VERDICTS - {'pending'}))
    p.add_argument("--note", help="Optional note to attach to review state")
    p.add_argument("--json", action="store_true")

    # run-review-stage-set
    p = sub.add_parser("run-review-stage-set", help="Update one review stage on a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("stage", choices=list(DELIVERY_REVIEW_STAGES))
    p.add_argument("status", choices=sorted(DELIVERY_REVIEW_STAGE_STATUSES))
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--finding", action="append", default=[], help="Finding entry to store on the stage")
    p.add_argument("--evidence", action="append", default=[], help="Evidence entry to store on the stage")
    p.add_argument("--note", action="append", default=[], help="Stage note to store")
    p.add_argument("--json", action="store_true")

    # run-review-verdict
    p = sub.add_parser("run-review-verdict", help="Set the final review verdict on a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("verdict", choices=sorted(DELIVERY_REVIEW_VERDICTS))
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--note", help="Optional note to append to review state")
    p.add_argument("--json", action="store_true")

    # run-review-sync
    p = sub.add_parser("run-review-sync", help="Sync a delivery run from REVIEW.json")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--json", action="store_true")

    # run-ship-start
    p = sub.add_parser("run-ship-start", help="Start ship state for a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--note", help="Optional note to attach to ship state")
    p.add_argument("--json", action="store_true")

    # run-ship-complete
    p = sub.add_parser("run-ship-complete", help="Record successful ship completion on a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("commit", nargs="?", default=None, help="Commit SHA (auto-inferred from HEAD if omitted)")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--branch", help="Branch shipped for this run")
    p.add_argument("--pr-url", help="PR URL created for this ship")
    p.add_argument("--note", help="Optional note to attach to ship state")
    p.add_argument("--json", action="store_true")

    # run-ship-draft
    p = sub.add_parser("run-ship-draft", help="Compute ship draft for a feature (commit surface, PR body, etc.)")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--json", action="store_true")

    # verify-import
    p = sub.add_parser("verify-import", help="Verify that a Python module and optional symbols import cleanly")
    p.add_argument("module", help="Module path to import")
    p.add_argument("symbol", nargs="*", help="Optional symbols that must exist on the imported module")
    p.add_argument("--json", action="store_true")

    # run-ship-fail
    p = sub.add_parser("run-ship-fail", help="Record a failed ship attempt on a delivery run")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--error", help="Error message or summary for the failed ship")
    p.add_argument("--note", help="Optional note to attach to ship state")
    p.add_argument("--json", action="store_true")

    # run-sync-session
    p = sub.add_parser("run-sync-session", help="Sync a delivery run from the active worktree session")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--run-id", help="Explicit run ID (defaults to latest)")
    p.add_argument("--json", action="store_true")

    # graph
    p = sub.add_parser("graph", help="Show dependency graph")
    p.add_argument("feature", help="Feature slug")

    # session-status
    p = sub.add_parser("session-status", help="Show active worktree session")
    p.add_argument("--json", action="store_true")

    # session-apply
    p = sub.add_parser("session-apply", help="Apply active worktree session outputs into the leader branch")
    p.add_argument("--json", action="store_true")

    # session-merge
    p = sub.add_parser("session-merge", help="Merge active worktree session branches")
    p.add_argument("--json", action="store_true")

    # session-cleanup
    sub.add_parser("session-cleanup", help="Cleanup active worktree session worktrees")

    # session-reconcile
    p = sub.add_parser("session-reconcile", help="Fix orphaned issues after compaction")
    p.add_argument("--json", action="store_true")

    # profile-suggest
    p = sub.add_parser("profile-suggest", help="Suggest the best profile for a feature or plan")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("--plan", help="Plan number to inspect")
    p.add_argument("--json", action="store_true")

    # profile-list
    p = sub.add_parser("profile-list", help="List available profiles from builtins and repo-local catalog")
    p.add_argument("--json", action="store_true")

    # profile-init
    p = sub.add_parser("profile-init", help="Create a new repo-local profile scaffold")
    p.add_argument("name", help="Profile slug")
    p.add_argument("--base", help="Base profile to copy policy from", default="feature-delivery")
    p.add_argument("--description", help="Optional description to seed the scaffold")
    p.add_argument("--force", action="store_true", help="Overwrite an existing profile file")
    p.add_argument("--json", action="store_true")

    # profile-stamp
    p = sub.add_parser("profile-stamp", help="Stamp a profile onto a plan and rerender markdown")
    p.add_argument("feature", help="Feature slug")
    p.add_argument("plan", help="Plan number")
    p.add_argument("--profile", help="Explicit profile name (defaults to the suggestion)")
    p.add_argument("--force", action="store_true", help="Replace an existing stamped profile")
    p.add_argument("--json", action="store_true")

    # costs
    p = sub.add_parser("costs", help="Show cost tracking summary")
    p.add_argument("--feature", help="Feature slug to query recorded cost events")
    p.add_argument("--project-slug", help="Claude Code project slug to parse transcripts")

    # cost-record
    p = sub.add_parser("cost-record", help="Parse transcript and record cost event")
    p.add_argument("issue_id", help="Issue ID to attach cost event to")
    p.add_argument("session_path", help="Path to Claude Code session JSONL transcript")

    # graph-index
    p = sub.add_parser("graph-index", help="Index the codebase into the context graph")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--watch", action="store_true", help="Watch for file changes and re-index automatically")

    # graph-query
    p = sub.add_parser("graph-query", help="Search for symbols by name in the context graph")
    p.add_argument("name", help="Symbol name to search for")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-impact
    p = sub.add_parser("graph-impact", help="Analyze change impact for a file")
    p.add_argument("file_path", help="File path to analyze")
    p.add_argument("--depth", type=int, default=3, help="Max BFS depth (default: 3)")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-context
    p = sub.add_parser("graph-context", help="Show context neighborhood for a node")
    p.add_argument("node_id", help="Node ID to inspect")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-dead
    p = sub.add_parser("graph-dead", help="Detect dead (unreferenced) symbols in the context graph")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-coupling
    p = sub.add_parser("graph-coupling", help="Detect structural coupling between symbols (Jaccard similarity)")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--strength", type=float, default=0.5, help="Minimum coupling strength threshold (default: 0.5)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-blast-radius
    p = sub.add_parser("graph-blast-radius", help="Compute blast-radius impact for changed files")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--files", help="Comma-separated file paths (default: auto-detect via git diff)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-communities
    p = sub.add_parser("graph-communities", help="Detect communities of tightly-coupled symbols via label propagation")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--min-size", type=int, default=2, help="Minimum community size (default: 2)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-flows
    p = sub.add_parser("graph-flows", help="Trace execution flows from entry points through CALLS edges")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--max-depth", type=int, default=10, help="Maximum BFS depth (default: 10)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-search
    p = sub.add_parser("graph-search", help="Full-text search over symbol names, signatures, and docstrings")
    p.add_argument("query", help="Search query string")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--limit", type=int, default=20, help="Maximum number of results (default: 20)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-status
    p = sub.add_parser("graph-status", help="Show graph status: existence, counts, and staleness")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-suggest-scope
    p = sub.add_parser("graph-suggest-scope", help="Suggest file scope for a plan based on keyword search and impact analysis")
    p.add_argument("--keywords", help="Comma-separated keywords to search for")
    p.add_argument("--files", help="Comma-separated related file paths for impact analysis")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--limit", type=int, default=20, help="Maximum results per keyword (default: 20)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-validate-scope
    p = sub.add_parser("graph-validate-scope", help="Validate that changes stay within declared file scope via blast-radius analysis")
    p.add_argument("--declared", required=True, help="Comma-separated declared file paths")
    p.add_argument("--changed", help="Comma-separated changed file paths (default: same as declared)")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-enrich
    p = sub.add_parser("graph-enrich", help="Discover related code and architecture for context enrichment")
    p.add_argument("--keywords", required=True, help="Comma-separated keywords to search for")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--limit", type=int, default=20, help="Maximum results per keyword (default: 20)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-contract-check
    p = sub.add_parser("graph-contract-check", help="Detect API contract (signature) breaks in changed files and find affected callers")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--files", help="Comma-separated file paths (default: auto-detect via git diff)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-prioritize
    p = sub.add_parser("graph-prioritize", help="Rank files by graph proximity from focal symbols to prioritize context")
    p.add_argument("--symbols", help="Comma-separated focal symbol names to use as BFS seeds")
    p.add_argument("--max-files", type=int, default=20, dest="max_files",
                   help="Maximum number of files to return (default: 20)")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-test-coverage
    p = sub.add_parser("graph-test-coverage", help="Report test coverage by walking CALLS edges from test file symbols")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--json", action="store_true", help="Output as JSON")

    # graph-viz
    p = sub.add_parser("graph-viz", help="Generate graph visualization in Mermaid or DOT format")
    p.add_argument("--repo", help="Repository root path (default: cwd)")
    p.add_argument("--format", default="mermaid", choices=["mermaid", "dot"],
                   help="Output format: mermaid or dot (default: mermaid)")
    p.add_argument("--scope", default="full", choices=["file", "module", "full"],
                   help="Subgraph scope: file, module, or full (default: full)")
    p.add_argument("--depth", type=int, default=3,
                   help="Maximum BFS depth from center node (default: 3)")
    p.add_argument("--center", default=None,
                   help="Center node ID for BFS (required for file/module scope)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check initialization for non-init commands
    # 'costs --project-slug' reads transcripts only, no DB needed
    # 'graph-*' commands use context graph DB, not memory engine DB
    _graph_cmds = {"graph-index", "graph-query", "graph-impact", "graph-context", "graph-dead", "graph-coupling", "graph-blast-radius", "graph-communities", "graph-flows", "graph-search", "graph-status", "graph-suggest-scope", "graph-validate-scope", "graph-enrich", "graph-contract-check", "graph-prioritize", "graph-test-coverage", "graph-viz"}

    if args.command in _graph_cmds:
        _ensure_graph_venv()

    _needs_db = not (args.command == "costs" and getattr(args, "project_slug", None))
    _needs_db = _needs_db and args.command not in _graph_cmds
    _needs_db = _needs_db and args.command not in {
        "_scheduler-worker",
        "profile-suggest",
        "profile-stamp",
        "profile-list",
        "profile-init",
        "scheduler-status",
        "scheduler-start",
        "scheduler-stop",
        "scheduler-run-once",
        "run-watch-status",
        "run-watch-tick",
        "run-watch-patrol",
        "run-watch-history",
        "run-attention",
        "work-show",
        "work-list",
        "work-sync",
        "work-next",
        "plan-auto",
        "lane-show",
        "lane-list",
        "dispatch-ready",
        "feedback-sync",
        "initiative-show",
        "initiative-list",
        "initiative-current",
        "run-ship-draft",
        "verify-import",
        "session-status",
        "session-cleanup",
    }
    if args.command != "init" and _needs_db and not is_initialized(_root()):
        print(
            "Memory engine not initialized. Run: "
            "python3 .cnogo/scripts/workflow_memory.py init",
            file=sys.stderr,
        )
        return 1

    dispatch = {
        "init": cmd_init,
        "create": cmd_create,
        "show": cmd_show,
        "update": cmd_update,
        "claim": cmd_claim,
        "release": cmd_release,
        "close": cmd_close,
        "report-done": cmd_report_done,
        "takeover": cmd_takeover,
        "stalled": cmd_stalled,
        "verify-close": cmd_verify_close,
        "reopen": cmd_reopen,
        "ready": cmd_ready,
        "list": cmd_list,
        "stats": cmd_stats,
        "dep-add": cmd_dep_add,
        "dep-remove": cmd_dep_remove,
        "blockers": cmd_blockers,
        "blocks": cmd_blocks,
        "export": cmd_export,
        "import": cmd_import,
        "sync": cmd_sync_fn,
        "prime": cmd_prime,
        "checkpoint": cmd_checkpoint,
        "history": cmd_history,
        "phase-get": cmd_phase_get,
        "phase-set": cmd_phase_set,
        "run-create": cmd_run_create,
        "run-list": cmd_run_list,
        "run-show": cmd_run_show,
        "work-show": cmd_work_show,
        "work-list": cmd_work_list,
        "work-sync": cmd_work_sync,
        "work-next": cmd_work_next,
        "plan-auto": cmd_plan_auto,
        "lane-show": cmd_lane_show,
        "lane-list": cmd_lane_list,
        "dispatch-ready": cmd_dispatch_ready,
        "feedback-sync": cmd_feedback_sync,
        "initiative-show": cmd_initiative_show,
        "initiative-list": cmd_initiative_list,
        "initiative-current": cmd_initiative_current,
        "run-watch": cmd_run_watch,
        "run-watch-status": cmd_run_watch_status,
        "run-watch-tick": cmd_run_watch_tick,
        "run-watch-patrol": cmd_run_watch_patrol,
        "run-watch-history": cmd_run_watch_history,
        "scheduler-status": cmd_scheduler_status,
        "scheduler-run-once": cmd_scheduler_run_once,
        "scheduler-start": cmd_scheduler_start,
        "scheduler-stop": cmd_scheduler_stop,
        "_scheduler-worker": cmd_scheduler_worker,
        "run-attention": cmd_run_attention,
        "run-refresh": cmd_run_refresh,
        "run-next": cmd_run_next,
        "run-task-prompt": cmd_run_task_prompt,
        "run-task-set": cmd_run_task_set,
        "run-task-begin": cmd_run_task_begin,
        "run-task-complete": cmd_run_task_complete,
        "run-task-fail": cmd_run_task_fail,
        "run-plan-verify": cmd_run_plan_verify,
        "run-review-ready": cmd_run_review_ready,
        "run-review-start": cmd_run_review_start,
        "run-review-stage-set": cmd_run_review_stage_set,
        "run-review-verdict": cmd_run_review_verdict,
        "run-review-sync": cmd_run_review_sync,
        "run-ship-start": cmd_run_ship_start,
        "run-ship-complete": cmd_run_ship_complete,
        "run-ship-fail": cmd_run_ship_fail,
        "run-ship-draft": cmd_run_ship_draft,
        "verify-import": cmd_verify_import,
        "run-sync-session": cmd_run_sync_session,
        "graph": cmd_graph,
        "session-status": cmd_session_status,
        "session-apply": cmd_session_apply,
        "session-merge": cmd_session_merge,
        "session-cleanup": cmd_session_cleanup,
        "session-reconcile": cmd_session_reconcile,
        "profile-suggest": cmd_profile_suggest,
        "profile-list": cmd_profile_list,
        "profile-init": cmd_profile_init,
        "profile-stamp": cmd_profile_stamp,
        "costs": cmd_costs,
        "cost-record": cmd_cost_record,
        "graph-index": cmd_graph_index,
        "graph-query": cmd_graph_query,
        "graph-impact": cmd_graph_impact,
        "graph-context": cmd_graph_context,
        "graph-dead": cmd_graph_dead,
        "graph-coupling": cmd_graph_coupling,
        "graph-blast-radius": cmd_graph_blast_radius,
        "graph-communities": cmd_graph_communities,
        "graph-flows": cmd_graph_flows,
        "graph-search": cmd_graph_search,
        "graph-status": cmd_graph_status,
        "graph-suggest-scope": cmd_graph_suggest_scope,
        "graph-validate-scope": cmd_graph_validate_scope,
        "graph-enrich": cmd_graph_enrich,
        "graph-contract-check": cmd_graph_contract_check,
        "graph-prioritize": cmd_graph_prioritize,
        "graph-test-coverage": cmd_graph_test_coverage,
        "graph-viz": cmd_graph_viz,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    if args.command not in {"_scheduler-worker", "scheduler-start", "scheduler-stop", "scheduler-run-once"}:
        try:
            scheduler_cfg = scheduler_settings_cfg(load_workflow_config(_root()))
            opportunistic = set(scheduler_cfg.get("opportunisticCommands", []))
            if args.command in opportunistic:
                run_scheduler_once(
                    force=False,
                    triggered_by=f"opportunistic:{args.command}",
                    root=_root(),
                )
        except Exception:
            pass

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
