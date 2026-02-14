# Plan 01: Bridge Module + Implementer Agent

## Goal
Create the core infrastructure: a bridge module that translates plan tasks into agent-executable descriptions with memory linkage, and an implementer agent that knows the claim-execute-verify-close cycle.

## Prerequisites
- [x] Memory engine built and reviewed (phases 1-7)
- [x] `/discuss team-implement-integration` complete
- [x] Memory epic `cn-9xdhpc` exists

## Tasks

### Task 1: Create bridge module
**Files:** `scripts/memory/bridge.py`
**Action:**
Create `scripts/memory/bridge.py` with two key functions:

1. `plan_to_task_descriptions(plan_json_path, root)` — Reads an `NN-PLAN.json` file, ensures memory issues exist for each task (creating them if `memoryId` is missing), and returns a list of dicts containing: `name`, `description` (full agent prompt), `memoryId`, `files`, `verify`, `blockedBy`.

2. `generate_implement_prompt(task_desc)` — Takes a single task description dict and generates the full agent prompt including:
   - Feature context (reads CONTEXT.md first 20 lines)
   - Task action from plan
   - File list (agent should only touch these files)
   - Verify commands (agent must run these and report results)
   - Memory claim/close instructions (bash snippets the agent runs)
   - Failure protocol (retry once, then notify leader)

Per CONTEXT.md decisions:
- Memory -> TaskList direction only (bridge reads memory, does not write to TaskList)
- Plan `verify[]` becomes agent success criterion
- Plan `files[]` serves as file boundary

**Verify:**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory.bridge import plan_to_task_descriptions, generate_implement_prompt
print('bridge module imports OK')
"
```

**Done when:** Module imports cleanly, both functions exist with correct signatures.

### Task 2: Create implementer agent
**Files:** `.claude/agents/implementer.md`
**Action:**
Create `.claude/agents/implementer.md` with frontmatter:
```yaml
---
name: implementer
description: Plan task execution specialist. Claims memory issues, implements code changes, runs verification, and closes on success. Use for parallel plan execution in teams.
tools: Read, Edit, Write, Bash, Grep, Glob
model: inherit
memory: project
---
```

Body should instruct the agent to:
1. Read the task description (provided in spawn prompt) for action, files, verify commands
2. Claim the memory issue: `python3 -c "from scripts.memory import claim; claim('<memoryId>', actor='<name>', root=Path('.'))"`
3. Read each file in the `files[]` list before making changes
4. Implement the changes described in `action`
5. Run each verify command; if any fails, diagnose and retry once
6. On all verify pass: close the memory issue with `memory.close(memoryId)`
7. On persistent failure: update memory issue with failure comment, notify leader via SendMessage
8. Include the standard Memory Engine Integration section (same as other agents)

**Verify:**
```bash
test -f .claude/agents/implementer.md && grep -q 'name: implementer' .claude/agents/implementer.md && grep -q 'claim' .claude/agents/implementer.md && echo "implementer agent OK"
```

**Done when:** Agent file exists with correct frontmatter and claim/verify/close cycle instructions.

### Task 3: Expose bridge in public API
**Files:** `scripts/memory/__init__.py`
**Action:**
Add bridge module functions to the public API:

1. Add imports at top: `from .bridge import plan_to_task_descriptions, generate_implement_prompt`
2. Add to `__all__` list: `"plan_to_task_descriptions"`, `"generate_implement_prompt"`

Keep it minimal — just expose the functions so commands can import from `scripts.memory`.

**Verify:**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import plan_to_task_descriptions, generate_implement_prompt
print('public API exports OK')
"
```

**Done when:** Both functions are importable from `scripts.memory`.

## Verification

After all tasks:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory.bridge import plan_to_task_descriptions, generate_implement_prompt
from scripts.memory import plan_to_task_descriptions as p2t
print('All imports OK')
" && test -f .claude/agents/implementer.md && python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(team-implement-integration): add bridge module and implementer agent

- Create scripts/memory/bridge.py with plan-to-task translation
- Create .claude/agents/implementer.md for plan task execution
- Expose bridge functions in scripts/memory/__init__.py
```

---
*Planned: 2026-02-14*
