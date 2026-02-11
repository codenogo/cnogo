# Plan 04: Validator Refactor & Final Cleanup

## Goal
Split the 233-line validate_repo() function, optimize rglob usage, and update WORKFLOW.schema.json.

## Prerequisites
- [ ] Plan 03 complete (workflow_utils.py must exist for imports)

## Tasks

### Task 1: Split validate_repo() into focused functions
**Files:** `scripts/workflow_validate.py`
**Action:**
Refactor the 233-line `validate_repo()` function (finding #19) into smaller, focused functions:

1. `_validate_features(root, errors, warnings)` — Feature directory validation
2. `_validate_quick_tasks(root, errors, warnings)` — Quick task validation
3. `_validate_research(root, errors, warnings)` — Research artifact validation
4. `_validate_brainstorm(root, errors, warnings)` — Brainstorm artifact validation
5. `_validate_ci_verification(root, errors, warnings)` — CI verification validation

Keep `validate_repo()` as the orchestrator that calls these functions.

**Verify:**
```bash
python3 scripts/workflow_validate.py
grep -c 'def _validate_' scripts/workflow_validate.py  # ≥5
```

**Done when:** validate_repo() is an orchestrator calling focused sub-functions, validator still passes.

### Task 2: Optimize rglob with WORKFLOW.json packages
**Files:** `scripts/workflow_validate.py`
**Action:**
Optimize `_detect_repo_shape()` to avoid full-tree rglob on every run (finding #18):

1. If `WORKFLOW.json` has non-empty `packages[]`, use that directly instead of rglob.
2. Only fall back to rglob when `repoShape` is `"auto"` AND `packages` is empty.
3. Use `load_workflow()` from `workflow_utils.py` to read the config.

**Verify:**
```bash
python3 scripts/workflow_validate.py
python3 -c "
import scripts.workflow_validate as v
# Should not error
print('OK')
"
```

**Done when:** Validator uses packages[] from WORKFLOW.json when available, falls back to rglob only when needed.

### Task 3: Update WORKFLOW.schema.json and final cleanup
**Files:** `docs/planning/WORKFLOW.schema.json`, `.gitignore`
**Action:**
1. **Update WORKFLOW.schema.json** to include the `agentTeams` section schema (open question from CONTEXT.md):
   ```json
   "agentTeams": {
     "type": "object",
     "properties": {
       "enabled": { "type": "boolean" },
       "delegateMode": { "type": "boolean" },
       "defaultCompositions": { "type": "object" }
     }
   }
   ```

2. **Add sensitive file patterns to .gitignore** (open question from CONTEXT.md):
   - `*.pem`, `*.key`, `*.p12`, `*.pfx`
   - `id_rsa`, `id_ed25519`, `id_dsa`, `id_ecdsa`
   - `credentials.json`, `service-account*.json`

3. **Add blank lines between function definitions** in workflow_validate.py where missing (PEP 8, finding #12 from quality review).

**Verify:**
```bash
python3 -c "import json; json.load(open('docs/planning/WORKFLOW.schema.json')); print('schema OK')"
grep 'agentTeams' docs/planning/WORKFLOW.schema.json
grep '*.pem' .gitignore
python3 scripts/workflow_validate.py
```

**Done when:** Schema includes agentTeams, .gitignore covers sensitive files, PEP 8 spacing fixed, validator passes.

## Verification

After all tasks:
```bash
python3 scripts/workflow_validate.py
python3 -c "import json; json.load(open('docs/planning/WORKFLOW.schema.json')); print('OK')"
grep -c 'def _validate_' scripts/workflow_validate.py  # ≥5
```

## Commit Message
```
fix(review-findings-remediation): refactor validator, schema update, final cleanup

- Split 233-line validate_repo() into focused sub-functions
- Optimize repo shape detection to use WORKFLOW.json packages[] first
- Add agentTeams section to WORKFLOW.schema.json
- Add sensitive file patterns to .gitignore
- Fix PEP 8 spacing in workflow_validate.py
```

---
*Planned: 2026-02-10*
