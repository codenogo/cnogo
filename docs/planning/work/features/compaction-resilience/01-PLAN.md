# Plan 01: Close the sync gap: enforce memory issue closure via prompt and SubagentStop hook

## Goal
Close the sync gap: enforce memory issue closure via prompt and SubagentStop hook

## Tasks

### Task 1: Strengthen bridge prompt lifecycle
**Files:** `scripts/memory/bridge.py`
**Action:**
Modify `generate_implement_prompt()` to add mandatory lifecycle instructions. After the existing Memory section, add a CRITICAL block: 'CRITICAL LIFECYCLE: (1) FIRST action: claim this issue. (2) LAST action before finishing: close this issue and confirm closure in your final message by writing "Memory closed: <id>". (3) If blocked and cannot complete, do NOT close — message the team lead instead.' This makes claim/close mandatory rather than optional examples. Keep the existing CLI examples as-is.

**Verify:**
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.bridge import generate_implement_prompt; p = generate_implement_prompt(task_name='test', action='do thing', files=['a.py'], verify=['true'], memory_id='cn-abc123'); assert 'CRITICAL' in p and 'FIRST action' in p and 'LAST action' in p and 'Memory closed:' in p, f'Missing lifecycle instructions'"
python3 -m py_compile scripts/memory/bridge.py
```

**Done when:** [Observable outcome]

### Task 2: Create SubagentStop hook script
**Files:** `scripts/hook-subagent-stop.py`
**Action:**
Create a new Python script that reads SubagentStop hook input from stdin as JSON. It receives: session_id, cwd, agent_id, agent_type, last_assistant_message, agent_transcript_path. The script should: (1) Parse stdin JSON. (2) Extract `last_assistant_message`. (3) Scan for memory ID pattern `cn-[a-z0-9]+(\.[0-9]+)*` using regex. (4) For each found ID, attempt to close via subprocess: `python3 scripts/workflow_memory.py close <id> --reason completed --actor subagent-stop-hook`. Ignore errors (issue may already be closed). (5) As fallback, read `.cnogo/worktree-session.json` and check for any worktree with status not in ('merged','cleaned') that has a memoryId — if the agent's cwd matches a worktree path, close that memory issue. (6) MUST complete in < 3 seconds total. Wrap everything in try/except, always exit 0. Log actions to stderr for debugging. Shebang: `#!/usr/bin/env python3`. Python stdlib only.

**Verify:**
```bash
python3 -m py_compile scripts/hook-subagent-stop.py
echo '{"agent_id":"test","agent_type":"test","last_assistant_message":"Done. Memory closed: cn-abc123","cwd":"/tmp","session_id":"s1","agent_transcript_path":"/tmp/t.jsonl"}' | python3 scripts/hook-subagent-stop.py; echo "exit: $?"
```

**Done when:** [Observable outcome]

### Task 3: Register SubagentStop hook in settings.json
**Files:** `.claude/settings.json`
**Action:**
Replace the existing SubagentStop hook command `echo 'Subagent completed: '"$CLAUDE_AGENT_TYPE"` with `python3 scripts/hook-subagent-stop.py`. Keep the same hook structure (type: command). The hook reads stdin JSON, so no environment variable references needed.

**Verify:**
```bash
python3 -c "import json; s=json.load(open('.claude/settings.json')); hooks=[h for e in s['hooks'].get('SubagentStop',[]) for h in e.get('hooks',[])]; assert any('hook-subagent-stop.py' in h.get('command','') for h in hooks), 'SubagentStop not registered'"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 -m py_compile scripts/hook-subagent-stop.py
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(compaction-resilience): add prompt enforcement and SubagentStop auto-close hook
```
