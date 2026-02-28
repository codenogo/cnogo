# Plan 01: Config, Schema, and Validation Groundwork

## Goal
Add the `staleIndicatorMinutes` config to WORKFLOW.json, set debugger model to opus, and update `workflow_validate.py` to accept the new `parallelizable` plan field.

## Prerequisites
- [x] CONTEXT.md decisions finalized

## Tasks

### Task 1: Set debugger model to opus and add model comments
**Files:** `.claude/agents/implementer.md`, `.claude/agents/debugger.md`
**Action:**
In `debugger.md`, change the YAML frontmatter `model: inherit` to `model: opus`. Per CONTEXT.md decision: "Opus best for complex reasoning and root cause analysis."

In both agent files, add a brief comment after the frontmatter explaining the model choice:
- `implementer.md`: sonnet — fast, cost-effective for straightforward implementation tasks
- `debugger.md`: opus — best reasoning for root cause analysis and complex debugging

Do not change any other content in either file.

**Verify:**
```bash
grep -q 'model: opus' .claude/agents/debugger.md && echo "PASS: debugger model is opus" || echo "FAIL"
grep -q 'model: sonnet' .claude/agents/implementer.md && echo "PASS: implementer model is sonnet" || echo "FAIL"
```

**Done when:** `debugger.md` has `model: opus`, both agents have model rationale comments.

### Task 2: Add staleIndicatorMinutes to WORKFLOW.json
**Files:** `docs/planning/WORKFLOW.json`
**Action:**
Add `"staleIndicatorMinutes": 10` inside the existing `"agentTeams"` object in WORKFLOW.json. Per CONTEXT.md: "agentTeams.staleIndicatorMinutes in WORKFLOW.json — project-level, easy to tune."

The `agentTeams` section should look like:
```json
"agentTeams": {
    "enabled": true,
    "delegateMode": true,
    "staleIndicatorMinutes": 10,
    "defaultCompositions": { ... }
}
```

Do not change any other fields.

**Verify:**
```bash
python3 -c "import json; cfg=json.load(open('docs/planning/WORKFLOW.json')); v=cfg['agentTeams']['staleIndicatorMinutes']; assert v == 10, f'Expected 10 got {v}'; print('PASS: staleIndicatorMinutes=10')"
```

**Done when:** WORKFLOW.json has `agentTeams.staleIndicatorMinutes: 10`.

### Task 3: Update workflow_validate.py for new fields
**Files:** `.cnogo/scripts/workflow_validate.py`
**Action:**
Two changes:

1. **WORKFLOW.json validation** — In `_validate_workflow_config()`, after the existing `agentTeams` validation (if one exists) or within the function, add validation for `agentTeams.staleIndicatorMinutes`: if present, must be an integer > 0. Warn if not.

2. **Plan JSON validation** — In `_validate_plan_contract()`, accept an optional top-level `"parallelizable"` boolean field. If present and not a boolean, emit a WARN. Do not require it — existing plans without it must remain valid.

Both changes are additive — they validate new optional fields, not reject old contracts.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_validate.py && echo "PASS: compiles" || echo "FAIL"
python3 .cnogo/scripts/workflow_validate.py && echo "PASS: validates" || echo "FAIL"
```

**Done when:** `workflow_validate.py` compiles, validates the repo without new errors, and would warn on invalid `staleIndicatorMinutes` or `parallelizable` types.

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_validate.py
grep -q 'model: opus' .claude/agents/debugger.md
python3 -c "import json; cfg=json.load(open('docs/planning/WORKFLOW.json')); assert 'staleIndicatorMinutes' in cfg['agentTeams']"
```

## Commit Message
```
feat(multi-agent-enhancements): config, schema, and validation groundwork

- Set debugger agent model to opus for better root cause analysis
- Add agentTeams.staleIndicatorMinutes to WORKFLOW.json
- Update workflow_validate.py to accept parallelizable plan field
```

---
*Planned: 2026-02-14*
