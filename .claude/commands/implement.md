# Implement: $ARGUMENTS
<!-- effort: high -->

Execute a plan with verification after each task.

## Arguments

`/implement <feature> <plan-number> [--team]`

Example: `/implement websocket-notifications 01`
Example (team mode): `/implement websocket-notifications 01 --team`

Note: If the plan JSON contains `"parallelizable": true/false`, this influences team-mode auto-detection (see Step 1c).

## Your Task

Execute the specified plan for "$ARGUMENTS".

### Step 1: Load Plan

1. Read `docs/planning/work/features/[feature]/[NN]-PLAN.md`
2. Read `docs/planning/work/features/[feature]/[NN]-PLAN.json` (contract)
3. Verify prerequisites are met

If plan not found, list available plans and ask user to specify.

### Step 1b: Memory Claim (If Enabled)

If the memory engine is initialized and the plan JSON has `memoryId` fields, show ready tasks:

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import is_initialized, ready; from pathlib import Path; root=Path('.'); [print(f'Ready: {t.id} {t.title}') for t in ready(feature_slug='<feature-slug>', root=root)] if is_initialized(root) else None"
```

Before starting each task, claim it:

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import claim; claim('<memoryId>', actor='session', root=__import__('pathlib').Path('.'))"
```

### Step 1c: Team Mode (If Requested)

**Detection logic (in priority order):**
1. If `$ARGUMENTS` contains `--team` → delegate to `/team implement <feature> <plan>`
2. If plan JSON has `"parallelizable": true` AND Agent Teams available → auto-delegate (still run `detect_file_conflicts()` and warn if conflicts exist, but proceed): "Delegating to team mode (plan marked parallelizable)."
3. If plan JSON has `"parallelizable": false` → serial execution (override auto-detection, even if `--team` is not set and tasks look independent)
4. If `parallelizable` not present → fall back to existing heuristic:
   a. If ALL: plan has >2 tasks, Agent Teams available, non-overlapping files → auto-delegate: "Delegating to team mode (N independent tasks with non-overlapping files)."
   b. If >1 task AND Agent Teams available but files overlap → "Serial execution is safer." Continue below.
   c. Otherwise → standard serial execution

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
- Diagnose the issue, fix, re-verify
- If memory enabled, `memory.update(task_memoryId, comment="Failed: ...")`
- If stuck after 2 attempts, pause and ask user

### Step 3: Run Plan Verification

After all tasks, run the plan's verification commands.

### Step 4: Commit

```bash
git add -A
git commit -m "[commit message from plan]"
```

### Step 5: Create Summary

Create `docs/planning/work/features/[feature]/[NN]-SUMMARY.md` and `[NN]-SUMMARY.json`.

Summary template:
```markdown
# Plan NN Summary

## Outcome
✅ Complete | ⚠️ Partial | ❌ Failed

## Changes Made
| File | Change |
|------|--------|

## Verification Results
- Task 1: ✅ [output]
- Plan verification: ✅ [output]

## Issues Encountered
[Any problems and how they were resolved]

## Commit
`abc123f` - [commit message]

---
*Implemented: [date]*
```

Contract schema (minimal):
```json
{
  "schemaVersion": 1,
  "feature": "slug",
  "planNumber": "01",
  "outcome": "complete|partial|failed",
  "changes": [{ "file": "path", "change": "what" }],
  "verification": [{ "task": 1, "result": "pass|fail", "details": "..." }],
  "commit": { "hash": "abc123f", "message": "..." },
  "timestamp": "2026-01-24T00:00:00Z"
}
```

## Output

- Summary of changes
- Issues encountered
- Next plan to execute (if any), or ready for `/review`

Finally: `python3 scripts/workflow_validate.py`
