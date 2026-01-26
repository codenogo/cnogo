# Plan: $ARGUMENTS

Create implementation tasks for the feature. Each plan has ≤3 tasks to keep context fresh.

## Your Task

Break "$ARGUMENTS" into atomic, executable plans.

### Naming Rule

- `$ARGUMENTS` MUST be the **feature slug** (kebab-case) matching `docs/planning/work/features/<feature-slug>/`.
- If the user provides a display name, instruct them to run `/discuss "<display name>"` first to derive the slug.

### Step 1: Load Context

1. Read `docs/planning/PROJECT.md` for patterns
2. Read `docs/planning/work/features/$ARGUMENTS/CONTEXT.md` and `CONTEXT.json` for decisions
3. Read `docs/planning/STATE.md` for current position

If CONTEXT.md doesn't exist, ask user to run `/discuss $ARGUMENTS` first or confirm they want to proceed without it.

### Step 2: Identify Boundaries

Split work by:
- **Service boundary** (gateway, service-a, service-b, frontend)
- **Layer boundary** (API, business logic, data, UI)
- **Risk boundary** (safe refactors vs. new functionality)

Each plan should be completable in one fresh Claude session.

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
      "verify": ["npm test --silent"]
    }
  ],
  "planVerify": ["npm test --silent"],
  "commitMessage": "feat(websocket-notifications): ...",
  "timestamp": "2026-01-24T00:00:00Z"
}
```

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

### Step 4: Update State

Update `docs/planning/STATE.md`:
```
## Current Focus
- Feature: $ARGUMENTS
- Status: Planned
- Plans: 01, 02, 03 (list them)
- Next: /implement $ARGUMENTS 01
```

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
