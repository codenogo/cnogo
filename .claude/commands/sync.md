# Sync
<!-- effort: medium -->

Coordinate work across parallel sessions/checkouts.

## The Problem

With parallel sessions running, you need visibility into what's happening across checkouts without constantly switching terminals.

## Step 0: Detect Mode

Before choosing a sync mode, detect the coordination environment:

1. **Check for Agent Teams**: Is `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set and are there active teammates?
   - If **Agent Teams active**: Use Modes 5-6 (shared task list + mailbox)
   - If **no Agent Teams**: Use memory sync (default)

2. **Auto-detection logic**:
   - Read team config at `~/.claude/teams/*/config.json` to check for active teams
   - If a team exists with active members, prefer Agent Teams modes
   - Otherwise, use memory sync

## Choosing a Mode

| Scenario | Recommended Mode |
|----------|-----------------|
| Default / quick status check | Memory sync |
| Agent Teams active with teammates | Mode 5-6 (shared task list) |
| Messaging a specific teammate | Mode 6 (Agent Teams message) |
| Full team orchestration | Use `/team` instead |

## Solution A: Memory Engine (Primary)

Use the memory engine for structured state synchronization:

### `/sync` (Memory-Backed)

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, sync, stats, prime
from pathlib import Path
root = Path('.')
if is_initialized(root):
    sync(root)
    print(prime(root=root))
    print()
    s = stats(root=root)
    print(f'Total: {s.get(\"total\", 0)} | Open: {s.get(\"open\", 0)} | Active: {s.get(\"in_progress\", 0)} | Ready: {s.get(\"ready\", 0)} | Blocked: {s.get(\"blocked\", 0)}')
    print()
    print('Memory exported to .cnogo/issues.jsonl and staged for git.')
else:
    print('Memory engine not initialized. Using manual sync.')
"
```

Memory mode provides:
- Structured issue state exported to git-tracked JSONL
- Dependency graph with blocked/ready detection
- Token-efficient context summaries
- Automatic merge handling (line-based JSONL format)

Memory sync provides structured state exported to git-tracked JSONL, dependency graphs, and token-efficient summaries. Agent Teams (Modes 5-6) remain for multi-agent coordination.

## Solution B: Agent Teams (Modes 5-6)

When Agent Teams is active, coordination happens through the shared task list and mailbox system built into Claude Code.

## Your Task

When user runs `/sync`:

1. Run the memory sync (export to JSONL, show prime() summary)
2. If Agent Teams are active, also show team status

### `/sync` (View — Agent Teams)

When Agent Teams is detected, show the shared task list instead:

```markdown
## Agent Teams Sync

### Team: [team-name]

### Teammates

| Name | Agent | Status | Current Task |
|------|-------|--------|-------------|
| reviewer-1 | code-reviewer | Active | Reviewing auth module |
| security-1 | security-scanner | Idle | (waiting for assignment) |
| tester-1 | test-writer | Active | Writing integration tests |

### Task List

| ID | Task | Owner | Status | Blocked By |
|----|------|-------|--------|------------|
| 1 | Review auth module | reviewer-1 | in_progress | — |
| 2 | Security audit | security-1 | pending | — |
| 3 | Integration tests | tester-1 | in_progress | — |
| 4 | Merge and ship | — | pending | 1, 2, 3 |

### File Boundaries

| Teammate | Owns |
|----------|------|
| reviewer-1 | src/auth/ |
| tester-1 | tests/ |
```

Use TaskList to read the current task state. Read the team config at `~/.claude/teams/*/config.json` for teammate details.

### Mode 6: `/sync message <teammate> <msg>` (Message — Agent Teams)

Route a message to a teammate via the Agent Teams mailbox:

1. Parse teammate name and message from arguments
2. Use SendMessage to deliver
3. Confirm delivery

## Output

### Memory Sync Mode

- Memory state exported to `.cnogo/issues.jsonl`
- Token-efficient summary via `prime()`
- Statistics overview

### Agent Teams View Mode

Formatted table of teammates, task list, and file boundaries.

### Agent Teams Message Mode

```
Message delivered to [teammate-name]
```

## Notes

This is a lightweight coordination mechanism. For heavier coordination:
- Use `/team` for full Agent Teams orchestration (create, assign, dismiss)
- Use GitHub issues/projects for cross-repo coordination
- Use a proper task board for team-wide visibility

The goal is just visibility, not enforcement. `/sync` shows status; `/team` manages the team.
