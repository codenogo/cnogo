# Plan 01: Remove 11 dead function wrappers and outdated section comments from scripts/memory/__init__.py

## Goal
Remove 11 dead function wrappers and outdated section comments from scripts/memory/__init__.py

## Tasks

### Task 1: Remove dead function wrappers and __all__ entries
**Files:** `scripts/memory/__init__.py`
**Action:**
Remove 11 dead function wrappers (function definitions) and their __all__ entries: plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts, create_session, get_conflict_context, save_session, run_watchdog_checks, load_ledger, save_ledger, create_ledger, check_stale_tasks. Keep merge_session, cleanup_session, load_session, check_stale_issues (used externally). Remove the entire section blocks including the section header comments for Bridge (lines 936-979), the dead entries in Worktree (create_session, get_conflict_context, save_session — keep merge_session, cleanup_session, load_session), the dead entries in Health monitoring (check_stale_tasks, run_watchdog_checks — keep check_stale_issues), and the entire Ledger section (lines 1131-1158).

**Verify:**
```bash
python3 -c "from scripts.memory import *; print('import OK')"
python3 -c "from scripts.memory import merge_session, cleanup_session, load_session, check_stale_issues; print('kept exports OK')"
python3 -c "import scripts.memory; assert 'plan_to_task_descriptions' not in scripts.memory.__all__; print('dead exports removed OK')"
```

**Done when:** [Observable outcome]

### Task 2: Update outdated Phase 2/3 section header comments
**Files:** `scripts/memory/__init__.py`
**Action:**
Update line 838 comment 'Blocked Cache & Cycle Detection (inline — Phase 2 adds graph.py)' to 'Blocked Cache & Cycle Detection' (graph.py exists). Update line 876 comment 'Sync (stubs — Phase 3 adds sync.py / context.py)' to 'Sync & Context' (both modules exist).

**Verify:**
```bash
python3 -c "import scripts.memory; print('module loads OK')"
python3 scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "from scripts.memory import *; print('wildcard import OK')"
python3 -c "from scripts.memory import init, create, ready, claim, close, prime; print('core API OK')"
python3 scripts/workflow_validate.py
```

## Commit Message
```
refactor(memory): remove 11 dead function wrappers and outdated comments
```
