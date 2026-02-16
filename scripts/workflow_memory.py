#!/usr/bin/env python3
"""CLI wrapper for the cnogo memory engine.

Usage:
    python3 scripts/workflow_memory.py <command> [options]

Commands:
    init                Initialize memory engine in .cnogo/
    create              Create a new issue
    show <id>           Show issue details
    update <id>         Update issue fields
    claim <id>          Claim an issue
    close <id>          Close an issue
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
    sync                Export + git add
    prime               Generate context summary
    checkpoint          Generate compact objective/progress checkpoint
    history <id>        Show recent event history for an issue
    phase-get <feature> Get current workflow phase for feature
    phase-set <feature> Set workflow phase for feature
    graph <feature>     Show dependency graph
    session-status      Show active worktree session status
    session-merge       Merge active worktree session branches
    session-cleanup     Cleanup active worktree session

No external dependencies. Python 3.9+ required.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure scripts/ is on the path when run directly
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.memory import (  # noqa: E402
    blocks,
    blockers,
    checkpoint,
    claim,
    cleanup_session,
    close,
    create,
    dep_add,
    dep_remove,
    export_jsonl,
    import_jsonl,
    init,
    is_initialized,
    history,
    list_issues,
    load_session,
    get_phase,
    merge_session,
    prime,
    ready,
    reopen,
    show,
    show_graph,
    stats,
    set_phase,
    sync,
    update,
)


def _root() -> Path:
    """Find repo root by walking up from cwd looking for .git."""
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / ".git").exists():
            return p
    return cwd


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
    sync(root)
    print("Synced: exported JSONL and staged for git")
    return 0


def cmd_prime(args: argparse.Namespace) -> int:
    root = _root()
    output = prime(limit=args.limit, verbose=args.verbose, root=root)
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
    root = _root()
    try:
        count = set_phase(args.feature, args.phase, root=root)
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
    if args.json:
        _print_json(session.to_dict() if session else {"session": None})
        return 0
    if not session:
        print("No active worktree session")
        return 0
    total = len(session.worktrees)
    done = sum(1 for w in session.worktrees if w.status in {"completed", "merged", "cleaned"})
    print(f"Feature: {session.feature}")
    print(f"Plan: {session.plan_number}")
    print(f"Phase: {session.phase}")
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
    payload = {
        "success": result.success,
        "merged": result.merged_indices,
        "conflictIndex": result.conflict_index,
        "conflictFiles": result.conflict_files,
        "error": result.error_message,
    }
    if args.json:
        _print_json(payload)
    else:
        if result.success:
            print(f"Merged tasks: {result.merged_indices}")
        else:
            print(f"Merge stopped at task {result.conflict_index}: {result.conflict_files}")
    return 0 if result.success else 1


def cmd_session_cleanup(args: argparse.Namespace) -> int:
    root = _root()
    session = load_session(root)
    if not session:
        print("No active worktree session")
        return 0
    cleanup_session(session, root)
    print("Worktrees cleaned")
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

    # close
    p = sub.add_parser("close", help="Close an issue")
    p.add_argument("id", help="Issue ID")
    p.add_argument("--reason", default="completed",
                   choices=["completed", "shipped", "superseded", "wontfix", "cancelled"])
    p.add_argument("--comment", help="Closing comment")
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
    sub.add_parser("sync", help="Export + git add")

    # prime
    p = sub.add_parser("prime", help="Generate context summary")
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

    # graph
    p = sub.add_parser("graph", help="Show dependency graph")
    p.add_argument("feature", help="Feature slug")

    # session-status
    p = sub.add_parser("session-status", help="Show active worktree session")
    p.add_argument("--json", action="store_true")

    # session-merge
    p = sub.add_parser("session-merge", help="Merge active worktree session branches")
    p.add_argument("--json", action="store_true")

    # session-cleanup
    sub.add_parser("session-cleanup", help="Cleanup active worktree session worktrees")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check initialization for non-init commands
    if args.command != "init" and not is_initialized(_root()):
        print(
            "Memory engine not initialized. Run: "
            "python3 scripts/workflow_memory.py init",
            file=sys.stderr,
        )
        return 1

    dispatch = {
        "init": cmd_init,
        "create": cmd_create,
        "show": cmd_show,
        "update": cmd_update,
        "claim": cmd_claim,
        "close": cmd_close,
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
        "graph": cmd_graph,
        "session-status": cmd_session_status,
        "session-merge": cmd_session_merge,
        "session-cleanup": cmd_session_cleanup,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
