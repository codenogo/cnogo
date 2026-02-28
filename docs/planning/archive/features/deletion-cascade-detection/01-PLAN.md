# Plan 01: Add cascade scanning to bridge.py that detects uncovered callers of deleted files and auto-expands subsequent task scopes

## Goal
Add cascade scanning to bridge.py that detects uncovered callers of deleted files and auto-expands subsequent task scopes

## Tasks

### Task 1: Add cascadePatterns config to WORKFLOW.json
**Files:** `docs/planning/WORKFLOW.json`
**Action:**
Add a top-level `cascadePatterns` array to WORKFLOW.json with a default Python pattern. Each entry has `glob` (file pattern like `*.py`) and `importPattern` (regex with `{module}` placeholder for the deleted module's stem/dotted path). Ship with Python as the default: glob `*.py`, importPattern `(?:from|import)\s+{module}`.

**Verify:**
```bash
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); assert 'cascadePatterns' in d; assert len(d['cascadePatterns']) >= 1; print('OK')"
```

**Done when:** [Observable outcome]

### Task 2: Add scan_deletion_callers() to bridge.py
**Files:** `.cnogo/scripts/memory/bridge.py`
**Action:**
Add a `scan_deletion_callers(root, deletions, cascade_patterns)` function to bridge.py. Parameters: `root: Path` (repo root), `deletions: list[str]` (file paths being deleted), `cascade_patterns: list[dict]` (from WORKFLOW.json). For each deletion, derive the module stem (e.g., `src/context/graphrag.py` -> `graphrag` and `src.context.graphrag`). For each cascade pattern, rglob the repo for matching files, read each file, and regex-match for the import pattern with `{module}` replaced. Return a deduplicated list of caller file paths (relative to root). Skip files in `.git`, `node_modules`, `__pycache__`, `.cnogo`. Use pathlib + re only (stdlib).

**Verify:**
```bash
python3 -m py_compile scripts/memory/bridge.py
```

**Done when:** [Observable outcome]

### Task 3: Wire cascade expansion into plan_to_task_descriptions()
**Files:** `.cnogo/scripts/memory/bridge.py`
**Action:**
After the main task-building loop in `plan_to_task_descriptions()`, add a post-pass: (1) Load WORKFLOW.json from `root / 'docs/planning/WORKFLOW.json'` to get cascadePatterns (gracefully skip if missing/empty). (2) For each non-skipped task, check if the original plan task had a `deletions` field. (3) If yes, call `scan_deletion_callers()` with those deletions. (4) Filter out files already in ANY task's `file_scope.paths`. (5) Add remaining uncovered callers to the NEXT non-skipped task's `file_scope.paths` and to a new `auto_expanded_paths` key on that TaskDescV2. If no next task exists, add to the current task. (6) Also initialize `auto_expanded_paths: []` on all TaskDescV2 dicts that don't get expanded (for consistent schema).

**Verify:**
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(deletion-cascade): add cascade scanning and auto-expand to bridge.py
```
