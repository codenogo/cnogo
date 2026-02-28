# Plan 01: Restore bridge.py with TaskDesc V2 output, add re-exports to __init__.py, and update worktree.py for V2 compatibility

## Goal
Restore bridge.py with TaskDesc V2 output, add re-exports to __init__.py, and update worktree.py for V2 compatibility

## Tasks

### Task 1: Restore bridge.py with V2 upgrade
**Files:** `.cnogo/scripts/memory/bridge.py`
**Action:**
Restore bridge.py from git history (ea99a65^) and upgrade:

1. plan_to_task_descriptions() emits TaskDescV2 dicts instead of V1. New shape per task: {task_id, plan_task_index, title, action, file_scope: {paths, forbidden: []}, commands: {verify, claim, report_done, context}, completion_footer, blockedBy, skipped}. Do NOT call generate_implement_prompt() inside this function anymore.

2. generate_implement_prompt(taskdesc) becomes a pure renderer: takes a single TaskDescV2 dict, returns markdown string. Signature changes from keyword args to single dict arg. Rendering logic stays the same (# Implement: title, action, file scope, verify commands, memory commands, lifecycle rules, TASK_DONE footer).

3. detect_file_conflicts(tasks) reads file_scope.paths (and optionally file_scope.forbidden) instead of flat files[] list.

4. Add generate_run_id(feature) — simple helper: returns f'{feature}-{int(time.time())}'.

5. Keep _is_already_closed() and _ensure_memory_issue() internal helpers as-is.

6. Add module-level TASK_DESC_SCHEMA_VERSION = 2 constant.

**Verify:**
```bash
python3 -c "from scripts.memory.bridge import plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts, generate_run_id; print('bridge imports OK')"
python3 -c "from scripts.memory.bridge import TASK_DESC_SCHEMA_VERSION; assert TASK_DESC_SCHEMA_VERSION == 2; print('schema version OK')"
python3 -c "from scripts.memory.bridge import generate_run_id; rid = generate_run_id('test'); assert rid.startswith('test-'); print('generate_run_id OK:', rid)"
```

**Done when:** [Observable outcome]

### Task 2: Add bridge + worktree re-exports to __init__.py
**Files:** `.cnogo/scripts/memory/__init__.py`
**Action:**
Add re-exports to __init__.py __all__ list and implement thin wrapper functions:

1. Bridge re-exports: plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts, generate_run_id. Import from .bridge module. Add thin wrappers that delegate to bridge functions.

2. Worktree re-exports (missing): create_session, save_session, get_conflict_context. These functions exist in worktree.py but were removed from __init__.py during workflow-dead-code-cleanup. Add them back as thin wrappers.

3. Add all 7 new names to __all__ list in appropriate sections (add a 'Bridge' section and expand the 'Worktree' section).

**Verify:**
```bash
python3 -c "from scripts.memory import plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts, generate_run_id; print('bridge re-exports OK')"
python3 -c "from scripts.memory import create_session, save_session, get_conflict_context; print('worktree re-exports OK')"
python3 -c "from scripts.memory import *; print('wildcard import OK')"
python3 -c "from scripts.memory import init, create, ready, claim, close, prime; print('core API still OK')"
```

**Done when:** [Observable outcome]

### Task 3: Update worktree.py for V2 compatibility
**Files:** `.cnogo/scripts/memory/worktree.py`
**Action:**
Update worktree.py to work with TaskDesc V2:

1. Add run_id field to WorktreeSession dataclass (default: ''). Update to_dict() to include 'runId' key and from_dict() to read it.

2. Update create_session() to read V2 fields from task descriptions:
   - desc.get('title', f'task-{i}') instead of desc.get('name', f'task-{i}') for task_name (line 291)
   - desc.get('task_id', '') instead of desc.get('memoryId', '') for memory_id in WorktreeInfo (line 313)
   - Optionally accept run_id parameter and store in session

3. Keep backward compatibility: if a desc has 'name' but not 'title', fall back to 'name'. Same for 'memoryId' vs 'task_id'. This allows gradual migration.

**Verify:**
```bash
python3 -c "from scripts.memory.worktree import WorktreeSession; s = WorktreeSession(run_id='test-123'); assert s.run_id == 'test-123'; d = s.to_dict(); assert d['runId'] == 'test-123'; print('run_id field OK')"
python3 -c "from scripts.memory.worktree import WorktreeSession; s = WorktreeSession.from_dict({'runId': 'abc'}); assert s.run_id == 'abc'; print('from_dict runId OK')"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "from scripts.memory import plan_to_task_descriptions, generate_implement_prompt, detect_file_conflicts, generate_run_id, create_session, save_session, get_conflict_context; print('all re-exports OK')"
python3 -c "from scripts.memory.bridge import TASK_DESC_SCHEMA_VERSION; assert TASK_DESC_SCHEMA_VERSION == 2"
python3 -c "from scripts.memory.worktree import WorktreeSession; s = WorktreeSession(run_id='x'); assert 'runId' in s.to_dict()"
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(execution-coordination): restore bridge.py with TaskDesc V2, add re-exports, update worktree for V2
```
