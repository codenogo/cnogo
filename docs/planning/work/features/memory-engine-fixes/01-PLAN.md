# Plan 01: Remaining Fixes — Cache Dedup, Closed-Issue Filter, Retry Logic

## Goal

Fix the last open issues: consolidate duplicated `rebuild_blocked_cache`, fix the stale graph.py copy that doesn't filter closed issues (W-2), and add retry-on-SQLITE_BUSY with exponential backoff.

## Prerequisites

- [x] CONTEXT.md decisions finalized
- [x] B-1, W-1, W-4, W-5, W-6, W-7, W-8 already fixed in current code

## Note on Scope Reduction

During planning, code audit revealed that 7 of 8 review issues were already fixed (tagged with `(B-1)`, `(W-1)`, etc. comments). The remaining work is:
- W-2: `graph.py` has a stale copy of `rebuild_blocked_cache` missing closed-issue filtering
- Deduplication: two copies of `rebuild_blocked_cache` exist (`__init__.py` + `graph.py`)
- Retry logic: agreed in discussion but not yet implemented

## Tasks

### Task 1: Consolidate `rebuild_blocked_cache` and fix W-2
**Files:** `.cnogo/scripts/memory/graph.py`, `.cnogo/scripts/memory/__init__.py`, `.cnogo/scripts/memory/sync.py`
**Action:**
1. Update `graph.py:rebuild_blocked_cache()` to match the improved `__init__.py` version:
   - Step 1: Add `JOIN issues blocked ON d.issue_id = blocked.id` and `AND blocked.status NOT IN ('closed')` to filter closed issues from being marked as blocked
   - Step 2: Add `JOIN issues i ON d.issue_id = i.id` and `AND i.status NOT IN ('closed')` to the transitive propagation query
2. Remove the duplicate `_rebuild_blocked_cache()` from `__init__.py` (lines 631-686)
3. Replace all calls to `_rebuild_blocked_cache(conn)` in `__init__.py` with `from .graph import rebuild_blocked_cache` and call `rebuild_blocked_cache(conn)` instead
4. `sync.py` already imports from `graph.py` — verify it still works

**Verify:**
```bash
python3 -c "from scripts.memory.graph import rebuild_blocked_cache; print('graph.py import OK')"
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import create, close, dep_add, ready, init; from pathlib import Path; import tempfile, os; d=tempfile.mkdtemp(); r=Path(d); init(r); a=create('A',root=r); b=create('B',root=r); dep_add(b.id,a.id,root=r); assert len(ready(root=r))==1; close(a.id,root=r); assert len(ready(root=r))==1; print('blocked cache OK')"
python3 -m py_compile scripts/memory/graph.py
python3 -m py_compile scripts/memory/__init__.py
```

**Done when:** Single source of truth for `rebuild_blocked_cache` in `graph.py`; closed issues excluded from blocked cache in both steps.

### Task 2: Add retry-on-SQLITE_BUSY helper to storage.py
**Files:** `.cnogo/scripts/memory/storage.py`
**Action:**
1. Add a `retry_on_busy()` context manager or decorator to `storage.py` that:
   - Catches `sqlite3.OperationalError` where the message contains "database is locked"
   - Retries up to 3 times with exponential backoff (0.1s, 0.2s, 0.4s)
   - Re-raises after final failure
   - Uses `time.sleep()` from stdlib
2. Keep it simple — a function wrapper, not a class. Example signature:
   ```python
   def with_retry(fn, *args, max_retries=3, base_delay=0.1, **kwargs):
   ```
3. Do NOT apply it anywhere yet — Task 3 wires it up

**Verify:**
```bash
python3 -m py_compile scripts/memory/storage.py
python3 -c "from scripts.memory.storage import with_retry; print('with_retry import OK')"
```

**Done when:** `with_retry` is importable from `storage.py` and handles `OperationalError` with backoff.

### Task 3: Wire retry logic into write operations
**Files:** `.cnogo/scripts/memory/__init__.py`
**Action:**
1. Import `with_retry` from `.storage`
2. Wrap the following write operations with retry:
   - `claim()` — the atomic CAS operation most likely to hit contention
   - `close()` — state change + blocked cache rebuild
   - `create()` — child counter increment under contention
3. Apply at the outermost level: wrap the entire function body's DB interaction (the try/finally block) so the retry covers the full transaction including `BEGIN IMMEDIATE`
4. Do NOT wrap read-only operations (`ready`, `list_issues`, `stats`, `show`) — WAL mode handles concurrent reads

**Verify:**
```bash
python3 -m py_compile scripts/memory/__init__.py
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import create, claim, close, init; from pathlib import Path; import tempfile; d=tempfile.mkdtemp(); r=Path(d); init(r); i=create('Test retry',root=r); claim(i.id,actor='a',root=r); close(i.id,root=r); print('retry-wrapped ops OK')"
```

**Done when:** `claim()`, `close()`, and `create()` retry on SQLITE_BUSY with exponential backoff.

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
python3 -m py_compile scripts/memory/__init__.py
python3 -m py_compile scripts/memory/storage.py
python3 -m py_compile scripts/memory/graph.py
python3 -m py_compile scripts/memory/sync.py
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import init, create, claim, close, ready, dep_add, stats, prime; from pathlib import Path; import tempfile; d=tempfile.mkdtemp(); r=Path(d); init(r); a=create('A',root=r); b=create('B',root=r); dep_add(b.id,a.id,root=r); print(f'ready={len(ready(root=r))}'); claim(a.id,actor='x',root=r); close(a.id,root=r); print(f'ready after close={len(ready(root=r))}'); print(stats(root=r)); print('ALL CHECKS PASS')"
```

## Commit Message
```
fix(memory): consolidate blocked cache, add retry-on-busy

- Remove duplicate rebuild_blocked_cache from __init__.py, use graph.py (W-2)
- Fix graph.py to filter closed issues from blocked cache
- Add with_retry() helper for SQLITE_BUSY exponential backoff
- Wire retry into claim(), close(), create() for multi-agent robustness
```

---
*Planned: 2026-02-14*
