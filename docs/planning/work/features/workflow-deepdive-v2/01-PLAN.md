# Plan 01: Harden data integrity: transaction isolation in JSONL export, stderr logging for silent hook failures, and SQL injection prevention in PRAGMA calls

## Goal
Harden data integrity: transaction isolation in JSONL export, stderr logging for silent hook failures, and SQL injection prevention in PRAGMA calls

## Tasks

### Task 1: Add read transaction wrapper in export_jsonl
**Files:** `.cnogo/scripts/memory/sync.py`
**Action:**
In sync.py export_jsonl(), wrap the four read operations (all_issues, all_dependencies, all_labels, all_events) in an explicit BEGIN...ROLLBACK transaction so all reads see a consistent WAL snapshot. Add conn.execute('BEGIN') before the reads and conn.execute('ROLLBACK') in the finally block. Same pattern as get_stats() in storage.py.

**Micro-steps:**
- Wrap the four read operations in export_jsonl with BEGIN before reads
- Add try/finally with ROLLBACK to release read lock on error
- Verify export_jsonl still produces correct output via prime command

**TDD:**
- required: `false`
- reason: Defensive concurrency improvement with no observable behavior change in single-process tests

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/memory/sync.py
python3 .cnogo/scripts/workflow_memory.py prime
```

**Done when:** [Observable outcome]

### Task 2: Add stderr logging for silent hook failures
**Files:** `.cnogo/scripts/workflow_hooks.py`
**Action:**
In workflow_hooks.py pre_bash(), change the bare 'except Exception:' at line 354 to 'except Exception as exc:' and add: print(f'[cnogo] Hook error (non-blocking): {exc}', file=sys.stderr) before return 0. This surfaces debugging info without blocking the developer's command.

**Micro-steps:**
- In pre_bash() except handler (line 354), capture the exception as 'exc'
- Add stderr warning with exception details before return 0
- Keep return 0 to never block work

**TDD:**
- required: `false`
- reason: Logging addition with no behavior change; hook must still return 0 on any failure

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
```

**Done when:** [Observable outcome]

### Task 3: Add table allowlist for PRAGMA table_info
**Files:** `.cnogo/scripts/memory/storage.py`
**Action:**
In storage.py, add near line 104: _ALLOWED_TABLES = frozenset({'issues', 'dependencies', 'events', 'labels', 'blocked_cache', 'child_counters', 'schema_info'}). In _column_exists(), add: if table not in _ALLOWED_TABLES: raise ValueError(f'Unknown table: {table!r}'). This prevents SQL injection if the function ever receives external input.

**Micro-steps:**
- Add _ALLOWED_TABLES frozenset containing all known table names from SCHEMA_SQL
- Add validation check at top of _column_exists()
- Raise ValueError for unknown table names

**TDD:**
- required: `false`
- reason: Defense-in-depth for internal function called only with hardcoded table names during migration

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/memory/storage.py
python3 .cnogo/scripts/workflow_memory.py prime
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile .cnogo/scripts/memory/sync.py
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
python3 -m py_compile .cnogo/scripts/memory/storage.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
fix(memory): harden data integrity — transaction isolation, hook logging, PRAGMA allowlist
```
