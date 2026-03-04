# Plan 02: Enforce forward-only phase transitions and add plan validation gate before memory issue creation

## Goal
Enforce forward-only phase transitions and add plan validation gate before memory issue creation

## Tasks

### Task 1: Enforce forward-only phase transitions
**Files:** `.cnogo/scripts/memory/storage.py`
**Action:**
In storage.py, add validate_phase_transition(current: str, target: str) -> bool that compares WORKFLOW_PHASES.index(current) vs WORKFLOW_PHASES.index(target). If target < current: print warning to stderr and return False. If equal: return True (idempotent). If forward: return True. Wire into set_feature_phase(): call get_feature_phase() first, then validate_phase_transition(), then proceed with UPDATE regardless (advisory mode per open question).

**Micro-steps:**
- Add validate_phase_transition(current, target) using WORKFLOW_PHASES index comparison
- Allow same-phase idempotent updates
- Print stderr warning on backward transitions (advisory mode)
- Wire validation into set_feature_phase() before UPDATE

**TDD:**
- required: `false`
- reason: Advisory mode — prints warning but does not block; no test framework in stdlib-only project

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/memory/storage.py
python3 .cnogo/scripts/workflow_memory.py phase-get workflow-deepdive-v2
```

**Done when:** [Observable outcome]

### Task 2: Add plan validation gate in bridge
**Files:** `.cnogo/scripts/memory/bridge.py`
**Action:**
In bridge.py, add _validate_plan_structure(plan: dict) that checks: (1) 'feature' is non-empty string, (2) 'planNumber' is non-empty string, (3) 'tasks' is a list with 1-3 entries, (4) each task has non-empty 'name', non-empty 'files' list, non-empty 'action' string. Raise ValueError with specific message for each violation. Call at top of plan_to_task_descriptions() before the task loop.

**Micro-steps:**
- Add _validate_plan_structure() helper at top of plan_to_task_descriptions()
- Check required fields: feature, planNumber, non-empty tasks list (len <= 3)
- Check each task has non-empty name, files, action
- Raise ValueError with clear message on malformed plans

**TDD:**
- required: `false`
- reason: Validation gate for internal bridge function; all callers pass well-formed plans in normal flow

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/memory/bridge.py
```

**Done when:** [Observable outcome]

### Task 3: Add phase check to ship-ready gate
**Files:** `.cnogo/scripts/workflow_checks_core.py`
**Action:**
In workflow_checks_core.py _cmd_ship_ready(), add a 'phase-check' entry to the checks list. Import memory storage or use subprocess to get current phase. If phase is 'review' or 'ship': status='pass'. If phase is 'implement' or earlier: status='warn' with details explaining the feature hasn't been reviewed yet. Add this check early in the function, after the feature_dir existence check.

**Micro-steps:**
- In _cmd_ship_ready(), add phase validation check early in the checks list
- Read current phase via storage.get_feature_phase()
- Warn if phase is not 'review' or 'ship'
- Add check result to the checks list output

**TDD:**
- required: `false`
- reason: Adding advisory check to existing gate; does not change pass/fail behavior for correctly phased features

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_checks_core.py
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile .cnogo/scripts/memory/storage.py
python3 -m py_compile .cnogo/scripts/memory/bridge.py
python3 -m py_compile .cnogo/scripts/workflow_checks_core.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
fix(memory): forward-only phase transitions, plan validation gate, ship-ready phase check
```
