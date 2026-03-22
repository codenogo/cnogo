# Brainstorm: $ARGUMENTS
<!-- effort: high -->

Compatibility wrapper for the canonical `/shape` workflow.

## Arguments

`/brainstorm <idea>`

## Your Task

Follow the exact `/shape "$ARGUMENTS"` workflow.

Use `/brainstorm` only as a backward-compatible entrypoint for users and repos that still reach for the old name.

1. Read any existing legacy `BRAINSTORM.*` artifact if present.
2. Migrate forward into canonical `SHAPE.md` and `SHAPE.json`.
3. Keep feature materialization behavior identical to `/shape`:
- create `FEATURE.md`, `FEATURE.json`, `CONTEXT.md`, and `CONTEXT.json` immediately for any `ready` candidate
- queue that feature with `python3 .cnogo/scripts/workflow_memory.py work-sync <feature-slug>`
- do not create new legacy `BRAINSTORM.*` artifacts for fresh work
- keep the workspace-first output contract identical to `/shape`: stay in shaping by default, with ready work entering the queue instead of handing off to `/discuss`

4. Validate:
```bash
python3 .cnogo/scripts/workflow_validate.py --json
```

## Output

- same workspace-first output contract as `/shape`
- ready work is emitted and queued directly from shape
