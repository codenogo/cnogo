# Graph Hook Fallback Indexing

## Problem

`post_commit_graph` in `workflow_hooks.py` hard-skips reindex when `.cnogo/.venv` is missing (line 545). This means graph DB is never created in non-bootstrapped repos or test environments. The hook contract test `test_reindex_creates_graph_db` fails because the hook returns 0 without indexing.

## Decision

Remove the hard-skip. When venv is missing, fall through to current-interpreter indexing. The existing `try/except` already handles `ImportError` gracefully.

## Scope

- **Fix**: Remove early return at line 545-553, keep advisory warning
- **Files**: `workflow_hooks.py` (fix), `test_workflow_hooks_graph.py` (already has the test)
- **Risk**: Low — only changes the no-venv path; venv-present path is unchanged
