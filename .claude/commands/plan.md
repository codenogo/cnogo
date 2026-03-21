# Plan: $ARGUMENTS
<!-- effort: medium -->

Create plans for a feature.

## Your Task

`$ARGUMENTS` must be the feature slug matching `docs/planning/work/features/<feature-slug>/`. If the user gives only a display name, route through `/discuss` first.

## Steps

1. **Branch**
   - Check `git branch --show-current` and `git status --porcelain`.
   - Planning must run on `feature/$ARGUMENTS`.
   - Dirty tree: stop. Missing branch: send the user to `/discuss` first.

2. **Load context**
   - Run `python3 .cnogo/scripts/workflow_memory.py phase-get $ARGUMENTS`; expected: `discuss` or `plan`.
   - Read `docs/planning/work/features/$ARGUMENTS/CONTEXT.json`.
   - Run `python3 .cnogo/scripts/workflow_memory.py prime --limit 5`.
   - Optional: `python3 .cnogo/scripts/workflow_memory.py graph-suggest-scope --keywords "<keywords>" --files "<relatedCode>" --json` to refine `files[]`.
   - Optional: `python3 .cnogo/scripts/workflow_memory.py profile-list --json`.

3. **Partition work**
   Split by boundary, layer, or risk. Use `.claude/skills/workflow-contract-integrity.md` and `.claude/skills/artifact-token-budgeting.md`.

4. **Write `NN-PLAN.json`**
   - Create `docs/planning/work/features/$ARGUMENTS/NN-PLAN.json`.
   - New plans use `schemaVersion: 3`.
   - Required fields: `schemaVersion`, `feature`, `planNumber`, `goal`, `tasks[]`, `planVerify[]`, `commitMessage`, `timestamp`; keep `tasks.length <= 3`.
   - Optional top-level `profile` selects delivery policy for `/implement`, `/review`, and `/ship`; use a string or `{ "name": "feature-delivery" }`.
   - Before finalizing, run `python3 .cnogo/scripts/workflow_memory.py profile-suggest $ARGUMENTS --plan <NN> --json`; if needed, stamp with `python3 .cnogo/scripts/workflow_memory.py profile-stamp $ARGUMENTS <NN>`.
   - If no profile fits, scaffold one with `python3 .cnogo/scripts/workflow_memory.py profile-init <profile-slug> --base feature-delivery`.
   - Each task needs `name`, `files[]`, `action`, `verify[]`, `microSteps[]`, and `tdd`.
   - For `schemaVersion >= 3`, each task also needs `contextLinks[]` pointing to the exact `CONTEXT.json` constraints or decisions it must satisfy.
   - `tdd` is either `required=true` with failing/passing verify commands or `required=false` with a reason.
   - For `schemaVersion >= 3`, `microSteps[]` must name at least one explicit error-path scenario when `tdd.required=true`.
   - `blockedBy` uses zero-based task indices.
   - `deletions` is optional; if used, leave a later task to absorb cleanup scope.
   - Keep `planVerify[]` feature-level; package lint/typecheck/test is auto-appended during `/implement`.

5. **Render `NN-PLAN.md`**
   Run `python3 .cnogo/scripts/workflow_render.py docs/planning/work/features/$ARGUMENTS/NN-PLAN.json`, then make only small readability edits in Markdown.

6. **Optional memory**
   If memory is initialized, run `python3 .cnogo/scripts/workflow_memory.py phase-set $ARGUMENTS plan`; this also backfills the feature Work Order. Optional: `create ... --plan NN`.

7. **Validate**
   Run `python3 .cnogo/scripts/workflow_validate.py --feature $ARGUMENTS`.

## Output

- plans created (`NN-PLAN.json` and `NN-PLAN.md`)
- resolved delivery profile / any stamped override
- execution order and dependencies
- which plans can run in parallel
