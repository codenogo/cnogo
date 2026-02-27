# TaskOutput Team Monitoring Anti-Patterns

## Problem

During `/team implement`, the team lead model invents three anti-patterns that cause errors:

1. **TaskOutput with fabricated IDs** — calls `TaskOutput("plan03-impl@impl-video-purchase")` using a composite `name@team_name` format that doesn't match any system-generated ID
2. **`isolation: "worktree"` on Task tool** — creates Claude Code-managed worktrees that duplicate cnogo's own worktree session system
3. **Manual `git worktree remove`** — fails with `fatal: contains modified or untracked files` because it omits `--force` (which `session-cleanup` already handles)

## Root Cause

Step 11 in `team.md` was underspecified — it said *what* to monitor (TaskList) but not *how*, leaving the model to invent its own monitoring approach.

## Decisions

| Area | Decision | Why |
|------|----------|-----|
| Monitoring | No TaskOutput for team agents | Foreground agents report via TaskList + SendMessage auto-delivery |
| Monitoring | No composite IDs | Claude Code uses opaque system-generated IDs, not `name@team_name` |
| Spawning | No `isolation: "worktree"` | cnogo manages worktrees via `create_session()` |
| Cleanup | No manual `git worktree remove` | `session-cleanup` handles `--force` and branch deletion |
| Wording | Explain *why*, not just *don't* | Architectural reasons prevent re-invention of anti-patterns |

## Scope

Fix is command guidance only (`.claude/commands/team.md`). No code changes to `bridge.py`, `worktree.py`, or `implementer.md`.

## Research

See `docs/planning/work/research/taskoutput-team-monitoring/RESEARCH.md` for validation of the TaskOutput assertion.
