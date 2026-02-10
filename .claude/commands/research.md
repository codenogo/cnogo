# Research: $ARGUMENTS
<!-- effort: max -->

Deep research for a feature/bug/decision. Produces a durable artifact that `/discuss` can reference to reduce uncertainty.

## Arguments

`/research <topic>`

Examples:

- `/research oauth token refresh best practices`
- `/research postgres advisory locks vs distributed locks`
- `/research react query cache invalidation patterns`

## Your Task

Research "$ARGUMENTS" deeply, using the best available sources (repo + internal docs + optional web/MCP), and write a research artifact suitable for engineering decisions.

### Step 0: Respect Project Policy

Read `docs/planning/WORKFLOW.json` and follow research settings:

- If `research.mode` is `"off"`: do not perform research; explain how to enable it.
- If `research.mode` is `"local"`: use repo-only sources.
- If `research.mode` is `"mcp"`: use MCP sources (Jira/Confluence/Notion/etc.) if configured.
- If `research.mode` is `"web"` or `"auto"`: use web research only if allowed in the environment; otherwise fall back to local + MCP.

### Step 1: Create Research Folder

Create:

- `docs/planning/work/research/<slug>/RESEARCH.md`
- `docs/planning/work/research/<slug>/RESEARCH.json`

Slug rules: kebab-case (`oauth-token-refresh`).

### Step 2: Gather Sources

Use the following, in order:

1. **Repo-local** (always):
   - `rg` search for relevant code, ADRs, docs, configs
   - `git log -p` for recent changes and historical context
2. **MCP sources** (if enabled/configured):
   - Jira/Linear tickets, Confluence/Notion docs, Sentry incidents, etc.
3. **Web sources** (if enabled/available):
   - Official docs, RFCs/standards, vendor docs, reputable engineering blogs

### Step 3: Synthesize Findings

Focus on:

- What the “right” options are and when each is appropriate
- Risks, edge cases, failure modes
- Concrete recommendations for *this* project (tie back to `PROJECT.md` constraints)

### Step 4: Write RESEARCH.md

```markdown
# Research: $ARGUMENTS

**Date:** [YYYY-MM-DD]
**Mode:** local | mcp | web | auto

## Executive Summary
[5-10 bullet points of highest-signal conclusions]

## Context (Project-Specific)
[How this connects to PROJECT.md constraints and current STATE]

## Options Considered

### Option A: [Name]
- **When to use**
- **Pros**
- **Cons**
- **Risks**

### Option B: [Name]
...

## Recommendation
[What to do + why + scope notes]

## Open Questions
- [ ] [Question]

## Sources
- [Source title] — [link or repo path] — [1-2 sentence relevance]
```

### Step 5: Write RESEARCH.json (Contract)

```json
{
  "schemaVersion": 1,
  "topic": "oauth token refresh best practices",
  "slug": "oauth-token-refresh",
  "timestamp": "2026-01-24T00:00:00Z",
  "mode": "local|mcp|web|auto",
  "sources": [
    { "type": "repo|mcp|web", "ref": "path/or/url", "title": "..." }
  ],
  "summary": ["...high-signal bullets..."],
  "recommendation": "..."
}
```

### Step 6: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- Where the research artifact was written
- Top conclusions + recommendation
- How it should influence `/discuss` decisions

