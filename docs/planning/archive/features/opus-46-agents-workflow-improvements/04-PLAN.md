# Plan 04: Update Installer, Agent Memory Setup, and Final Integration

## Goal
Update install.sh to install .claude/agents/ and agent-memory scaffolding, update README and command count, and run full end-to-end validation.

## Prerequisites
- [ ] Plan 01 complete (agent definitions to install)
- [ ] Plan 02 complete (settings.json changes to install)
- [ ] Plan 03 complete (team.md command to install)

## Tasks

### Task 1: Update install.sh to install .claude/agents/ and memory scaffolding
**Files:** `install.sh`
**Action:**
Add two new sections to install.sh:

1. **Agent definitions section** (after the `.claude/commands` section):
   - `mkdir -p "$TARGET_DIR/.claude/agents"`
   - Copy all `.claude/agents/*.md` files
   - Print each agent installed with its model tier
   - Example output: `   ├── agents/code-reviewer.md (sonnet)`

2. **Agent memory scaffolding** (after agent definitions):
   - `mkdir -p "$TARGET_DIR/.claude/agent-memory"` (project scope, checked in)
   - Create `.gitkeep` in agent-memory directory
   - Do NOT create `.claude/agent-memory-local/` (not used per decision)

3. **Update command count** in the "Commands installed" summary:
   - Change "(21)" → "(28)" (21 existing + /team + 6 new agent count note)
   - Actually: the command count is the slash commands. /team is 1 new. So 21 + 1 = 22. But we also added /brainstorm, /research, /bug, /close from the previous commit. Check current count.
   - Add new "Agents:" line: `  Agents:   /spawn  /team  /background  (10 agent definitions)`

4. **Update "Next steps"** at the bottom:
   - Add step: "5. Run '/agents' to view available subagents"

**Verify:**
```bash
grep "agents" install.sh | head -10
grep "agent-memory" install.sh
grep -c "mkdir" install.sh  # Should increase by 2
```

**Done when:** install.sh creates .claude/agents/ with all 10 definitions and .claude/agent-memory/ with .gitkeep.

### Task 2: Update README.md with agent workflow documentation
**Files:** `README.md`
**Action:**
Add a new section to README.md documenting the agent system:

1. **"Agent Definitions" section** explaining:
   - What `.claude/agents/` contains
   - The 10 agents with their model tiers and specializations (table)
   - How to invoke agents (direct request or via /spawn)
   - Persistent memory and how it works
   - How to create custom project-specific agents

2. **"Agent Teams" section** explaining:
   - What Agent Teams are (experimental)
   - How to use /team command
   - Keyboard shortcuts
   - Recommended team compositions
   - When to use teams vs. subagents

3. **Update the "Commands installed" section** to reflect the new /team command and agent definitions

Keep the update concise — reference the official Claude Code docs for deep details.

**Verify:**
```bash
grep "Agent Definitions" README.md
grep "Agent Teams" README.md
grep "claude/agents" README.md
grep "/team" README.md
```

**Done when:** README documents agent definitions, Agent Teams, and the /team command.

### Task 3: Full end-to-end validation and STATE.md update
**Files:** `docs/planning/STATE.md`, `docs/planning/work/features/opus-46-agents-workflow-improvements/CONTEXT.md`
**Action:**

1. Run `python3 scripts/workflow_validate.py` and fix any issues
2. Verify all 10 agent files exist and have valid frontmatter
3. Verify settings.json is valid JSON with all expected keys
4. Verify WORKFLOW.json is valid JSON with agentTeams section
5. Verify install.sh references all new files
6. Update STATE.md:
   - Status: "Implementing" → "Ready for review"
   - Plans: 01 ✅, 02 ✅, 03 ✅, 04 ✅
   - Next Action: `/review opus-46-agents-workflow-improvements`

**Verify:**
```bash
python3 scripts/workflow_validate.py
ls .claude/agents/*.md | wc -l  # 10
python3 -c "import json; json.load(open('.claude/settings.json')); print('settings OK')"
python3 -c "import json; json.load(open('docs/planning/WORKFLOW.json')); print('workflow OK')"
grep "Ready for review" docs/planning/STATE.md
```

**Done when:** All validation passes, STATE.md updated, feature ready for /review.

## Verification

After all tasks:
```bash
# Full validation
python3 scripts/workflow_validate.py

# Agent count
ls .claude/agents/*.md | wc -l  # 10

# JSON validity
python3 -c "import json; json.load(open('.claude/settings.json')); json.load(open('docs/planning/WORKFLOW.json')); print('All JSON valid')"

# Install script test (dry check)
grep -c "agents" install.sh

# Feature state
grep "Ready for review" docs/planning/STATE.md
```

## Commit Message
```
feat(opus-46-agents-workflow-improvements): installer, README, final integration

- Update install.sh to install .claude/agents/ and agent-memory scaffolding
- Add agent workflow documentation to README.md
- Full end-to-end validation
- Update STATE.md to ready for review
```

---
*Planned: 2026-02-10*
