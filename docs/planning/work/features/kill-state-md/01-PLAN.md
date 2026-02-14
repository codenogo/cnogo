# Plan 01: Python Foundation

## Goal
Make the memory engine capable of fully replacing STATE.md by enhancing `prime()`, replacing `infer_feature_from_state()`, and updating validation rules.

## Prerequisites
- [x] `/discuss kill-state-md` complete (CONTEXT.md + CONTEXT.json)
- [x] Memory engine operational (`.cnogo/memory.db`)

## Tasks

### Task 1: Enhance prime() with Active Epic Details + Plan Progress
**Files:** `scripts/memory/context.py`
**Action:**
Add a new section to `prime()` output between the header and "In Progress" that shows active epics with:
- Feature slug
- Plan number (from `plan_number` field)
- Child task completion ratio (e.g., "2/3 tasks done")

Query: find epics (`issue_type='epic'`) with `status` in `('open', 'in_progress')`. For each, count children by status. Also show `metadata.get('handoff')` snippet if present (for session handoff — CONTEXT.md decision #2).

Keep total output under ~1500 tokens. Format:

```
### Active Epics
- `cn-xxx` Feature: my-feature (Plan 02) — 2/3 tasks done
  Handoff: "Working on auth module, next: add tests"
```

**Verify:**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import prime
from pathlib import Path
output = prime(root=Path('.'))
print(output)
# Should show Active Epics section with kill-state-md epic
assert 'kill-state-md' in output or 'Active Epics' in output or 'Features' in output
print('OK')
"
```

**Done when:** `prime()` output includes active epic details with plan progress and optional handoff snippet.

### Task 2: Replace infer_feature_from_state() with Memory Query
**Files:** `scripts/workflow_checks.py`
**Action:**
Replace the `infer_feature_from_state()` function (lines 50-65) with a new implementation that:
1. First tries memory: `list_issues(issue_type='epic', status='in_progress')` — return `feature_slug` of first match
2. Falls back to: `list_issues(issue_type='epic', status='open')` — return `feature_slug` of first match
3. Final fallback: parse branch name (e.g., `feature/foo-bar` → `foo-bar`)
4. Return `None` if nothing found

Import memory at function level (not top-level) to avoid import errors if memory package isn't available. Keep the function name for backward compat — callers don't change.

**Verify:**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
sys.path.insert(0, 'scripts')
from workflow_checks import infer_feature_from_state
from pathlib import Path
result = infer_feature_from_state(Path('.'))
print(f'Inferred feature: {result}')
# Should find kill-state-md from memory
assert result is not None, 'Should infer a feature from memory'
print('OK')
"
```

**Done when:** `infer_feature_from_state()` queries memory instead of parsing STATE.md, with branch-name fallback.

### Task 3: Update workflow_validate.py — Remove STATE.md Check, Add memory.db Check
**Files:** `scripts/workflow_validate.py`
**Action:**
At line 649, change:
```python
_require(root / "docs" / "planning" / "STATE.md", findings, "Missing planning doc STATE.md")
```
to:
```python
_require(root / ".cnogo" / "memory.db", findings, "Memory engine not initialized (run install.sh or python3 scripts/workflow_memory.py init)")
```

This enforces CONTEXT.md decision #7: memory.db is required, STATE.md is not.

**Verify:**
```bash
python3 scripts/workflow_validate.py
```

**Done when:** Validation passes without STATE.md, requires memory.db instead.

## Verification

After all tasks:
```bash
# prime() shows epics
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; from pathlib import Path; print(prime(root=Path('.')))"

# Feature inference works from memory
python3 -c "import sys; sys.path.insert(0,'.'); sys.path.insert(0,'scripts'); from workflow_checks import infer_feature_from_state; from pathlib import Path; r = infer_feature_from_state(Path('.')); print(f'Feature: {r}'); assert r"

# Validation passes
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(kill-state-md): enhance memory engine to replace STATE.md

- Enhance prime() with active epic details, plan progress, and handoff
- Replace infer_feature_from_state() with memory query + branch fallback
- Update workflow_validate.py: require memory.db instead of STATE.md
```

---
*Planned: 2026-02-14*
