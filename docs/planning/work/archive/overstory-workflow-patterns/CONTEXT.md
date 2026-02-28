# Context: Overstory Workflow Patterns

Adopt 4 patterns from the [Overstory](https://github.com/jayminwest/overstory) swarm orchestration system into cnogo.

## Scope

| Feature | Files | Effort |
|---------|-------|--------|
| Tiered merge resolution | `.cnogo/scripts/memory/worktree.py` | LOW |
| Unified /doctor command | `.cnogo/scripts/workflow_checks.py`, `.cnogo/scripts/workflow_checks_core.py` | LOW |
| Transcript cost tracking | `.cnogo/scripts/memory/costs.py` (new), memory events table | LOW |
| Agent health monitoring | `.cnogo/scripts/memory/watchdog.py` (new) | MEDIUM |

## Key Decisions

**Merge:** Add tier 2 (auto-resolve-keep-incoming) to `merge_session()`, but only when `detect_file_conflicts()` confirms disjoint files. Track `resolvedTier` per merge. Tier 1 (clean merge) already exists.

**Doctor:** New subcommand of `workflow_checks.py`. Runs 5 checks: workflow validation, DB integrity, orphaned worktrees, stale issues, hook config. Each must complete in <5s.

**Costs:** Parse `~/.claude/projects/{slug}/{session}.jsonl` transcripts. Model-specific pricing (Opus/Sonnet/Haiku). Store as `cost_report` events in memory.db.

**Watchdog:** On-demand polling only (no daemon). Check task staleness against `staleIndicatorMinutes`. Log events + notify team lead. No automatic termination.

## Constraints

- Python stdlib only
- No daemon/background processes
- Tier 2 merge gated on disjoint-file pre-validation
- Defensive transcript parsing (format may change)
- Max 3 tasks per plan

## Open Questions

1. Parse historical transcripts or current session only?
2. Should `/doctor --fix` auto-remediate (e.g., prune orphaned worktrees)?
3. Should watchdog create memory issues or just log events?

## Research

See `docs/planning/work/research/overstory-workflow-patterns/RESEARCH.md` for full analysis including Overstory's own risk assessment (STEELMAN.md).
