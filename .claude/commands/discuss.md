# Discuss: $ARGUMENTS
<!-- effort: medium -->

Capture key implementation decisions before planning/coding.

## Your Task

Analyze `$ARGUMENTS`, resolve gray areas with the user, and persist decisions.

### Naming Rule

- Treat `$ARGUMENTS` as display name unless user explicitly gives a slug.
- Feature directory must use kebab-case slug: `docs/planning/work/features/<feature-slug>/`.

### Step 0: Phase Check (Warn, Do Not Block)

```bash
python3 scripts/workflow_memory.py phase-get <feature-slug>
```

Expected before `/discuss`: `discuss` (or `plan` when revisiting).

### Step 1: Read Lightweight Context

```bash
cat docs/planning/PROJECT.md
python3 scripts/workflow_memory.py prime --limit 5
rg -l "$ARGUMENTS" --type-add 'code:*.{java,ts,tsx,js,jsx,py,go}' -t code
```

### Step 1b: Research Only When Needed

If decisions depend on external standards/best-practices/high-risk domains:

```bash
/research "$ARGUMENTS"
```

Reference resulting research artifact in context contracts.

### Step 2: Drive Decision Conversation

Ask focused questions, then record final choices in these buckets:
- architecture/API shape
- data flow and failure handling
- UX/error behavior (if frontend)
- operational concerns (observability/rollback/risk)

Stop once open risk is low enough to plan.

### Step 3: Persist Contracts (Source of Truth)

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

### Step 4: Optional Memory Epic

If memory is initialized, create feature epic and store ID in `CONTEXT.json`:

```bash
python3 scripts/workflow_memory.py create "Feature: <feature-slug>" --type epic --feature <feature-slug> --json
python3 scripts/workflow_memory.py phase-set <feature-slug> discuss
```

### Step 5: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Final decisions, constraints, and open questions
- Paths to `CONTEXT.md` and `CONTEXT.json`
- Confirmation feature is ready for `/plan <feature-slug>`
