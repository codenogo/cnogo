# Plan 04: Standardize command step numbering, fix implement.md gap, and add error recovery paths and scope boundaries

## Goal
Standardize command step numbering, fix implement.md gap, and add error recovery paths and scope boundaries

## Tasks

### Task 1: Standardize Step 0 structure across commands
**Files:** `.claude/commands/discuss.md`, `.claude/commands/plan.md`, `.claude/commands/implement.md`, `.claude/commands/review.md`, `.claude/commands/ship.md`
**Action:**
Audit all 5 core command files for Step 0 consistency. Standardize: discuss.md has Step 0 (branch bootstrap), 0a (cleanup), 0b (switch/create). plan/implement/review/ship have Step 0 (verify-only, no create), 0a (cleanup). Fix any missing or misnamed sub-steps. Ensure the 'verify-only — do NOT create' annotation is present on plan/implement/review/ship.

**Micro-steps:**
- Audit Step 0 sub-step numbering in each command file
- Ensure consistent pattern: Step 0 = branch verify, Step 0a = merged branch cleanup
- Ensure implement/review/ship use verify-only pattern (no branch creation)
- Verify token budget compliance after changes

**TDD:**
- required: `false`
- reason: Documentation standardization validated by workflow_validate token budgets

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Fix implement.md Step 2a gap and add error recovery
**Files:** `.claude/commands/implement.md`
**Action:**
In implement.md: (1) In Step 2c (team mode routing), add fallback: 'If team delegation fails, fall back to serial execution with a warning.' (2) In Step 3, strengthen error recovery: on task verify failure, run checkpoint command, inspect history, fix, retry (max 2 attempts). After 2 failures, stop and report the failure with context instead of continuing. (3) Add note about partial completion: 'If stopping mid-plan, ensure completed tasks have SUMMARY entries and memory is synced.'

**Micro-steps:**
- Review Step 2c (team mode routing) for missing fallback
- Add explicit serial fallback guidance when --team fails
- Add Step 3 error recovery: retry guidance (max 2 attempts) and escalation path
- Add checkpoint/resume guidance for partial completion

**TDD:**
- required: `false`
- reason: Documentation fix adding missing guidance sections

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Add quick scope boundaries and review stage gate docs
**Files:** `.claude/commands/quick.md`, `.claude/commands/review.md`
**Action:**
In quick.md Step 1 (Scope), add explicit boundaries: if scope exceeds 5 files or touches core data models or requires migration, stop and switch to /discuss + /plan. In review.md Step 3, after spec-compliance stage, add bold instruction: '**If spec stage is `fail`, STOP and return blockers. Do NOT proceed to Step 4 code quality.**' Ensure this is unambiguous.

**Micro-steps:**
- In quick.md Step 1, add explicit scope boundary criteria
- Add escalation triggers: when to switch to /discuss + /plan
- In review.md, add explicit STOP instruction if spec-compliance stage fails

**TDD:**
- required: `false`
- reason: Documentation improvement adding missing boundary definitions

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
docs(commands): standardize step numbering, fix implement gap, add error recovery and scope boundaries
```
