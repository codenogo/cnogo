# Kill STATE.md - Implementation Context

## Summary

Remove `docs/planning/STATE.md` entirely. Make the memory engine the single source of truth for project state, session handoff, and feature progress. Eliminates the dual-update problem where 17 commands had to manually update both STATE.md and memory in parallel.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Memory requirement | Required at install — `install.sh` runs `memory.init()` automatically | Eliminates all "If Enabled" guards; memory is always available |
| Session handoff | Store as metadata on active epic | `prime()` already shows active epics; `/resume` reads `show(epic_id).metadata['handoff']` naturally |
| Recent Decisions log | Drop entirely | Feature decisions live in CONTEXT.md; merges/rollbacks already in git log; table was redundant |
| /sync Modes 1-4 | Replace with memory Mode 7 only | Drop manual grep-based modes; `/sync` always uses `prime()` + `stats()`; JSONL is git-tracked for cross-checkout visibility |
| prime() enhancement | Add active epic details + plan progress | Show in-progress epic(s) with feature_slug, plan_number, child task completion ratio (replaces Current Focus section) |
| Feature auto-detection | Query memory for in-progress epic | Replace `infer_feature_from_state()` with `list_issues(issue_type='epic', status='in_progress')`, fallback to branch name |
| Install & validation | Remove STATE.md from install.sh + workflow_validate.py | Stop copying STATE.md; remove `_require(STATE.md)` check; add `_require(.cnogo/memory.db)` check |
| Migration | Auto-delete STATE.md on next install | `install.sh` detects and removes existing STATE.md from target projects |

## Constraints

- Memory engine must be initialized before any command that previously read STATE.md
- `prime()` output must remain token-efficient (~500-1500 tokens) despite added epic details
- Handoff metadata on epics must handle the "no active epic" case (idle project, between features)
- All 17 commands that reference STATE.md must be updated
- `workflow_checks.py` and `workflow_validate.py` need Python-level changes
- `install.sh` needs STATE.md removed from template loop + auto-delete logic added
- `.claude/CLAUDE.md` and `CLAUDE.md` docs reference STATE.md — update documentation
- README.md references STATE.md extensively — update documentation

## Open Questions

- When no epic is in progress (idle project), where does `/pause` store handoff? Options: create a transient "session" issue, or store in `.cnogo/` metadata file. Lean toward transient issue.

## Related Code

- `.cnogo/scripts/memory/context.py` — `prime()` function that needs enhancement
- `.cnogo/scripts/memory/__init__.py` — public API, needs `update()` for handoff metadata
- `.cnogo/scripts/workflow_checks.py:50-65` — `infer_feature_from_state()` to replace
- `.cnogo/scripts/workflow_validate.py:649` — `_require(STATE.md)` to remove
- `install.sh:177` — STATE.md in template copy loop
- `.claude/commands/resume.md` — reads STATE.md for handoff (most complex migration)
- `.claude/commands/pause.md` — writes handoff to STATE.md
- `.claude/commands/status.md` — reads STATE.md for display
- `.claude/commands/sync.md` — Modes 1-4 grep STATE.md
- `.claude/commands/plan.md` — reads/writes Current Focus
- `.claude/commands/implement.md` — writes plan completion
- `.claude/commands/discuss.md` — reads/writes Current Focus
- `.claude/commands/ship.md` — reads/writes Current Focus
- `.claude/commands/close.md` — writes Current Focus + Decisions
- `.claude/commands/team.md` — writes plan completion
- `.claude/commands/verify.md` — writes verification status
- `.claude/commands/verify-ci.md` — writes CI verification status
- `.claude/commands/review.md` — reads active feature for artifact placement
- `.claude/commands/rollback.md` — writes Decisions
- `docs/planning/STATE.md` — the file itself (to be deleted)

---
*Discussed: 2026-02-14*
