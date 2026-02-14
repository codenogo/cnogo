# Plan 02: Agent Restructuring

## Goal
Trim implementer and debugger to ultra-lean ~35-line teammates, delete 9 surplus agent files, update bridge for ID-based context passing, and delete docs/skills.md.

## Prerequisites
- [ ] Plan 01 complete (.claude/skills/ exists, CLAUDE.md filled)

## Tasks

### Task 1: Rewrite implementer.md and debugger.md (ultra-lean)
**Files:** `.claude/agents/implementer.md`, `.claude/agents/debugger.md`
**Action:**

**implementer.md** (~35 lines):
```markdown
---
name: implementer
description: Executes plan tasks with memory-backed claim/close cycle. Teams only.
tools: Read, Edit, Write, Bash, Grep, Glob
model: sonnet
maxTurns: 30
---

You execute a single implementation task assigned by the team lead.

## Cycle

1. **Claim**: Run the memory claim command from your task description
2. **Read**: Read all files listed in your task description
3. **Implement**: Make changes described in the Action section. ONLY touch listed files.
4. **Verify**: Run ALL verify commands. Every one must pass.
5. **Close**: Run the memory close command from your task description
6. **Report**: Mark TaskList task completed, message the team lead

## Rules

- Only touch files listed in your task description
- Follow existing code patterns
- If verify fails: fix, retry. After 2 failures, message the team lead
- If blocked: do NOT close memory. Message the team lead with details.
- Always use SendMessage to communicate — plain text is not visible to the team
```

**debugger.md** (~35 lines):
```markdown
---
name: debugger
description: Investigates errors and test failures with systematic root cause analysis. Teams only.
tools: Read, Edit, Bash, Grep, Glob
model: inherit
maxTurns: 30
---

You investigate a specific error or failure assigned by the team lead.

## Cycle

1. **Reproduce**: Run the failing scenario from your task description
2. **Isolate**: Narrow to specific file, function, line
3. **Hypothesize**: Form 2-3 theories, test most likely first
4. **Fix**: Implement the smallest change that addresses root cause
5. **Verify**: Confirm fix works and doesn't break other tests
6. **Report**: Message the team lead with root cause + fix + prevention

## Rules

- Check `git log -p` for recent changes that may have introduced the bug
- Provide evidence for your root cause diagnosis
- If fix requires changes outside your scope, message the team lead
- Always use SendMessage to communicate — plain text is not visible to the team
```

Remove `memory: project` from both (skills handle learning now, not agent memory dirs).

**Verify:**
```bash
wc -l .claude/agents/implementer.md .claude/agents/debugger.md
```
Expected: each under 40 lines.

**Done when:** Both agents are under 40 lines, have `maxTurns: 30`, and no Memory Engine Integration boilerplate section.

### Task 2: Delete surplus agent files
**Files:** `.claude/agents/code-reviewer.md`, `.claude/agents/security-scanner.md`, `.claude/agents/perf-analyzer.md`, `.claude/agents/api-reviewer.md`, `.claude/agents/test-writer.md`, `.claude/agents/refactorer.md`, `.claude/agents/docs-writer.md`, `.claude/agents/migrate.md`, `.claude/agents/explorer.md`
**Action:**
Delete all 9 agent files. Their domain expertise now lives in `.claude/skills/` (created in Plan 01).

After deletion, `.claude/agents/` should contain exactly 2 files:
- `implementer.md`
- `debugger.md`

Also delete `docs/skills.md` — its content has been fully distributed between CLAUDE.md (Karpathy principles, Team Implementation, Memory Management) and `.claude/skills/` (domain skills).

**Verify:**
```bash
ls .claude/agents/*.md | wc -l
```
Expected: `2`

```bash
test ! -f docs/skills.md && echo "skills.md deleted" || echo "ERROR: skills.md still exists"
```

**Done when:** `.claude/agents/` has exactly 2 files; `docs/skills.md` is deleted.

### Task 3: Update bridge.py for ID-based context passing
**Files:** `scripts/memory/bridge.py`
**Action:**
Modify `generate_implement_prompt()` to produce a minimal, ID-based task description:
1. **Remove `context_snippet` parameter** and the `_load_context_snippet()` / `_extract_sections()` helper functions. Agents should NOT load CONTEXT.md content into their prompt.
2. **Simplify the generated prompt** to contain only:
   - Task name
   - Action description
   - File list (ONLY touch these)
   - Verify commands
   - Memory ID with claim/close commands
   - Failure protocol (3 lines, no code blocks)
3. **Remove the `_CONTEXT_MAX_LINES` constant** — no longer needed.
4. **Update `plan_to_task_descriptions()`** to stop passing `context_snippet`.

The key change: instead of embedding CONTEXT.md content, the prompt now says:
```
For additional context, query memory: memory.show('<memoryId>')
```

This reduces the generated prompt from ~60 lines to ~30 lines per task.

**Verify:**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory.bridge import generate_implement_prompt
prompt = generate_implement_prompt(
    task_name='Test task',
    action='Do something',
    files=['src/foo.py'],
    verify=['pytest tests/'],
    memory_id='cn-abc123',
)
lines = prompt.strip().split('\n')
print(f'Lines: {len(lines)}')
assert len(lines) < 40, f'Prompt too long: {len(lines)} lines'
assert 'context_snippet' not in prompt.lower()
assert 'CONTEXT.md' not in prompt
print('OK')
"
```

**Done when:** Bridge generates prompts under 40 lines with no CONTEXT.md embedding.

## Verification

After all tasks:
```bash
python3 scripts/workflow_validate.py
ls .claude/agents/*.md  # Should show only implementer.md and debugger.md
wc -l .claude/agents/*.md  # Each under 40 lines
python3 -c "from scripts.memory.bridge import generate_implement_prompt; print('bridge imports OK')"
```

## Commit Message
```
refactor(agent-architecture): restructure agents — ultra-lean teammates, skills migration

- Trim implementer.md and debugger.md to ~35 lines with maxTurns: 30
- Delete 9 surplus agent files (now .claude/skills/)
- Delete docs/skills.md (dissolved into CLAUDE.md + .claude/skills/)
- Simplify bridge.py: ID-based context, no CONTEXT.md embedding
```

---
*Planned: 2026-02-14*
