# Research: $ARGUMENTS
<!-- effort: high -->

Produce a durable research artifact that reduces decision uncertainty.

## Arguments

`/research <topic>`

## Your Task

1. Read policy from `docs/planning/WORKFLOW.json`:
- `off`: stop and explain how to enable
- `local`: repo-only sources
- `mcp`: repo + configured MCP sources
- `web`/`auto`: include web if environment allows

2. Create artifact folder:
- `docs/planning/work/research/<slug>/RESEARCH.md`
- `docs/planning/work/research/<slug>/RESEARCH.json`

3. Gather evidence in this order:
- repo code/docs/history (`rg`, `git log`)
- MCP systems (if enabled)
- web primary sources (official docs/specs)

4. Synthesize for this project:
- options and fit criteria
- risks/failure modes
- recommendation with tradeoffs
- open questions

5. Write contracts:
- `RESEARCH.md`: concise narrative
- `RESEARCH.json`: `schemaVersion`, `topic`, `slug`, `timestamp`, `mode`, `sources[]`, `summary[]`, `recommendation`

6. Validate:
```bash
python3 scripts/workflow_validate.py --json
```

## Output

- Artifact paths
- Top conclusions
- Recommended next command (`/discuss <topic>`)
