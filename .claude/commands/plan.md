# Plan: $ARGUMENTS
<!-- effort: medium -->

Create implementation plans for a feature. Keep each plan small (max 3 tasks).

## Your Task

Break `$ARGUMENTS` into atomic, executable plans.

### Naming Rule

- `$ARGUMENTS` must be the feature slug (`kebab-case`) matching `docs/planning/work/features/<feature-slug>/`.
- If user gives a display name, route through `/discuss "<display name>"` first.

### Step 0: Branch Verification (verify-only — do NOT create)

Plan work must run on `feature/$ARGUMENTS`. The branch should already exist from `/discuss`.

```bash
git branch --show-current
git status --porcelain
```

Rules:
- If already on `feature/$ARGUMENTS`, continue.
- If `feature/$ARGUMENTS` exists locally but is not the current branch:
  - If working tree is dirty, stop and ask user to commit/stash first.
  - Else switch to it and pull latest: `git switch feature/$ARGUMENTS && git pull --ff-only`
- If `feature/$ARGUMENTS` does **not** exist, stop and tell the user to run `/discuss $ARGUMENTS` first to create the branch.

**Step 0a: Clean up merged branches**

```bash
git branch --merged main | grep -v '^\*\|main' | xargs -r git branch -d
git remote prune origin
```

Report deleted branches if any.

### Step 1: Phase Check (Warn, Do Not Block)

```bash
python3 .cnogo/scripts/workflow_memory.py phase-get $ARGUMENTS
```

Expected before `/plan`: `discuss` or `plan`.

### Step 2: Load Minimal Context

```bash
cat docs/planning/work/features/$ARGUMENTS/CONTEXT.json
python3 .cnogo/scripts/workflow_memory.py prime --limit 5
```

### Step 2b: Graph Scope Suggestions

```bash
python3 .cnogo/scripts/workflow_memory.py graph-suggest-scope --keywords "<feature keywords from CONTEXT.json>" --files "<relatedCode from CONTEXT.json>" --json
```

Use suggestions when authoring task `files[]` arrays. Advisory only — graph failures don't block planning.

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
- `schemaVersion: 2`, `feature`, `planNumber`, `goal`, `tasks[]`, `planVerify[]`, `commitMessage`, `timestamp`
- `tasks.length <= 3`; each has `files[]`, `action`, `verify[]`, `microSteps[]`, `tdd`
- `tdd`: `required=true` with `failingVerify`/`passingVerify`, or `required=false` with `reason`
- `blockedBy`: zero-based task indices (optional; empty = runnable immediately)
- `deletions`: optional list of files deleted; bridge auto-expands next task's scope

### Step 5: Render `NN-PLAN.md` from Contract

```bash
python3 .cnogo/scripts/workflow_render.py docs/planning/work/features/$ARGUMENTS/NN-PLAN.json
```

Then make any small human-readable edits needed (rationale/notes), while keeping JSON as source of truth.

### Step 6: Optional Memory Tracking

If memory is initialized, set feature phase and optionally create tracking issues:

```bash
python3 .cnogo/scripts/workflow_memory.py phase-set $ARGUMENTS plan
```

Optional task issue creation example:

```bash
python3 .cnogo/scripts/workflow_memory.py create "Task title" --type task --feature $ARGUMENTS --plan NN
```

### Step 7: Validate

```bash
python3 .cnogo/scripts/workflow_validate.py --feature $ARGUMENTS
```

## Output

- Plans created (`NN-PLAN.json` + `NN-PLAN.md`)
- Execution order/dependencies
- Which plans can run in parallel
