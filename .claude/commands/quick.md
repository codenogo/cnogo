# Quick: $ARGUMENTS
<!-- effort: low -->

Fast path for small fixes with full verification and artifacts.

## When to Use

Use for small, low-risk tasks (typically ≤1 hour, limited file set).

## Your Task

Execute `$ARGUMENTS` with minimal ceremony.

### Step 0: Branch

```bash
git checkout main
git pull
git checkout -b fix/<slug>
```

(Use `master` if that is the repo default.)

### Step 1: Scope

Identify likely files, expected behavior, and verification commands.
If scope looks large/risky, stop and switch to `/discuss` + `/plan`.

### Step 2: Write Quick Plan Contract

Create:
- `docs/planning/work/quick/NNN-<slug>/PLAN.json`

Minimum fields:
- `schemaVersion`, `id`, `slug`, `goal`, `files[]`, `verify[]`, `timestamp`

Example:

```json
{
  "schemaVersion": 1,
  "id": "001",
  "slug": "fix-typo",
  "goal": "What this accomplishes",
  "files": ["path/to/file.ts"],
  "verify": ["npm test --silent"],
  "timestamp": "2026-01-24T00:00:00Z"
}
```

Render markdown plan:

```bash
python3 scripts/workflow_render.py docs/planning/work/quick/NNN-<slug>/PLAN.json
```

### Step 3: Implement + Verify

- Make the change
- Run task verify commands
- Run any targeted tests for impacted behavior

### Step 4: Write Summary Contract

Create:
- `docs/planning/work/quick/NNN-<slug>/SUMMARY.json`

Minimum fields:
- `schemaVersion`, `id`, `slug`, `outcome`, `changes[]`, `verification[]`, `commit`, `timestamp`

Render markdown summary:

```bash
python3 scripts/workflow_render.py docs/planning/work/quick/NNN-<slug>/SUMMARY.json
```

### Step 5: Optional Memory Tracking

If memory is initialized:

```bash
python3 scripts/workflow_memory.py create "$ARGUMENTS" --type quick --feature <feature-slug-if-known>
```

Then close when done:

```bash
python3 scripts/workflow_memory.py close <issue-id> --reason completed
```

### Step 6: Commit

```bash
git add -A
git commit -m "fix([scope]): $ARGUMENTS"
```

### Step 7: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- What changed
- Verification results
- Ready for `/ship` or follow-up `/quick`
