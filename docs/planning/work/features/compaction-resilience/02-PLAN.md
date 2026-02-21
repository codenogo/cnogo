# Plan 02: Checkpoint ephemeral state before compaction and provide reconciliation logic

## Goal
Checkpoint ephemeral state before compaction and provide reconciliation logic

## Tasks

### Task 1: Create PreCompact hook script
**Files:** `scripts/hook-pre-compact.py`
**Action:**
Create a new Python script that reads PreCompact hook input from stdin as JSON (`{hook_event_name, trigger, custom_instructions}`). The script should: (1) Parse stdin JSON, extract `trigger` ('auto'|'manual'). (2) Read `.cnogo/worktree-session.json` if it exists — extract feature, planNumber, phase, and worktree statuses. (3) Read team config from `~/.claude/teams/` directory — find any active team configs and extract team name + member names. (4) Write `.cnogo/compaction-checkpoint.json` with: `{schemaVersion: 1, trigger, timestamp, session: {feature, planNumber, phase, worktrees: [{taskIndex, name, status, memoryId}]}, team: {name, members: [name]}}`. If no session exists, write `session: null`. If no team, write `team: null`. (5) Append one telemetry line to `.cnogo/command-usage.jsonl`: `{type: 'compaction', trigger, timestamp, hasSession: bool, worktreeCount: int}`. (6) MUST complete in < 3 seconds. Wrap everything in try/except, always exit 0. Log actions to stderr. Shebang: `#!/usr/bin/env python3`. Python stdlib only. Use atomic write (tempfile + os.replace) for the checkpoint file.

**Verify:**
```bash
python3 -m py_compile scripts/hook-pre-compact.py
echo '{"hook_event_name":"PreCompact","trigger":"auto","custom_instructions":""}' | python3 scripts/hook-pre-compact.py; echo "exit: $?"
```

**Done when:** [Observable outcome]

### Task 2: Create reconcile module
**Files:** `scripts/memory/reconcile.py`
**Action:**
Create `scripts/memory/reconcile.py` with a `reconcile_session(root: Path) -> dict` function. The function should: (1) Load `.cnogo/worktree-session.json` via `worktree.load_session()`. If no session, check `.cnogo/compaction-checkpoint.json` for stale session data. (2) For each worktree entry with a `memoryId` and status in ('merged', 'cleaned'): close the memory issue via the memory engine's `close()` function with reason='completed' and actor='session-reconcile'. Ignore already-closed issues. (3) For each worktree entry with status not in ('merged', 'cleaned'): check git if the branch was merged into the base branch (use `git merge-base --is-ancestor`). If merged, close the memory issue. (4) Return a summary dict: `{reconciled: [{id, action, status}], skipped: [{id, reason}], errors: [{id, error}]}`. (5) Import from sibling modules using relative imports (from . import storage, from .worktree import load_session). (6) Handle missing/corrupt files gracefully (return empty summary, don't raise). Python stdlib only.

**Verify:**
```bash
python3 -m py_compile scripts/memory/reconcile.py
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.reconcile import reconcile_session; r = reconcile_session(type('P',(),{'__truediv__':lambda s,o:type('P',(),{'exists':lambda s:False})(),'resolve':lambda s:s})()); assert isinstance(r, dict) and 'reconciled' in r"
```

**Done when:** [Observable outcome]

### Task 3: Register PreCompact hook in settings.json
**Files:** `.claude/settings.json`
**Action:**
Add a new `PreCompact` hook entry in `.claude/settings.json` under the `hooks` key. Add it after the `SubagentStop` entry. Structure: `"PreCompact": [{"hooks": [{"type": "command", "command": "python3 scripts/hook-pre-compact.py"}]}]`. Keep all existing hooks unchanged.

**Verify:**
```bash
python3 -c "import json; s=json.load(open('.claude/settings.json')); hooks=[h for e in s['hooks'].get('PreCompact',[]) for h in e.get('hooks',[])]; assert any('hook-pre-compact.py' in h.get('command','') for h in hooks), 'PreCompact not registered'"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/hook-pre-compact.py
python3 -m py_compile scripts/memory/reconcile.py
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(compaction-resilience): add PreCompact checkpoint hook and reconcile module
```
