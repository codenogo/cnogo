# Brainstorm: $ARGUMENTS
<!-- effort: high -->

Explore solution space before committing to implementation decisions.

## Arguments

`/brainstorm <idea>`

## Your Task

1. Load constraints:
- `docs/planning/PROJECT.md`
- `docs/planning/WORKFLOW.json`
- relevant skill files only when needed

2. Ask focused narrowing questions (3-7 at a time):
- user/job-to-be-done
- success criteria
- scope boundaries
- constraints (time, infra, compliance)
- major risks

3. Generate 2-4 candidate directions with explicit tradeoffs:
- who it serves
- in-scope/out-of-scope
- architecture sketch
- top risks + mitigations
- MVP slice

4. If uncertainty remains high (security, data, distributed systems), run `/research` and fold results in.

5. Write artifacts:
- `docs/planning/work/ideas/<slug>/BRAINSTORM.md`
- `docs/planning/work/ideas/<slug>/BRAINSTORM.json`

`BRAINSTORM.json` minimum fields:
- `schemaVersion`, `topic`, `slug`, `timestamp`
- `questionsAsked[]`, `constraints[]`
- `candidates[]` (`name`, `summary`, `risks[]`, `mvp[]`)
- `recommendation` (`primary`, `backup`)

6. Validate:
```bash
python3 scripts/workflow_validate.py --json
```

## Output

- 1-3 strongest options
- recommended option + why
- exact next command: `/discuss "<chosen-option>"`
