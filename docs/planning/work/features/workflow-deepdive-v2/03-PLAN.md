# Plan 03: Fix WORKFLOW.json agent specializations, extract bool-type-check helper, and fix performance-review self-reference

## Goal
Fix WORKFLOW.json agent specializations, extract bool-type-check helper, and fix performance-review self-reference

## Tasks

### Task 1: Fix WORKFLOW.json agent team compositions
**Files:** `docs/planning/WORKFLOW.json`
**Action:**
In WORKFLOW.json agentTeams.defaultCompositions, roles like 'code-reviewer', 'security-scanner', 'perf-analyzer', 'test-writer', 'docs-writer', 'refactorer', 'debugger-runtime', 'debugger-test', 'debugger-build' don't map to .claude/agents/ files (only implementer.md, debugger.md, resolver.md exist). Replace compositions with valid mappings: 'review' uses ['implementer', 'implementer', 'implementer'], 'fullstack' uses ['implementer', 'debugger', 'implementer', 'implementer'], 'debug' uses ['debugger', 'debugger', 'debugger']. Config-only fix per constraint.

**Micro-steps:**
- Map defaultCompositions roles to actual .claude/agents/ files (implementer, debugger, resolver)
- Replace undefined roles with valid agent names or generic 'implementer' references
- Validate JSON parses correctly

**TDD:**
- required: `false`
- reason: Config-only change validated by JSON parse and workflow_validate

**Verify:**
```bash
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); print('agents:', list(d['agentTeams']['defaultCompositions'].keys()))"
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Extract _is_positive_int helper in validate_core
**Files:** `.cnogo/scripts/workflow_validate_core.py`
**Action:**
In workflow_validate_core.py, add: def _is_positive_int(val: Any, *, allow_zero: bool = False) -> bool: return isinstance(val, int) and not isinstance(val, bool) and (val >= 0 if allow_zero else val > 0). Replace the ~20 occurrences of the expanded pattern. For negated checks like 'isinstance(val, bool) or not isinstance(val, int) or val <= 0', replace with 'not _is_positive_int(val)'. For zero-allowing checks, use _is_positive_int(val, allow_zero=True).

**Micro-steps:**
- Add _is_positive_int(val, *, allow_zero=False) helper function near top
- Replace ~20 occurrences of isinstance(val, bool) or not isinstance(val, int) pattern
- Verify all existing validations still produce same results

**TDD:**
- required: `false`
- reason: Pure DRY refactor with no behavior change; validated by workflow_validate producing identical results

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_validate_core.py
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Fix performance-review self-reference
**Files:** `.claude/skills/performance-review.md`
**Action:**
In performance-review.md Step B2 (line 38), remove the self-referential 'Apply `.claude/skills/performance-review.md` performance checklist:' line. The performance checklist items are already inline in lines 39-48 of the same file. Replace line 38 with a direct heading like 'Performance checklist:' to eliminate the circular reference.

**Micro-steps:**
- Locate Step B2 line 38: 'Apply .claude/skills/performance-review.md'
- Replace with inline checklist (the content is already there in lines 39-48)
- Remove the self-referential apply instruction

**TDD:**
- required: `false`
- reason: Documentation fix removing circular reference

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "import json; json.load(open('docs/planning/WORKFLOW.json'))"
python3 -m py_compile .cnogo/scripts/workflow_validate_core.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
fix(config): fix agent compositions, extract bool-type helper, fix performance-review self-ref
```
