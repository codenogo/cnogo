# Team: $ARGUMENTS
<!-- effort: high -->

Orchestrate Agent Teams for collaborative multi-agent workflows.

> **EXPERIMENTAL**: Agent Teams is a research preview feature. Behavior may change. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` to enable (already enabled by default in this workflow pack).

## Arguments

`/team <action> [args]`

| Action | Usage | Purpose |
|--------|-------|---------|
| `create` | `/team create <task-description>` | Create a team and spawn teammates for a task |
| `status` | `/team status` | Show teammates, task list, and progress |
| `message` | `/team message <teammate> <message>` | Send a message to a specific teammate |
| `dismiss` | `/team dismiss` | Shut down all teammates gracefully |

## Available Agents for Teams

Teammates are spawned from `.claude/agents/` definitions:

| Agent | Model | Role | Best As Teammate For |
|-------|-------|------|---------------------|
| `code-reviewer` | sonnet | Code quality analysis | Review teams, full-stack teams |
| `security-scanner` | sonnet | Vulnerability auditing | Review teams, security audits |
| `perf-analyzer` | sonnet | Performance analysis | Review teams, optimization sprints |
| `api-reviewer` | sonnet | API design review | Review teams, API-heavy features |
| `test-writer` | inherit | Test generation | Full-stack teams, TDD workflows |
| `debugger` | inherit | Root cause analysis | Debug teams, incident response |
| `refactorer` | inherit | Code quality improvement | Full-stack teams, cleanup sprints |
| `docs-writer` | haiku | Documentation | Full-stack teams, release prep |
| `migrate` | inherit | Framework/dependency upgrades | Migration teams |

## Recommended Team Compositions

### Code Review Team
3 reviewers analyzing different dimensions in parallel:
```
/team create Review PR #142 for quality, security, and performance
```
Spawns: `code-reviewer`, `security-scanner`, `perf-analyzer`

### Full-Stack Team
4 specialists owning different layers:
```
/team create Build the notifications feature end-to-end
```
Spawns: `test-writer` (tests), `debugger` (backend), `refactorer` (frontend), `docs-writer` (docs)

### Debug Team
3 investigators testing competing hypotheses:
```
/team create Investigate why the app crashes after login — try 3 different theories
```
Spawns: `debugger`, `debugger`, `debugger` (each assigned a different hypothesis)

### Migration Team
2 specialists for safe upgrades:
```
/team create Upgrade React from v18 to v19
```
Spawns: `migrate` (core upgrade), `test-writer` (regression tests)

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Shift+Up/Down` | Select a teammate to view/interact with |
| `Shift+Tab` | Toggle delegate mode (lead coordinates only, no coding) |
| `Ctrl+T` | Toggle task list visibility |
| `Ctrl+B` | Background the current task |
| `Escape` | Interrupt current teammate's turn |

## Your Task

### Step 0: Verify Agent Teams Enabled

Check that `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set to `"1"` in the environment or `.claude/settings.json`. If not enabled, inform the user how to enable it.

### Step 1: Parse Action

Extract the action and arguments from "$ARGUMENTS":
- First word = action (create, status, message, dismiss)
- Remaining = action-specific arguments

### Step 2: Execute Action

#### Action: `create`

1. Analyze the task description to determine which agents are needed
2. Match to a recommended composition (or create a custom one)
3. **Activate delegate mode** — the lead (you) should coordinate, not code directly
4. Create the team using TeamCreate
5. Create tasks using TaskCreate based on the task description
6. Spawn teammates from `.claude/agents/` definitions using the Task tool with `team_name`
7. **Assign file boundaries** to each teammate to prevent merge conflicts:
   - Each teammate should own specific files/directories
   - No two teammates should edit the same file
   - Document assignments in the task descriptions
8. Report the team composition and assignments

#### Action: `status`

1. Read the team config to list all teammates
2. Show TaskList with current status
3. Report:
   - Active teammates and their current task
   - Completed tasks
   - Blocked tasks and why
   - Recommended next actions

#### Action: `message`

1. Parse teammate name and message from arguments
2. Send the message using SendMessage
3. Confirm delivery

#### Action: `dismiss`

1. Send shutdown_request to each teammate
2. Wait for confirmations
3. Clean up team resources with TeamDelete
4. Report final status

### Step 3: Report

```markdown
## Team Status

**Team:** [team-name]
**Mode:** [delegate/active]
**Teammates:** [count]

| Teammate | Agent | Status | Current Task |
|----------|-------|--------|-------------|
| [name] | [agent-type] | [active/idle/done] | [task description] |

### Task List
| ID | Task | Owner | Status | Blocked By |
|----|------|-------|--------|------------|

### File Boundaries
| Teammate | Owns |
|----------|------|
| [name] | [files/directories] |
```

## Best Practices

1. **Use delegate mode by default** — Press `Shift+Tab` to keep the lead focused on coordination
2. **Assign clear file boundaries** — Prevents merge conflicts between teammates
3. **Size tasks appropriately** — ~5-6 self-contained units per teammate
4. **Monitor with Ctrl+T** — Check task list regularly, redirect off-track work
5. **Start with review tasks** — Build intuition for team value before implementation tasks
6. **Keep teams small** — 3-4 teammates is optimal; more increases coordination overhead and token cost
7. **Token awareness** — Each teammate loads context independently; 3 teammates ≈ 3-4x token usage

## Examples

```bash
# Parallel code review
/team create Review PR #142 with security, performance, and code quality reviewers

# Full-stack feature
/team create Build user notifications with backend, tests, and docs specialists

# Competing hypothesis debugging
/team create Debug the login crash — investigate auth tokens, session state, and race conditions

# Check team progress
/team status

# Send guidance to a teammate
/team message debugger Focus on the session middleware, I think that's the issue

# Wrap up
/team dismiss
```

## Notes

- Agent Teams is a research preview — expect rough edges
- No session resumption after `/resume` or `/rewind` commands
- One team per session maximum
- Teammates cannot spawn their own teams
- For lighter coordination, use `/sync` instead
- For single-agent work, use `/spawn` instead

## Output

- Team composition and teammate assignments
- Task list with file boundaries
- Instructions for monitoring and interacting with the team
