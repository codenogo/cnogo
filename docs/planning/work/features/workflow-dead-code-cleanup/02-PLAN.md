# Plan 02: Archive 3 orphaned/incomplete feature directories to declutter active feature space

## Goal
Archive 3 orphaned/incomplete feature directories to declutter active feature space

## Tasks

### Task 1: Create archive directory and move stale features
**Files:** `docs/planning/work/archive/event-hardening/`, `docs/planning/work/archive/context-engineering-fixes/`, `docs/planning/work/archive/overstory-workflow-patterns/`
**Action:**
Create docs/planning/work/archive/ directory. Move 3 stale feature directories from docs/planning/work/features/ to docs/planning/work/archive/: event-hardening (REVIEW-only, no CONTEXT/PLANs), context-engineering-fixes (CONTEXT + REVIEW but no PLANs/SUMMARYs), overstory-workflow-patterns (3 PLANs without SUMMARYs, last touched 2026-02-14). Use git mv to preserve history.

**Verify:**
```bash
test -d docs/planning/work/archive/event-hardening
test -d docs/planning/work/archive/context-engineering-fixes
test -d docs/planning/work/archive/overstory-workflow-patterns
test ! -d docs/planning/work/features/event-hardening
test ! -d docs/planning/work/features/context-engineering-fixes
test ! -d docs/planning/work/features/overstory-workflow-patterns
```

**Done when:** [Observable outcome]

### Task 2: Close related memory issues for archived features
**Files:** `.cnogo/issues.jsonl`
**Action:**
Close the overstory-workflow-patterns epic (cn-12vmyu0) and its 3 child tasks (cn-12vmyu0.1, cn-12vmyu0.2, cn-12vmyu0.3) with reason 'archived — stale feature moved to archive'. No memory issues exist for event-hardening or context-engineering-fixes. Closing updates .cnogo/issues.jsonl via auto-export.

**Verify:**
```bash
python3 .cnogo/scripts/workflow_memory.py show cn-12vmyu0 2>&1 | grep -q closed
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
ls docs/planning/work/archive/
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
chore(planning): archive 3 stale feature directories
```
