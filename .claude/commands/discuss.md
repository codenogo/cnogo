# Discuss: $ARGUMENTS
<!-- effort: medium -->

Capture key implementation decisions before planning/coding.

## Your Task

Analyze `$ARGUMENTS`, resolve gray areas with the user, and persist decisions.

### Naming Rule

- Treat `$ARGUMENTS` as display name unless user explicitly gives a slug.
- Feature directory must use kebab-case slug: `docs/planning/work/features/<feature-slug>/`.

### Step 0: Branch Bootstrap (Feature Isolation)

Derive `<feature-slug>` first (kebab-case), then ensure the active branch is `feature/<feature-slug>`.

```bash
git branch --show-current
git status --porcelain
```

**Step 0a: Clean up merged branches** before creating new work:

```bash
git branch --merged main
```

Delete any local branches already merged into main (excluding `main` itself):

```bash
git branch --merged main | grep -v '^\*\|main' | xargs -r git branch -d
git remote prune origin
```

Report deleted branches if any.

**Step 0b: Switch or create feature branch:**

Rules:
- If already on `feature/<feature-slug>`, pull latest: `git pull --ff-only` (ignore failure if no upstream yet), then continue.
- If a branch switch is needed and working tree is dirty, stop and ask user to commit/stash first (do not continue on wrong branch).
- If `feature/<feature-slug>` exists locally, switch and sync: `git switch feature/<feature-slug> && git pull --ff-only` (ignore failure if no upstream yet).
- Else create it from default branch:

```bash
git switch main || git switch master
git pull --ff-only
git switch -c feature/<feature-slug>
```

Report final active branch before writing artifacts.

### Step 1: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get <feature-slug>
```

Expected before `/discuss`: `discuss` (or `plan` when revisiting).

### Step 2: Read Lightweight Context

```bash
cat docs/planning/PROJECT.md
python3 scripts/workflow_memory.py prime --limit 5
rg -l "$ARGUMENTS" --type-add 'code:*.{java,ts,tsx,js,jsx,py,go}' -t code
```

### Step 2b: Research Only When Needed

If decisions depend on external standards/best-practices/high-risk domains:

```bash
/research "$ARGUMENTS"
```

Reference resulting research artifact in context contracts.

### Step 3: Drive Decision Conversation

Ask focused questions, then record final choices in these buckets:
- architecture/API shape
- data flow and failure handling
- UX/error behavior (if frontend)
- operational concerns (observability/rollback/risk)

Stop once open risk is low enough to plan.

### Step 4: Persist Contracts (Source of Truth)

Create:
- `docs/planning/work/features/<feature-slug>/CONTEXT.json`
- `docs/planning/work/features/<feature-slug>/CONTEXT.md`

`CONTEXT.json` minimum:
- `schemaVersion`, `feature`, `displayName`, `decisions[]`, `constraints[]`, `openQuestions[]`, `relatedCode[]`, `timestamp`
- optional: `featureId`, `research[]`, `memoryEpicId`

Minimal contract shape:

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "displayName": "Websocket Notifications",
  "decisions": [{ "area": "api", "decision": "REST", "rationale": "..." }],
  "constraints": ["..."],
  "openQuestions": ["..."],
  "relatedCode": ["path/to/file.ts"],
  "timestamp": "2026-01-24T00:00:00Z"
}
```

`CONTEXT.md` should be a concise human summary of the same information.

### Step 5: Optional Memory Epic

If memory is initialized, create feature epic and store ID in `CONTEXT.json`:

```bash
python3 scripts/workflow_memory.py create "Feature: <feature-slug>" --type epic --feature <feature-slug> --json
python3 scripts/workflow_memory.py phase-set <feature-slug> discuss
```

### Step 6: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Final decisions, constraints, and open questions
- Paths to `CONTEXT.md` and `CONTEXT.json`
- Confirmation feature is ready for `/plan <feature-slug>`
