# Execution Coordination — unified harness with bridge contract

## Problem

`/implement` (serial) and `/team implement` (parallel) are two divergent execution paths. bridge.py was deleted in PR #12 (breaking team flow), ledger.py was redundant state never executed, and worktree functions needed by team flow aren't exported. Additionally, the V1 TaskDesc shape bakes all structured fields into a markdown `description` string, losing `action` as a first-class field.

## Design: One Harness, Two Modes, TaskDesc V2

```
plan JSON
   |
   v
bridge.plan_to_task_descriptions(plan_json_path, root)
   |
   v
List[TaskDescV2]   (structured — no markdown description field)
   |
   +-- serial (/implement): iterate TaskDescV2, use fields (action, file_scope,
   |   commands) directly. Agent has full plan context — doesn't need prompts.
   |
   +-- parallel (/team implement): persist as versioned wrapper artifact.
       At spawn-time: generate_implement_prompt(taskdesc) → markdown prompt.
       Create worktree session, spawn implementer per task, monitor,
       reconcile, merge, cleanup.
```

Both modes get: validated blockedBy, memory issue bootstrapping, skip-already-closed on resume.

## TaskDesc V2 Shape

```python
{
    "task_id": "cn-xxx.1",          # memory issue ID (or "" if no memory)
    "plan_task_index": 0,           # zero-based index for stable ordering
    "title": "Restore bridge.py",   # human-readable name
    "action": "Restore from git...",# first-class action text from plan
    "file_scope": {
        "paths": ["scripts/memory/bridge.py"],   # ONLY touch these
        "forbidden": []                           # NEVER touch these
    },
    "commands": {
        "verify": ["python3 -c ..."],
        "claim": "python3 scripts/workflow_memory.py claim cn-xxx.1 --actor implementer",
        "report_done": "python3 scripts/workflow_memory.py report-done cn-xxx.1 --actor implementer",
        "context": "python3 scripts/workflow_memory.py show cn-xxx.1"
    },
    "completion_footer": "TASK_DONE: [cn-xxx.1]",
    "blockedBy": [],
    "skipped": false
}
```

Persisted artifact wrapper:
```json
{
    "schema_version": 2,
    "feature": "execution-coordination",
    "plan_number": "01",
    "generated_at": "2026-02-21T17:00:00Z",
    "tasks": [ /* TaskDescV2[] */ ]
}
```

## Decisions

### 1. Restore bridge.py + upgrade to V2

Restore from git (ea99a65^), then upgrade:
- `plan_to_task_descriptions(plan_json_path, root)` — emit TaskDescV2 objects (no markdown)
- `generate_implement_prompt(taskdesc)` — pure renderer: TaskDescV2 dict → markdown string (spawn-time only)
- `detect_file_conflicts(tasks)` — read `file_scope.paths` and `file_scope.forbidden`
- Add: `generate_run_id(feature)` — moved from deleted ledger.py

### 2. Kill ledger.py — no run.json

Ledger state is redundant (verified by audit):

| State | Already tracked by |
|-------|-------------------|
| Team identity | `~/.claude/teams/` |
| Task assignments | TaskList/TaskCreate |
| Feature phase | memory phase-get/phase-set |
| Worktree state | worktree-session.json |

Only unique value was `generate_run_id()` — a one-liner that moves to bridge.py.

### 3. Re-export worktree + bridge functions

Add to `__init__.py` `__all__` + thin wrappers:
- Worktree: `create_session`, `save_session`, `get_conflict_context`
- Bridge: `plan_to_task_descriptions`, `generate_implement_prompt`, `detect_file_conflicts`, `generate_run_id`

### 4. Unify execution paths

**Serial (`/implement`):** Call `plan_to_task_descriptions()` at start for validation. Iterate TaskDescV2 results, use structured fields directly. Do NOT call `generate_implement_prompt()`.

**Parallel (`/team implement`):** Call `plan_to_task_descriptions()`. Persist as versioned wrapper. At spawn-time, render prompts via `generate_implement_prompt(taskdesc)`. Remove ledger imports, use `generate_run_id()` from bridge. Store `run_id` in worktree-session.json.

### 5. Update worktree.py for V2

- Add `run_id` field to WorktreeSession dataclass
- Update `create_session()` to read V2 fields (`task_id`, `title`, `file_scope.paths`, `skipped`)

### 6. No hook changes needed

Audit confirmed `hook-subagent-stop.py` is already correct:
- Parses structured `TASK_DONE: [cn-xxx]` footer
- Calls `report-done` only (never close)
- Contract 06 intact

## Files Affected

| File | Action |
|------|--------|
| `scripts/memory/bridge.py` | Restore from git + upgrade to V2 output + add `generate_run_id()` |
| `scripts/memory/__init__.py` | Add bridge + worktree re-exports |
| `scripts/memory/worktree.py` | Add `run_id` to WorktreeSession, update `create_session()` for V2 |
| `.claude/commands/team.md` | Remove ledger imports, load V2 wrapper, render prompts at spawn-time |
| `.claude/commands/implement.md` | Call `plan_to_task_descriptions()` at step 3, use V2 structured fields |

## What stays unchanged

- `scripts/hook-subagent-stop.py` — already correct
- `scripts/hook-pre-compact.py` — already correct
- `scripts/memory/reconcile_leader.py` — already correct
- `.claude/agents/implementer.md` — already correct

## Migration

- Delete old `.cnogo/task-descriptions-*.json` files (V1 format)
- Consumers fail fast on `schema_version != 2`

## Next

`/plan execution-coordination`
