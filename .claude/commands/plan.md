# Plan: $ARGUMENTS
<!-- effort: high -->

Create implementation tasks for the feature. Each plan has ≤3 tasks to keep context fresh.

## Your Task

Break "$ARGUMENTS" into atomic, executable plans.

### Naming Rule

- `$ARGUMENTS` MUST be the **feature slug** (kebab-case) matching `docs/planning/work/features/<feature-slug>/`.
- If the user provides a display name, instruct them to run `/discuss "<display name>"` first to derive the slug.

### Step 1: Load Context

1. Read `docs/planning/PROJECT.md` for patterns
2. Read `docs/planning/work/features/$ARGUMENTS/CONTEXT.md` and `CONTEXT.json` for decisions
3. Load current position from memory:
   ```bash
   python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"
   ```

If CONTEXT.md doesn't exist, ask user to run `/discuss $ARGUMENTS` first or confirm they want to proceed without it.

### Step 2: Identify Boundaries

Split work by:
- **Service boundary** (gateway, service-a, service-b, frontend)
- **Layer boundary** (API, business logic, data, UI)
- **Risk boundary** (safe refactors vs. new functionality)

Each plan should be completable in one fresh Claude session.

### Principle Reminder

Apply **Karpathy Principles** (see CLAUDE.md) while planning:

- Think Before Coding (surface tradeoffs)
- Simplicity First (minimum viable plan)
- Goal-Driven Execution (explicit verify commands)

### Step 3: Create Plans

For each plan, create:

- `docs/planning/work/features/$ARGUMENTS/NN-PLAN.md`
- `docs/planning/work/features/$ARGUMENTS/NN-PLAN.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per plan: `NN-PLAN.md` + `NN-PLAN.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Plan size**: `tasks.length` MUST be **≤ 3**.
- **Task quality**: each task MUST have explicit `files[]` and `verify[]`. For monorepos, prefer `task.cwd`.
- **Validation**: run `python3 scripts/workflow_validate.py` before moving to `/implement`.

`NN-PLAN.json` contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "planNumber": "01",
  "goal": "One sentence goal",
  "tasks": [
    {
      "name": "Task name",
      "cwd": "packages/api (optional; recommended for monorepos)",
      "files": ["path/to/file.ts"],
      "action": "Specific instructions",
      "verify": ["npm test --silent"],
      "blockedBy": [0]
    }
  ],
  "planVerify": ["npm test --silent"],
  "commitMessage": "feat(websocket-notifications): ...",
  "timestamp": "2026-01-24T00:00:00Z"
}
```

**`blockedBy` semantics (optional field):**
- Type: `number[]` — zero-based indices into the same plan's `tasks` array
- Meaning: this task cannot start until ALL referenced tasks are completed
- Default: `[]` (empty) — task can run immediately in parallel
- Example: `"blockedBy": [0, 1]` means "wait for task 0 and task 1 to finish first"
- Used by `/team implement` to set `addBlockedBy` on TaskList entries
- In serial `/implement`, tasks are executed in array order regardless of `blockedBy`

For the human plan, create `docs/planning/work/features/$ARGUMENTS/NN-PLAN.md`:

```markdown
# Plan NN: [Short Title]

## Goal
[One sentence: what this plan delivers]

## Prerequisites
- [ ] Plan NN-1 complete (if dependent)
- [ ] [Any other prerequisites]

## Tasks

### Task 1: [Name]
**Files:** `path/to/file.ts`, `path/to/other.ts`
**Action:**
[Specific instructions. Reference decisions from CONTEXT.md]

**Verify:**
```bash
[Command to verify this task]
```

**Done when:** [Observable outcome]

### Task 2: [Name]
...

### Task 3: [Name]
...

## Verification

After all tasks:
```bash
[Commands to verify the plan is complete]
```

## Commit Message
```
feat($ARGUMENTS): [description]

- [bullet points of changes]
```

---
*Planned: [date]*
```

### Rules

1. **Max 3 tasks per plan** — More than 3? Split into another plan.
2. **Explicit file paths** — No ambiguity about what to touch.
3. **Verification per task** — How do we know it works?
4. **Reference CONTEXT.md** — Use the decisions, don't re-decide.
5. **Contracts required** — Every `NN-PLAN.md` must have a matching `NN-PLAN.json`.

### Step 4: Memory Integration (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), create issues for each task:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create, dep_add, show
from pathlib import Path
root = Path('.')
if is_initialized(root):
    # Read epic ID from CONTEXT.json if available
    epic_id = '<memoryEpicId from CONTEXT.json>'

    # Create a task for each plan task
    for i, task in enumerate(tasks):
        issue = create(
            task['name'],
            parent=epic_id,
            feature_slug='<feature-slug>',
            plan_number='<NN>',
            metadata={'files': task['files'], 'verify': task['verify']},
            root=root,
        )
        print(f'Task {i+1}: {issue.id}')

    # Add inter-task dependencies (if tasks are sequential)
    # dep_add(task2_id, task1_id, root=root)
"
```

Store each task's `memoryId` in `NN-PLAN.json`:

```json
{
  "...existing fields...",
  "memoryEpicId": "<plan-level-epic-id>",
  "tasks": [
    {
      "...existing fields...",
      "memoryId": "<task-issue-id>"
    }
  ]
}
```

Add inter-task dependencies with `dep_add()` when tasks must execute in order.

If memory is not initialized, skip this step — the command works identically without it.

## Output

After creating plans:
- List all plans with their goals
- Identify dependencies between plans
- Recommend execution order
- Note which plans can run in parallel (for Boris-style sessions)

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
