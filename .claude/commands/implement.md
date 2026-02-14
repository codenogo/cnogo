# Implement: $ARGUMENTS
<!-- effort: high -->

Execute a plan with verification after each task.

## Arguments

`/implement <feature> <plan-number> [--team]`

Example: `/implement websocket-notifications 01`
Example (team mode): `/implement websocket-notifications 01 --team`

## Your Task

Execute the specified plan for "$ARGUMENTS".
**Tip:** For complex plans, use Plan Mode (`Shift+Tab`) to strategize the execution steps before writing code.

### Principle Reminder (Use Skills Library)

Apply **Karpathy Principles** from `docs/skills.md` during implementation:

- Surgical Changes (minimize diff, avoid drive-by refactors)
- Goal-Driven Execution (verify after each task; loop until proven)

### Step 1: Load Plan

1. Read `docs/planning/work/features/[feature]/[NN]-PLAN.md`
2. Read `docs/planning/work/features/[feature]/[NN]-PLAN.json` (contract)
3. Read `docs/planning/work/features/[feature]/CONTEXT.md` for decisions
4. Verify prerequisites are met

If plan not found, list available plans and ask user to specify.

### Step 1b: Memory Claim (If Enabled)

If the memory engine is initialized and the plan JSON has `memoryId` fields:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, claim, ready
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Show ready tasks for this feature
    tasks = ready(feature_slug='<feature-slug>', root=root)
    for t in tasks:
        print(f'Ready: {t.id} {t.title}')
"
```

Before starting each task, claim it:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import claim
from pathlib import Path
claim('<memoryId>', actor='<session-id>', root=Path('.'))
"
```

### Step 1c: Team Mode (If Requested)

If team-based parallel execution is requested or applicable:

**Detection logic:**
1. If `$ARGUMENTS` contains `--team` → delegate to `/team implement <feature> <plan>`
2. Else if the plan has >1 task AND Agent Teams is available (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`):
   - Suggest: "This plan has N tasks. Run `/team implement <feature> <plan>` for parallel execution?"
   - If user confirms, delegate to `/team implement`
   - If user declines, continue with standard serial execution below
3. Otherwise → standard serial execution (unchanged)

**When delegating to team mode:**
- Run `/team implement <feature> <plan>` which uses the bridge module to generate task descriptions, spawn implementer teammates, and coordinate execution
- The team lead monitors via TaskList and handles failures
- After all tasks complete, the team lead runs plan verification and creates summary artifacts

**When continuing with serial mode:**
- Proceed to Step 2 below (existing single-agent sequential flow, unchanged)

### Step 2: Execute Tasks

For each task in the plan:

1. **Announce** — "Starting Task N: [name]"
2. **Claim** — If memory enabled, `memory.claim(task_memoryId, actor=session_id)`
3. **Read** — Load the files mentioned in the task
4. **Implement** — Make the changes as specified
5. **Verify** — Run the verification command
6. **Close** — If memory enabled and verify passes, `memory.close(task_memoryId)`
7. **Report** — "Task N complete" or "Task N failed: [reason]"

If verification fails:
- Diagnose the issue
- Fix and re-verify
- If memory enabled, `memory.update(task_memoryId, comment="Failed: ...")`
- If stuck after 2 attempts, pause and ask user

### Step 3: Run Plan Verification

After all tasks, run the plan's verification commands.

### Step 4: Commit

Create atomic commit with the message from the plan:
```bash
git add -A
git commit -m "[commit message from plan]"
```

### Step 5: Create Summary

Create/update `docs/planning/work/features/[feature]/[NN]-SUMMARY.md`:

```markdown
# Plan NN Summary

## Outcome
✅ Complete | ⚠️ Partial | ❌ Failed

## Changes Made

| File | Change |
|------|--------|
| `path/to/file` | [what changed] |

## Verification Results

- Task 1: ✅ [output]
- Task 2: ✅ [output]
- Task 3: ✅ [output]
- Plan verification: ✅ [output]

## Issues Encountered

[Any problems and how they were resolved]

## Commit

`abc123f` - [commit message]

---
*Implemented: [date]*
```

Also create a machine-checkable contract:

- `docs/planning/work/features/[feature]/[NN]-SUMMARY.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per summary: `NN-SUMMARY.md` + `NN-SUMMARY.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Outcome required**: `outcome` MUST be `complete|partial|failed`.
- **Validation**: run `python3 scripts/workflow_validate.py` after writing the summary.

Contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "planNumber": "01",
  "outcome": "complete|partial|failed",
  "changes": [{ "file": "path/to/file", "change": "what changed" }],
  "verification": [{ "task": 1, "result": "pass|fail", "details": "..." }],
  "commit": { "hash": "abc123f", "message": "..." },
  "timestamp": "2026-01-24T00:00:00Z"
}
```

### Step 6: Update State

Update `docs/planning/STATE.md`:
```
## Current Focus
- Feature: [feature]
- Plan 01: ✅ Complete
- Plan 02: 🔄 In progress
- Next: /implement [feature] 02
```

## Output

After completion:
- Summary of changes
- Any issues encountered
- Next plan to execute (if any)
- Or ready for `/review` if all plans complete

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
