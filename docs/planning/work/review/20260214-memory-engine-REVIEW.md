# Review Report: cnogo Memory Engine

**Date:** 2026-02-14T01:10:00Z
**Branch:** main
**Reviewer:** Claude (security-scanner, code-reviewer, manual)
**Scope:** 8 new files (~2,300 LOC), 22 modified files (commands + agents)

---

## Automated Checks

| Check | Result |
|-------|--------|
| Functional Tests (16 scenarios) | PASS |
| Workflow Validation | PASS |
| SQL Injection Scan | PASS (no exploitable vectors) |
| Path Traversal Scan | PASS |
| Secrets Scan | PASS |
| Unsafe Deserialization | PASS (no eval/exec/pickle) |
| Type Checking | N/A (no mypy configured) |
| Dependency Audit | PASS (stdlib only) |

---

## Question-by-Question Evaluation

### 1. Are dependencies first-class now?

**Verdict: YES with caveats**

What works:
- `dep_add()` / `dep_remove()` create and destroy directed edges between issues (`__init__.py:417-477`)
- Cycle detection via DFS prevents invalid graphs (`__init__.py:542-559`)
- Blocked cache materializes O(1) ready-state lookups (`__init__.py:510-539`)
- `blockers()` and `blocks()` expose the graph from both directions (`storage.py:319-345`)
- `ready()` excludes blocked issues using the materialized cache (`storage.py:486-524`)
- Two edge types: `blocks` (direct blocker) and `parent-child` (transitive containment)

What needs attention:
- **Blocked cache rebuild has a brief inconsistency window** (DELETE then INSERT). Low practical risk in single-agent use, but concurrent `ready()` queries during rebuild could return stale results.
- **Cycle detection only validates new edges**, not the existing graph. If a manual DB edit or corrupted import creates a cycle, it goes undetected. The `find_cycles()` function exists in `graph.py` but isn't exposed in the public API.
- **Parent-child transitive blocking semantics are subtle**: an open parent does NOT block children, but a blocked parent DOES propagate. The code is correct; the comment needs more clarity.

### 2. Discovery during execution maps to your actual workflow?

**Verdict: YES**

What works:
- Hierarchical IDs (`cn-a3f8.1.1`) mirror the discuss-plan-implement hierarchy
- `create(parent=...)` automatically creates parent-child deps and generates child IDs
- `metadata` JSON field stores arbitrary discovery context (file lists, verify commands)
- Issue types (`epic`, `task`, `subtask`, `bug`, `quick`, `background`) map 1:1 to cnogo commands
- 12 command `.md` files wired with conditional memory sections
- Feature/plan linkage via `feature_slug` and `plan_number` fields
- Labels support flexible categorization

What needs attention:
- **Child counter race condition**: `next_child_number()` does a read-then-write that isn't atomic across processes. Two agents creating children for the same parent could collide. Practical risk is low (rare scenario) but worth hardening.

### 3. Session persistence without re-prompting?

**Verdict: MOSTLY YES (one gap)**

What works:
- SQLite persists all state locally in `.cnogo/memory.db`
- JSONL export preserves issues, dependencies, and labels for git-portable sync
- `import_jsonl()` rebuilds SQLite from JSONL (including blocked cache and child counters)
- `prime()` generates ~500-1500 token context summaries for efficient session restoration
- `/resume` command wired to call `import_jsonl()` + `prime()` + `ready()`
- `/pause` command wired to call `sync()` for pre-handoff persistence

What's missing:
- **Events (audit trail) are NOT exported to JSONL.** The `export_jsonl()` function exports issues, deps, and labels but omits the `events` table. This means the audit trail is local-only and lost on cross-machine sync or post-merge import. This is the single biggest gap in the persistence story.

### 4. Multi-agent coordination that actually works?

**Verdict: YES for typical use, fragile under high concurrency**

What works:
- Compare-and-swap `claim_issue()` (`storage.py:241-250`): `WHERE assignee IS NULL OR assignee = ''` ensures only one agent wins
- SQLite WAL mode enables concurrent reads without blocking
- `busy_timeout = 5000` provides 5-second retry on lock contention
- `blocked_cache` prevents agents from picking up tasks whose prereqs aren't done
- `/team` command wired to create team epics, assign subtasks, claim/close per agent

What needs attention:
- **CAS doesn't use `BEGIN IMMEDIATE`**: Two agents could execute the UPDATE concurrently. SQLite's default deferred transaction only acquires a write lock at commit time. In practice, SQLite serializes writes at the database level (only one writer at a time), so this is safe for SQLite-level atomicity. But `BEGIN IMMEDIATE` would make the intent clearer.
- **Blocked cache rebuild window**: Same as Q1 above.
- **No retry logic on `SQLITE_BUSY`**: If busy_timeout expires, the error propagates unhandled.

### 5. Audit trail you can trust?

**Verdict: YES locally, NO portably**

What works:
- Events table is append-only: `insert_event()` is the only write path (`storage.py:352-361`)
- No UPDATE or DELETE on events exists anywhere in the codebase
- AUTOINCREMENT IDs guarantee monotonic ordering
- Every state change (create, claim, update, close, reopen, dep_add, dep_remove) emits an event
- Events record actor, timestamp, and structured data payload

What's broken:
- **Events not exported/imported** (same as Q3). The audit trail is trapped in the local SQLite file. Cross-session, cross-machine, and post-merge scenarios lose all history.
- **No `all_events()` function in storage.py** for bulk export (easy to add).

