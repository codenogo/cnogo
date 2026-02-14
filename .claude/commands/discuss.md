# Discuss: $ARGUMENTS
<!-- effort: high -->

Capture implementation decisions before any planning or coding begins, and persist them as both human-readable markdown and a machine-checkable contract.

## Your Task

Analyse the feature "$ARGUMENTS" and identify gray areas that need decisions.

### Naming Rule (Enforced)

- Treat `$ARGUMENTS` as the **feature display name** (free text) unless the user explicitly provides a slug.
- The feature directory name MUST be a **feature slug** in kebab-case: lowercase letters/numbers/hyphens (e.g. `websocket-notifications`).
- If the user input is not a slug (contains spaces, uppercase, or punctuation), derive a slug and ask for confirmation:
  - Example: `"Websocket Notifications"` → `websocket-notifications`

### Step 1: Read Context

1. Read `docs/planning/PROJECT.md` for constraints and patterns
2. Load current position from memory:
   ```bash
   python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"
   ```
3. Search codebase for related code: `rg -l "$ARGUMENTS" --type-add 'code:*.{java,ts,tsx,js,jsx,py,go}' -t code`
4. **Check External Context:**
   - If Jira/Linear MCP configured: Fetch ticket details
   - If Figma MCP configured: Fetch design specs

### Step 1b: Deep Research (When Needed)

If any of the following are true, run a research pass before finalizing decisions:

- The feature touches **security/auth**, payments, crypto, compliance, or other high-risk domains
- The approach depends on **external standards** (OAuth/OIDC, JWT, webhooks, PCI, etc.)
- The team is choosing between multiple architectural options (locks/queues/caching/idempotency)
- There is uncertainty about best practices or prior art

Run:

```bash
/research "$ARGUMENTS"
```

Then reference `docs/planning/work/research/<slug>/RESEARCH.md` inside `CONTEXT.md` and include key conclusions in the decisions table.

### Step 2: Identify Decision Points

Based on the feature type, surface relevant questions:

**API/Backend features:**
- Request/response format preferences
- Error handling approach
- Retry/timeout behaviour
- Pagination strategy
- Caching approach

**Frontend features:**
- Layout and component structure
- Loading/empty/error states
- Interaction patterns
- Responsive behaviour
- Accessibility considerations

**Data/Integration features:**
- Data flow direction
- Transformation rules
- Failure modes
- Idempotency requirements

**Infrastructure features:**
- Scaling considerations
- Monitoring approach
- Rollback strategy

### Step 3: Conduct Discussion

For each decision point:
1. Present the question with options
2. Wait for user input
3. Record the decision

Keep asking until all gray areas are resolved or user says "done".

### Step 4: Create Context File

Create:

- `docs/planning/work/features/<feature-slug>/CONTEXT.md`
- `docs/planning/work/features/<feature-slug>/CONTEXT.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per artifact.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Slug correctness**: contracts must use the same `<feature-slug>` as the directory name.
- **Validation**: run `python3 scripts/workflow_validate.py` before moving to `/plan`.

`CONTEXT.json` contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "displayName": "Websocket Notifications",
  "featureId": "JIRA-123 (optional)",
  "research": ["docs/planning/work/research/<slug>/RESEARCH.md (optional)"],
  "decisions": [
    { "area": "api", "decision": "REST", "rationale": "..." }
  ],
  "constraints": ["..."],
  "openQuestions": ["..."],
  "relatedCode": ["path/to/file.ts"],
  "timestamp": "2026-01-24T00:00:00Z"
}
```

Create `docs/planning/work/features/<feature-slug>/CONTEXT.md`:

```markdown
# <displayName> - Implementation Context

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| [area] | [choice] | [why] |

## Constraints

- [Any constraints discovered]

## Open Questions

- [Anything to resolve during implementation]

## Related Code

- `path/to/file.ts` - [why relevant]

## Research (optional)

- `docs/planning/work/research/<slug>/RESEARCH.md`

---
*Discussed: [date]*
```

### Step 5: Memory Integration (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), create a feature epic:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create
from pathlib import Path
root = Path('.')
if is_initialized(root):
    issue = create(
        'Feature: <feature-slug>',
        issue_type='epic',
        feature_slug='<feature-slug>',
        labels=['feature'],
        description='<one-line feature description>',
        root=root,
    )
    print(f'Memory epic: {issue.id}')
"
```

Store the returned `memoryEpicId` in `CONTEXT.json`:

```json
{
  "...existing fields...",
  "memoryEpicId": "<returned-id>"
}
```

If memory is not initialized, skip this step — the command works identically without it.

## Output

After creating CONTEXT.md, summarise:
- Key decisions made
- Constraints identified
- Ready for `/plan <feature-slug>`

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
