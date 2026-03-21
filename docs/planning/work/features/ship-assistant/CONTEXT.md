# Context: Ship Assistant

Guided ship path that computes commit surface, generates PR metadata, and auto-infers ship completion args.

## Decisions

### D1: Hardcoded baseline exclude patterns

Hardcoded `SHIP_EXCLUDE_PATTERNS` in the module. Runtime paths excluded from ship commits: `.cnogo/runs/`, `.cnogo/work-orders/` (except `.gitkeep`), `.cnogo/feature-phases.json`, `.cnogo/watch/`, `.cnogo/worktree-session.json`. Additive config may come later but baseline is not replaceable.

### D2: Commit message from plan contract

Read plan `commitMessage` field as source of truth. No LLM re-summarization at ship time.

### D3: Terse deterministic PR body

Format: `## Summary` (plan goal bullets), `## Test Plan` (SUMMARY.json verification), `## Review` (verdict + reviewers), `## Planning References` (repo-relative paths). `## Follow-ups` only when review verdict is warn or open items exist. No tables, no LLM prose.

### D4: Auto-infer on run-ship-complete

Auto-infer branch and commit by default. Fail closed unless: branch matches `feature/<feature>`, `git rev-parse HEAD` succeeds, no run ambiguity. Explicit args required if any guard fails.

### D5: New module in orchestration

Code in `.cnogo/scripts/workflow/orchestration/ship_draft.py`. CLI: `run-ship-draft` in `workflow_memory.py`.

### D6: Update /ship to use draft

Replace manual steps with draft-driven flow. Each step still visible but pre-computed.

### D7: Work Orders are runtime, not source

`.cnogo/work-orders/*.json` gitignored and excluded from ship. Only `.gitkeep` tracked.

### D8: Output includes convenience command

`run-ship-draft` returns `commitSurface[]` (source of truth) and `gitAddCommand` (operator convenience).

## Constraints

- Python stdlib only
- No git operations in the module
- Plan commitMessage is source of truth
- Backward compatible — /ship still works without draft
- SHIP_EXCLUDE_PATTERNS baseline is hardcoded

## Related Code

| File | Role |
|---|---|
| `.cnogo/scripts/workflow/orchestration/ship.py` | Ship state machine |
| `.cnogo/scripts/workflow/orchestration/work_order.py` | Work Order model |
| `.cnogo/scripts/workflow/orchestration/delivery_run.py` | DeliveryRun model |
| `.cnogo/scripts/workflow/checks/ship_ready.py` | Ship readiness gate |
| `.cnogo/scripts/workflow_memory.py` | CLI entrypoint |
| `.claude/commands/ship.md` | Ship command to update |
| `.gitignore` | Runtime exclusions |

---
*Generated: 2026-03-21*
