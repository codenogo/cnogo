# Plan 01: Remove hard-skip in post_commit_graph when .cnogo/.venv is missing; fall through to current-interpreter indexing

## Goal
Remove hard-skip in post_commit_graph when .cnogo/.venv is missing; fall through to current-interpreter indexing

## Tasks

### Task 1: Remove venv-missing early return, fall through to direct indexing
**Files:** `.cnogo/scripts/workflow_hooks.py`, `tests/test_workflow_hooks_graph.py`
**Action:**
Remove the `if not venv_python.exists(): ... return 0` block (lines 545-553). Replace with an advisory warning that does NOT return early — just prints to stderr and falls through to the existing import/index block below. The existing try/except at line 567 already catches ImportError if kuzu is unavailable, so no new error handling needed.

**Micro-steps:**
- Run test_reindex_creates_graph_db — expect FAIL (graph.db not created due to hard-skip)
- In workflow_hooks.py, remove the if-block at lines 545-553 that returns early when venv_python does not exist
- Add advisory warning before the fallback indexing block: print a note to stderr that venv is recommended but continuing with current interpreter
- Run test_reindex_creates_graph_db — expect PASS
- Run full test_workflow_hooks_graph.py — expect 5/5 pass

**TDD:**
- required: `true`
- failingVerify:
  - `PYTHONPATH=.cnogo python3 -m pytest tests/test_workflow_hooks_graph.py::TestPostCommitGraph::test_reindex_creates_graph_db -q`
- passingVerify:
  - `PYTHONPATH=.cnogo python3 -m pytest tests/test_workflow_hooks_graph.py -q`

**Verify:**
```bash
PYTHONPATH=.cnogo python3 -m pytest tests/test_workflow_hooks_graph.py -q
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
PYTHONPATH=.cnogo python3 -m pytest tests/test_workflow_hooks_graph.py -q
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
```

## Commit Message
```
fix(hooks): remove hard-skip in post_commit_graph, fallback to current interpreter when venv missing
```
