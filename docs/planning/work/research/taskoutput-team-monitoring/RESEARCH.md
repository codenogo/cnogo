# Research: TaskOutput Team Monitoring Anti-Pattern

## Question

Is this assertion correct?

> Using TaskOutput with `name@team_name` IDs is an anti-pattern. The error `No task found with ID: plan03-impl@impl-video-purchase` occurs because TaskOutput is for background shells, not team agents.

## Findings

### 1. The `name@team_name` ID format is invalid

The ID `plan03-impl@impl-video-purchase` is a composite constructed from Task tool parameters (`name` + `@` + `team_name`). Claude Code's task system uses opaque identifiers (system-generated), not composable `name@team_name` strings. No documentation or code in Claude Code references this format.

**Verdict: CORRECT** — constructing composite IDs is the primary error.

### 2. TaskOutput scope is broader than "background shells only"

The Claude Code TaskOutput tool description states: *"Retrieves output from a running or completed task (background shell, **agent**, or remote session)."* It explicitly supports agents.

However, in cnogo's architecture this doesn't matter because:
- cnogo spawns teammates in **foreground** (not `run_in_background`)
- Foreground agents don't produce TaskOutput entries
- Team coordination uses TaskList + SendMessage auto-delivery instead

**Verdict: PARTIALLY CORRECT** — TaskOutput supports agents in general, but cnogo's foreground spawning pattern makes it irrelevant for team workflows.

### 3. The real root cause is two-fold

1. **Invalid ID format**: The model invents `name@team_name` composite IDs that don't match any system-generated ID
2. **Wrong tool for the pattern**: Even with a correct ID, foreground-spawned team agents don't have TaskOutput entries — they communicate via SendMessage and report status via TaskList

### 4. Worktree cleanup is a separate issue

The related error (`fatal: contains modified or untracked files, use --force`) occurs because the team lead manually runs `git worktree remove` without `--force` instead of using `session-cleanup` (which already uses `--force`). Additionally, using `isolation: "worktree"` on the Task tool creates Claude Code-managed worktrees that conflict with cnogo's own worktree session system.

## Recommendation

The fix in `team.md` should say:

> Do NOT use TaskOutput — foreground team agents report via TaskList and SendMessage, not TaskOutput. Do NOT construct IDs like "name@team_name" — these are invalid.

This is more precise than "TaskOutput is for background shells" because it explains *why* TaskOutput doesn't apply (foreground spawning + auto-delivery) rather than incorrectly limiting TaskOutput's general scope.

## Sources

| Source | Type | Key evidence |
|--------|------|-------------|
| `.claude/commands/team.md` | repo | Spawning rules, monitoring steps, cleanup |
| `docs/planning/work/research/opus-46-multi-agent/RESEARCH.md` | repo | Agent Teams architecture, message auto-delivery |
| Claude Code TaskOutput tool description | system | "background shell, agent, or remote session" |
| `.cnogo/scripts/memory/worktree.py:668` | repo | `cleanup_session()` already uses `--force` |
| `.cnogo/scripts/memory/bridge.py:117-190` | repo | `generate_implement_prompt()` — no TaskOutput references |
