# Plan: $ARGUMENTS
<!-- effort: medium -->

Create implementation plans for a feature. Keep each plan small (max 3 tasks).

## Your Task

Break `$ARGUMENTS` into atomic, executable plans.

### Naming Rule

- `$ARGUMENTS` must be the feature slug (`kebab-case`) matching `docs/planning/work/features/<feature-slug>/`.
- If user gives a display name, route through `/discuss "<display name>"` first.

### Step 0: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get $ARGUMENTS
```

Expected before `/plan`: `discuss` or `plan`.

### Step 1: Load Minimal Context

```bash
cat docs/planning/work/features/$ARGUMENTS/CONTEXT.json
python3 scripts/workflow_memory.py prime --limit 5
```

Open `CONTEXT.md` only if contract fields are insufficient.

### Step 2: Partition Work

Split by boundaries:
- service/component boundary
- layer boundary (API/domain/data/UI)
- risk boundary (safe refactor vs behavior change)

Use principles from `CLAUDE.md` (do not duplicate long explanations here).

### Step 3: Author `NN-PLAN.json` (Source of Truth)

Write:
- `docs/planning/work/features/$ARGUMENTS/NN-PLAN.json`

Required constraints:
- `schemaVersion`, `feature`, `planNumber`, `goal`, `tasks[]`, `planVerify[]`, `commitMessage`, `timestamp`
- `tasks.length <= 3`
- each task has explicit `files[]`, `action`, `verify[]`

Minimal contract shape:

```json
{
  "schemaVersion": 1,
  "feature": "feature-slug",
  "planNumber": "01",
  "goal": "One-sentence goal",
  "tasks": [
    {
      "name": "Task name",
      "cwd": "packages/api (optional)",
      "files": ["path/to/file.ts"],
      "action": "Specific instructions",
      "verify": ["npm test --silent"],
      "blockedBy": [0]
    }
  ],
  "planVerify": ["npm test --silent"],
  "commitMessage": "feat(feature-slug): ...",
  "timestamp": "2026-01-24T00:00:00Z"
}
```

`blockedBy` semantics:
- zero-based task indices in the same plan
- task starts only when all referenced tasks are complete
- optional; empty means runnable immediately

### Step 4: Render `NN-PLAN.md` from Contract

```bash
python3 scripts/workflow_render.py docs/planning/work/features/$ARGUMENTS/NN-PLAN.json
```

Then make any small human-readable edits needed (rationale/notes), while keeping JSON as source of truth.

### Step 5: Optional Memory Tracking

If memory is initialized, set feature phase and optionally create tracking issues:

```bash
python3 scripts/workflow_memory.py phase-set $ARGUMENTS plan
```

Optional task issue creation example:

```bash
python3 scripts/workflow_memory.py create "Task title" --type task --feature $ARGUMENTS --plan NN
```

### Step 6: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Plans created (`NN-PLAN.json` + `NN-PLAN.md`)
- Execution order/dependencies
- Which plans can run in parallel
