# Workflow Contract Integrity

Use this skill when authoring or reviewing planning artifacts.

## Goal

Keep planning contracts and rendered markdown aligned with no lifecycle drift.

## Checks

1. Contract validity:
- `CONTEXT.json`, `*-PLAN.json`, `*-SUMMARY.json`, `REVIEW.json` parse cleanly
- required fields exist and are non-empty

2. Plan integrity:
- max 3 tasks per plan
- each task has explicit `files[]`, `action`, `verify[]`
- dependency indices are valid and acyclic

3. Summary integrity:
- `changes[].file` are declared in corresponding plan task `files[]`
- if extra files were touched intentionally, update plan contract to reflect reality

4. Cross-link integrity:
- feature with plans has `CONTEXT.md/.json`
- review exists only after summary artifacts
- phase progression is coherent (`discuss -> plan -> implement -> review -> ship`)

5. Freshness integrity:
- enforce `WORKFLOW.json.freshness` thresholds for stale context/plan/summary

## Commands

```bash
python3 scripts/workflow_validate.py --json
python3 scripts/workflow_render.py <contract.json>
```

## Output

- Blockers: schema or lifecycle violations
- Warnings: drift/freshness risks
- Exact file edits needed to restore consistency