### 6. Meta-observation?

**Verdict: YES**

What works:
- `prime()` generates a structured markdown summary with stats, in-progress work, and ready tasks (`context.py:23-83`)
- `show_graph()` renders ASCII dependency trees with status icons (`context.py:86-151`)
- `stats()` returns comprehensive aggregates: by status, by type, by feature (`storage.py:527-568`)
- Token-efficient design: ~500-1500 tokens for full context injection

What could be better:
- `stats()` runs multiple independent queries without a read transaction, so counts may not sum consistently under concurrent writes
- `show_graph()` renders parent-child hierarchy well but could make `blocks` relationships more visually distinct

---

## Issues Found

### Blockers (must fix)

| ID | File | Issue | Severity |
|----|------|-------|----------|
| B-1 | `sync.py:27-62` | Events NOT exported to JSONL — audit trail lost on roundtrip | Critical |

### Warnings (should fix)

| ID | File | Issue | Severity |
|----|------|-------|----------|
| W-1 | `storage.py:407-424` | `next_child_number()` read-then-write not atomic across processes | High |
| W-2 | `__init__.py:510-539` | Blocked cache rebuild has brief inconsistency window (DELETE+INSERT) | High |
| W-3 | `storage.py:236` | Dynamic SQL via f-string for column names — safe but fragile (add whitelist) | Medium |
| W-4 | `sync.py:87-124` | JSONL import has no schema validation (accepts invalid status/types) | Medium |
| W-5 | `__init__.py:542-559` | Cycle detection DFS has no depth/iteration bound | Medium |
| W-6 | `storage.py:241-250` | `claim_issue()` should use `BEGIN IMMEDIATE` for explicit write lock | Medium |
| W-7 | `sync.py:110-122` | Import doesn't validate dependency foreign keys before insert | Low |
| W-8 | `storage.py:527-568` | `get_stats()` runs multiple queries without read transaction | Low |

### Suggestions (optional)

| ID | File | Suggestion |
|----|------|------------|
| S-1 | `__init__.py:102-190` | Extract ID generation into a helper to reduce `create()` from 90 lines |
| S-2 | `graph.py:76-120` | `topological_order()` is dead code — expose in API or remove |
| S-3 | `graph.py:123-183` | `find_cycles()` should be exposed in public API for health checks |
| S-4 | `identity.py:33` | Consider 6-byte default IDs — 4 bytes hits 50% collision at ~65K issues |
| S-5 | `__init__.py` | Use `contextlib.contextmanager` for DB connections instead of try/finally |
| S-6 | All | Add Python `logging` instead of `print()` for warnings |

---

## Security Review Summary

**Reviewer: security-scanner agent**

| Category | Status |
|----------|--------|
| SQL Injection | PASS — All values parameterized; f-string used only for column names from internal callers |
| Path Traversal | PASS — All paths rooted at `root / .cnogo /` |
| Command Injection | PASS — `subprocess.run()` with `shell=False`, args as list, 10s timeout |
| Secrets/Credentials | PASS — No hardcoded secrets, no credential handling |
| Unsafe Deserialization | PASS — JSON only, no pickle/yaml/marshal/eval/exec |
| DoS Vectors | WARN — Cycle detection unbounded; blocked cache rebuild can be slow on large graphs |
| Foreign Key Integrity | PASS — Schema enforces FK constraints; WAL mode with busy_timeout |
| Data Validation | WARN — JSONL import accepts unvalidated data; CHECK constraints catch some at DB level |

**Overall Security Rating: B+ (Good with one critical gap)**

---

## Manual Review Notes

### Code Quality

| Check | Status |
|-------|--------|
| Functions <=50 lines | WARN — `create()` is 88 lines |
| Clear, descriptive naming | PASS |
| No magic numbers/strings | WARN — `10` retries, `5` bytes in ID generation |
| Error handling present | PASS — try/finally on all connections |
| Logging appropriate | WARN — uses print() not logging |
| No TODO without ticket | PASS |
| Consistent with patterns | PASS |

### Testing

| Check | Status |
|-------|--------|
| Unit tests for new logic | WARN — 16 functional tests inline, no pytest suite yet |
| Edge cases covered | PASS — collision retry, double-claim, cycle detection |
| Error cases tested | PASS — ValueError on bad claim/close |
| No flaky test patterns | PASS — deterministic tests with temp dirs |

### Karpathy Checklist

| Principle | Status | Notes |
|----------|--------|------|
| Think Before Coding | PASS | 13-section architectural plan preceded implementation |
| Simplicity First | PASS | stdlib-only, no ORM, no external deps, 2300 LOC for full engine |
| Surgical Changes | PASS | Commands gain conditional sections; existing behavior unchanged when memory disabled |
| Goal-Driven Execution | PASS | 16 functional tests verify core scenarios; workflow validator passes |

---

## Verdict

**WARN — Conditional pass. One blocker (events not exported) and several important hardening items.**

The memory engine is architecturally sound and functionally complete for single-agent workflows. The core data model, query engine, and command integration are well-designed. The main gap is event export for portable audit trails. Multi-agent concurrency hardening items (W-1, W-2, W-6) should be addressed before team-scale use.

### Recommended path forward:
1. Fix B-1 (events export) — enables trusted audit trail and true session persistence
2. Fix W-1, W-2 (atomicity) — enables safe multi-agent use
3. Add W-3 (field whitelist) — defense in depth
4. Address remaining warnings in a follow-up PR
5. Create a proper pytest suite from the 16 inline functional tests
