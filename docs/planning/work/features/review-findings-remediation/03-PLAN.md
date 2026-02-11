# Plan 03: PostToolUse Optimization & Python Consolidation

## Goal
Optimize the PostToolUse formatting hook for speed, create shared workflow_utils.py, and refactor Python scripts to use it.

## Prerequisites
- [ ] Plan 01 complete (settings.json hook path fixed)
- [ ] Plan 02 complete (install.sh copies scripts/)

## Tasks

### Task 1: Optimize PostToolUse formatting hook
**Files:** `scripts/workflow_hooks.py`
**Action:**
Optimize the post-edit formatting hook to reduce the 100-500ms overhead (finding #11):

1. **Add early-exit check** at the top of `post_edit()`:
   - Read `WORKFLOW.json` `performance.postEditFormat` — if `"off"`, exit immediately.
   - Exit early if no `$CLAUDE_TOOL_INPUT` is set.

2. **Replace subprocess `which` with `shutil.which()`** from Python stdlib:
   - Change `_which()` function to use `shutil.which(cmd)` instead of `subprocess.check_output(["which", cmd])`.
   - Eliminates 2-5 subprocess spawns per invocation (~40-80ms).

3. **Cache repo root** detection:
   - Compute `git rev-parse --show-toplevel` once and store as module-level variable.
   - Avoid re-calling on subsequent invocations within the same process (relevant if the hook is ever kept alive).

**Verify:**
```bash
python3 -c "import scripts.workflow_hooks" 2>/dev/null || python3 scripts/workflow_hooks.py post_edit 2>/dev/null; echo "exit: $?"
grep 'shutil.which' scripts/workflow_hooks.py
grep -c 'subprocess.*which' scripts/workflow_hooks.py  # 0
```

**Done when:** workflow_hooks.py uses shutil.which(), has early-exit, no subprocess for which.

### Task 2: Create workflow_utils.py
**Files:** `scripts/workflow_utils.py`
**Action:**
Create a shared utility module with functions duplicated across 4-5 scripts (finding #15):

1. **`repo_root() -> Path`** — Consistent implementation using `git rev-parse --show-toplevel` with `Path.cwd()` fallback.
2. **`load_json(path) -> dict`** — Load and parse a JSON file, return dict.
3. **`write_json(path, data)`** — Write dict to JSON file with 2-space indent and trailing newline.
4. **`load_workflow() -> dict`** — Load `docs/planning/WORKFLOW.json` relative to repo root.

All stdlib-only. No external dependencies.

**Verify:**
```bash
python3 -c "from scripts.workflow_utils import repo_root, load_json, write_json, load_workflow; print('imports OK')"
python3 -c "from scripts.workflow_utils import repo_root; print(repo_root())"
```

**Done when:** workflow_utils.py exists with all 4 functions, importable.

### Task 3: Refactor Python scripts to use workflow_utils.py
**Files:** `scripts/workflow_validate.py`, `scripts/workflow_detect.py`, `scripts/workflow_checks.py`, `scripts/workflow_render.py`, `scripts/workflow_hooks.py`
**Action:**
Replace duplicated functions in all 5 scripts with imports from workflow_utils.py (finding #15):

1. **workflow_validate.py**: Replace `_load_json()` and `_find_repo_root()` with imports. Add `# WORKFLOW.json is a trusted file (equivalent to Makefile)` comment near shell=True usage in workflow_checks.py (finding #16).
2. **workflow_detect.py**: Replace `load_json()`, `write_json()`, and `Path.cwd()` repo root with imports.
3. **workflow_checks.py**: Replace `load_json()`, `write_json()`, `run_shell()` — add trusted-file comment for shell=True (finding #16).
4. **workflow_render.py**: Replace `load()` with `load_json` import.
5. **workflow_hooks.py**: Replace repo root detection with import.

**Verify:**
```bash
python3 scripts/workflow_validate.py
python3 scripts/workflow_detect.py --help 2>/dev/null; echo "exit: $?"
python3 -c "import json; json.load(open('scripts/workflow_utils.py'.replace('.py','') + '.py' if False else open('scripts/workflow_utils.py')); print('exists')" 2>/dev/null || python3 -c "from scripts.workflow_utils import repo_root; print('OK')"
grep 'from scripts.workflow_utils import\|from .workflow_utils import' scripts/workflow_validate.py scripts/workflow_detect.py scripts/workflow_checks.py scripts/workflow_render.py scripts/workflow_hooks.py
```

**Done when:** All 5 scripts import from workflow_utils.py, no duplicated load_json/repo_root functions, validator still passes.

## Verification

After all tasks:
```bash
python3 scripts/workflow_validate.py
grep 'shutil.which' scripts/workflow_hooks.py
python3 -c "from scripts.workflow_utils import repo_root, load_json; print('OK')"
```

## Commit Message
```
fix(review-findings-remediation): optimize PostToolUse, consolidate Python utils

- Optimize workflow_hooks.py: shutil.which(), early-exit, cached repo root
- Create scripts/workflow_utils.py with shared load_json, repo_root, write_json
- Refactor 5 Python scripts to use shared utils (eliminate DRY violations)
- Document WORKFLOW.json as trusted file for shell=True usage
```

---
*Planned: 2026-02-10*
