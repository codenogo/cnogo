# Plan 01: Move all Python runtime files to .cnogo/scripts/ with working imports

## Goal
Move all Python runtime files to .cnogo/scripts/ with working imports

## Tasks

### Task 1: Create _bootstrap.py and move workflow scripts
**Files:** `.cnogo/scripts/_bootstrap.py`, `.cnogo/scripts/workflow_memory.py`, `.cnogo/scripts/workflow_checks.py`, `.cnogo/scripts/workflow_checks_core.py`, `.cnogo/scripts/workflow_validate.py`, `.cnogo/scripts/workflow_validate_core.py`, `.cnogo/scripts/workflow_hooks.py`, `.cnogo/scripts/workflow_render.py`, `.cnogo/scripts/workflow_detect.py`, `.cnogo/scripts/workflow_utils.py`
**Action:**
Create .cnogo/scripts/_bootstrap.py with sys.path setup (adds .cnogo/ directory to sys.path so 'from scripts.memory import ...' resolves correctly). Then git mv the 9 workflow Python scripts from scripts/ to .cnogo/scripts/. Add 'import _bootstrap  # noqa: F401' as the first import after 'from __future__ import annotations' in each moved file. The _bootstrap.py content: import os, sys; _cnogo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); add _cnogo_dir to sys.path if not present.

**Micro-steps:**
- Create .cnogo/scripts/ directory
- Create .cnogo/scripts/_bootstrap.py that adds .cnogo/ to sys.path
- git mv each of the 9 workflow .py files from scripts/ to .cnogo/scripts/
- Add 'import _bootstrap  # noqa: F401' after 'from __future__ import annotations' in each moved script
- Verify python3 .cnogo/scripts/workflow_memory.py --help runs without import errors

**TDD:**
- required: `false`
- reason: File moves with bootstrap import — no new logic to test, verified by import check

**Verify:**
```bash
test -f .cnogo/scripts/_bootstrap.py
test -f .cnogo/scripts/workflow_memory.py
test -f .cnogo/scripts/workflow_utils.py
python3 -c "import sys; sys.path.insert(0, '.cnogo'); import scripts.memory; print('memory import OK')"
python3 .cnogo/scripts/workflow_memory.py prime --limit 1
```

**Done when:** [Observable outcome]

### Task 2: Move memory and context packages
**Files:** `.cnogo/scripts/memory/`, `.cnogo/scripts/context/`
**Action:**
git mv the memory/ and context/ packages from scripts/ to .cnogo/scripts/. These are pure directory moves — no code changes needed inside the packages because _bootstrap.py ensures 'from scripts.memory import ...' and 'from scripts.context import ...' resolve to the new location.

**Micro-steps:**
- git mv scripts/memory/ .cnogo/scripts/memory/
- git mv scripts/context/ .cnogo/scripts/context/
- Verify directory structure is intact (memory/ has 13 files, context/ has phases/ subdir)
- Verify Python imports resolve through _bootstrap.py

**TDD:**
- required: `false`
- reason: Directory moves — no code changes, verified by import checks

**Verify:**
```bash
test -d .cnogo/scripts/memory
test -d .cnogo/scripts/context/phases
python3 -c "import sys; sys.path.insert(0, '.cnogo'); from scripts.memory import is_initialized; print('memory OK')"
python3 -c "import sys; sys.path.insert(0, '.cnogo'); from scripts.context.phases.structure import process_structure; print('context OK')"
```

**Done when:** [Observable outcome]

### Task 3: Create tests/conftest.py and verify all tests pass
**Files:** `tests/conftest.py`
**Action:**
Create tests/conftest.py with sys.path setup: import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.cnogo')). This makes all 19 test files that import from scripts.memory or scripts.context work without changes. Run pytest to verify.

**Micro-steps:**
- Create tests/conftest.py that adds .cnogo/ to sys.path via conftest fixture
- Run the full test suite to verify all 19 test files find their imports
- Fix any remaining import issues

**TDD:**
- required: `false`
- reason: conftest.py is test infrastructure — verified by running the tests themselves

**Verify:**
```bash
test -f tests/conftest.py
python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
test -f .cnogo/scripts/_bootstrap.py
test -d .cnogo/scripts/memory
test -d .cnogo/scripts/context/phases
python3 .cnogo/scripts/workflow_memory.py prime --limit 1
python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
test ! -f scripts/workflow_memory.py
```

## Commit Message
```
refactor(cnogo-packaging): move Python runtime to .cnogo/scripts/
```
