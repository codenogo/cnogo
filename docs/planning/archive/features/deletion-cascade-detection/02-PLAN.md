# Plan 02: Add validation warning for deletion-last-task, render auto_expanded_paths in agent prompts, and document deletions field in plan.md

## Goal
Add validation warning for deletion-last-task, render auto_expanded_paths in agent prompts, and document deletions field in plan.md

## Tasks

### Task 1: Add deletion-last-task validation warning
**Files:** `scripts/workflow_validate_core.py`
**Action:**
In `_validate_plan_contract()`, after the existing task validation loop, add a check: if any task has a non-empty `deletions` array and it is the last task in the plan (no subsequent task exists), emit a WARN finding: 'Task N has `deletions` but is the last task in the plan — no subsequent task to receive auto-expanded caller cleanup scope.' Also validate that `deletions` is a list of strings when present.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_validate_core.py
python3 scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Render auto_expanded_paths in generate_implement_prompt()
**Files:** `scripts/memory/bridge.py`
**Action:**
In `generate_implement_prompt()`, after the 'Files (ONLY touch these)' section, check for `auto_expanded_paths` in the taskdesc. If non-empty, add a section: '**Auto-expanded (callers of deleted files):**' followed by the file list. This gives the agent visibility into why its scope is larger than the plan specified.

**Verify:**
```bash
python3 -m py_compile scripts/memory/bridge.py
```

**Done when:** [Observable outcome]

### Task 3: Document deletions field in plan.md schema
**Files:** `.claude/commands/plan.md`
**Action:**
In the Step 4 section of plan.md, add `deletions` to the task schema documentation. Add a line after `files[]` explaining: `"deletions": ["path/to/file.py"]` — optional list of files being deleted by this task. When present, the bridge auto-scans the repo for callers and expands the next task's file scope. Keep the addition concise (2-3 lines max) to stay within token budget.

**Verify:**
```bash
python3 scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 -m py_compile scripts/workflow_validate_core.py
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(deletion-cascade): add validation, prompt rendering, and plan docs for deletions field
```
