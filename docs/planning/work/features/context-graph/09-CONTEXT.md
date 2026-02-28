# Context: context-graph 09 — Workflow Integration

> Wire the context graph into the daily workflow: fix review blast-radius, auto-index on /plan, PostCommit hook.

## Summary

Plans 01-08 built the full context graph engine (parser, storage, 10 phases, 8 CLI commands, 265 tests). But the graph is CLI-only — it doesn't participate in `/review` or `/plan` workflows automatically. Plan 09 closes this gap with the "triple trigger" design from CONTEXT.md.

## Decisions

### Bug Fix: `_graph_impact_section()` sys.path
- `workflow_checks_core.py:1319` imports `from scripts.context import ContextGraph` but `root` is not on `sys.path`
- Error: `"No module named 'scripts'"` in REVIEW.json impactAnalysis
- Fix: add `sys.path.insert(0, str(root))` before import (same pattern at lines 545, 1913)

### Workflow Integration: Auto-index on /plan
- When `/plan` runs, check if graph is stale (graph.db missing or files changed since last index)
- If stale, auto-index before partitioning work
- Gives planners coupling/community data for better task boundaries

### PostCommit Hook: Synchronous Reindex
- Add `post_commit_graph()` function to `workflow_hooks.py`
- Register PostToolUse hook in `.claude/settings.json` matching Bash commands containing `git commit`
- Runs synchronous incremental reindex (~1-3s, only changed files)
- Idempotent — safe to run multiple times

## Constraints
- Stdlib only
- Must not break existing hooks
- PostCommit hook must be idempotent
