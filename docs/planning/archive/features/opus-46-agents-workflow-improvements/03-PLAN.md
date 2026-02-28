# Plan 03: Agent Teams Integration — /team Command and /sync Dual-Mode

## Goal
Create the /team command for Agent Teams orchestration and update /sync to dual-mode (Agent Teams shared task list when active, manual fallback otherwise).

## Prerequisites
- [ ] Plan 01 complete (agent definitions for teammate spawning)
- [ ] Plan 02 complete (Agent Teams env var in settings.json)

## Tasks

### Task 1: Create /team command
**Files:** `.claude/commands/team.md`
**Action:**
Create a new slash command for Agent Teams orchestration. The command should:

1. Parse arguments: `/team <action> [args]`
   - `/team create <task-description>` — Create a team for a task, spawn teammates
   - `/team status` — Show all teammates, their status, and task list
   - `/team message <teammate> <message>` — Send a message to a teammate
   - `/team dismiss` — Shut down all teammates
2. Include experimental status warning at the top
3. Reference `.claude/agents/` definitions for teammate specializations
4. Provide recommended team compositions:
   - **Code review team**: 3 reviewers (security, perf, code-quality)
   - **Full-stack team**: backend, frontend, tests, docs
   - **Debug team**: competing hypothesis investigators
5. Document keyboard shortcuts: Shift+Up/Down (select), Shift+Tab (delegate mode), Ctrl+T (task list)
6. Recommend delegate mode by default (lead coordinates, doesn't code)
7. Include file boundary assignment guidance to prevent merge conflicts
8. Add `<!-- effort: high -->` effort hint

**Verify:**
```bash
test -f .claude/commands/team.md && echo "EXISTS"
grep "EXPERIMENTAL" .claude/commands/team.md
grep "delegate" .claude/commands/team.md
grep "Shift" .claude/commands/team.md
grep "effort: high" .claude/commands/team.md
```

**Done when:** /team command exists with create/status/message/dismiss actions, experimental warning, and team composition templates.

### Task 2: Update /sync for dual-mode operation
**Files:** `.claude/commands/sync.md`
**Action:**
Update sync.md to detect and use Agent Teams when active:

1. Add a new "Step 0: Detect Mode" section before existing steps:
   - Check if Agent Teams is active (env var + active teammates)
   - If active: use Agent Teams shared task list and mailbox for coordination
   - If not active: fall back to existing manual sync file approach
2. Add new mode for Agent Teams:
   - **Mode 5: `/sync` (Agent Teams)** — Show shared task list with teammate assignments, status, and dependencies
   - **Mode 6: `/sync message <teammate> <msg>`** — Route to Agent Teams mailbox
3. Keep all existing modes (1-4) intact as fallback
4. Add a "Choosing Mode" section explaining when each is appropriate
5. Update the Notes section to reference `/team` for heavier coordination

**Verify:**
```bash
grep "Agent Teams" .claude/commands/sync.md
grep "Detect Mode" .claude/commands/sync.md
grep "fallback" .claude/commands/sync.md
grep -c "Mode" .claude/commands/sync.md  # Should be > 4
```

**Done when:** /sync detects Agent Teams mode and offers both shared task list and manual coordination.

### Task 3: Add Agent Teams hooks guidance to settings.json and WORKFLOW.json
**Files:** `.claude/settings.json`, `docs/planning/WORKFLOW.json`
**Action:**

For settings.json:
- Add `SubagentStop` hook that logs teammate completion to help with session awareness
- Keep it lightweight: just echo a completion message with the agent type name

```json
"SubagentStop": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "echo '🤖 Subagent completed: '\"$CLAUDE_AGENT_TYPE\""
      }
    ]
  }
]
```

For WORKFLOW.json:
- Add an `agentTeams` section (additive, backward-compatible):

```json
"agentTeams": {
  "enabled": true,
  "delegateMode": true,
  "defaultCompositions": {
    "review": ["code-reviewer", "security-scanner", "perf-analyzer"],
    "fullstack": ["test-writer", "debugger", "docs-writer", "refactorer"],
    "debug": ["debugger", "debugger", "debugger"]
  }
}
```

**Verify:**
```bash
python3 -c "import json; d=json.load(open('.claude/settings.json')); assert 'SubagentStop' in d['hooks']; print('Hook OK')"
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); assert 'agentTeams' in d; print('Config OK')"
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** SubagentStop hook added to settings, agentTeams config added to WORKFLOW.json, validation passes.

## Verification

After all tasks:
```bash
test -f .claude/commands/team.md && echo "TEAM CMD OK"
grep "Agent Teams" .claude/commands/sync.md && echo "SYNC DUAL-MODE OK"
python3 -c "import json; d=json.load(open('.claude/settings.json')); print('Hooks:', list(d['hooks'].keys()))"
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); print('Agent Teams:', d.get('agentTeams', {}).get('enabled'))"
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(opus-46-agents-workflow-improvements): Agent Teams integration

- Create /team command with create/status/message/dismiss actions
- Update /sync with dual-mode (Agent Teams + manual fallback)
- Add SubagentStop hook for teammate completion logging
- Add agentTeams config section to WORKFLOW.json
```

---
*Planned: 2026-02-10*
