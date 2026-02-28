# Plan 03: Update validator for new review schema with backward compatibility, and add principle reminders to implement command

## Goal
Update validator for new review schema with backward compatibility, and add principle reminders to implement command

## Tasks

### Task 1: Update workflow_validate_core.py for new config key and review schema
**Files:** `.cnogo/scripts/workflow_validate_core.py`
**Action:**
1) Rename _get_karpathy_checklist_level() to _get_operating_principles_level(). Read from enforcement.operatingPrinciples first, fall back to enforcement.karpathyChecklist for backward compat. 2) Update _validate_workflow_config() to validate enforcement.operatingPrinciples instead of karpathyChecklist (accept both during migration). 3) Remove _review_principles_cfg() and DEFAULT_REVIEW_PRINCIPLES and REVIEW_PRINCIPLES_REQUIRED_SCHEMA (no longer needed — principles are not review-scoped). 4) Rewrite _validate_ci_verification(): remove the Karpathy checklist check in REVIEW.md. Remove the mandatory principles[] validation in REVIEW.json. Instead validate that new review schema fields exist when schemaVersion >= 3: securityFindings, performanceFindings, patternCompliance (arrays). For old REVIEW.json with principles[] (schemaVersion < 3), accept silently (backward compat). 5) Update validate_repo() and _validate_features() to pass the renamed level variable.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_validate_core.py
! grep -q 'karpathy' scripts/workflow_validate_core.py
! grep -q 'Karpathy' scripts/workflow_validate_core.py
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Add principle reminders to implement.md command
**Files:** `.claude/commands/implement.md`
**Action:**
In Step 3 (Execute Tasks), after 'announce task start' (item 1), add: '1b. Review applicable Operating Principles from .claude/CLAUDE.md before coding (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution)'. Keep it concise — one line, not a full checklist.

**Verify:**
```bash
grep -q 'Operating Principles' .claude/commands/implement.md
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/workflow_validate_core.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(review-workflow): update validator for new review schema with backward compat + implement principles
```
