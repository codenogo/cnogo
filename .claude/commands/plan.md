# Plan: $ARGUMENTS
<!-- effort: medium -->

Create implementation plans for a feature. Keep each plan small (max 3 tasks).

## Your Task

Break `$ARGUMENTS` into atomic, executable plans.

### Naming Rule

- `$ARGUMENTS` must be the feature slug (`kebab-case`) matching `docs/planning/work/features/<feature-slug>/`.
- If user gives a display name, route through `/discuss "<display name>"` first.

### Step 0: Branch Alignment

Plan work must run on `feature/$ARGUMENTS`.

```bash
git branch --show-current
git status --porcelain
```

Rules:
- If already on `feature/$ARGUMENTS`, continue.
- If switching branches is needed and working tree is dirty, stop and ask user to commit/stash first.
- If `feature/$ARGUMENTS` exists locally, switch to it.
- Else create it from default branch:

```bash
git switch main || git switch master
git pull --ff-only
git switch -c feature/$ARGUMENTS
```

### Step 1: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get $ARGUMENTS
```

Expected before `/plan`: `discuss` or `plan`.

### Step 2: Load Minimal Context

```bash
cat docs/planning/work/features/$ARGUMENTS/CONTEXT.json
python3 scripts/workflow_memory.py prime --limit 5
```

### Step 3: Partition Work

Split by boundaries:
- service/component
- layer (API/domain/data/UI)
- risk (refactor vs behavior change)

Apply:
- `.claude/skills/workflow-contract-integrity.md` for contract/lifecycle correctness
- `.claude/skills/artifact-token-budgeting.md` to keep plans concise

### Step 4: Author `NN-PLAN.json` (Source of Truth)

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

### Step 5: Render `NN-PLAN.md` from Contract

```bash
python3 scripts/workflow_render.py docs/planning/work/features/$ARGUMENTS/NN-PLAN.json
```

Then make any small human-readable edits needed (rationale/notes), while keeping JSON as source of truth.

### Step 6: Optional Memory Tracking

If memory is initialized, set feature phase and optionally create tracking issues:

```bash
python3 scripts/workflow_memory.py phase-set $ARGUMENTS plan
```

Optional task issue creation example:

```bash
python3 scripts/workflow_memory.py create "Task title" --type task --feature $ARGUMENTS --plan NN
```

### Step 7: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Plans created (`NN-PLAN.json` + `NN-PLAN.md`)
- Execution order/dependencies
- Which plans can run in parallel
