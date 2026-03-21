#!/usr/bin/env python3
"""cnogo Memory Engine — Public API façade."""

from __future__ import annotations

from .api import (
    blockers,
    blocks,
    claim,
    close,
    create,
    dep_add,
    dep_remove,
    get_cost_summary,
    get_phase,
    init,
    is_initialized,
    list_issues,
    ready,
    record_cost_event,
    release,
    report_done,
    reopen,
    set_phase,
    show,
    stalled_tasks,
    stats,
    takeover_task,
    update,
    verify_and_close,
)
from .bridge import (
    detect_file_conflicts,
    generate_implement_prompt,
    generate_run_id,
    plan_to_task_descriptions,
    recommend_team_mode,
)
from .context import checkpoint, history, prime, show_graph
from .costs import parse_transcript, summarize_project_costs as cost_summary
from .reconcile import reconcile_session
from .reconcile_leader import reconcile
from .sync import export_jsonl, import_jsonl, sync
from .watchdog import check_stale_issues
from .worktree import (
    cleanup_session,
    create_session,
    get_conflict_context,
    load_session,
    merge_session,
    save_session,
)

__all__ = [
    "init",
    "is_initialized",
    "create",
    "show",
    "update",
    "claim",
    "close",
    "reopen",
    "release",
    "report_done",
    "verify_and_close",
    "takeover_task",
    "ready",
    "list_issues",
    "stats",
    "get_phase",
    "set_phase",
    "stalled_tasks",
    "dep_add",
    "dep_remove",
    "blockers",
    "blocks",
    "export_jsonl",
    "import_jsonl",
    "sync",
    "prime",
    "checkpoint",
    "history",
    "show_graph",
    "merge_session",
    "cleanup_session",
    "load_session",
    "create_session",
    "save_session",
    "get_conflict_context",
    "plan_to_task_descriptions",
    "generate_implement_prompt",
    "detect_file_conflicts",
    "recommend_team_mode",
    "generate_run_id",
    "reconcile_session",
    "record_cost_event",
    "get_cost_summary",
    "cost_summary",
    "parse_transcript",
    "check_stale_issues",
    "reconcile",
]
