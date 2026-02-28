# Plan 03: Rewrite SubagentStop hook and worker prompts for safe report-only behavior (Contracts 06, 10-worker)

## Goal
Rewrite SubagentStop hook and worker prompts for safe report-only behavior (Contracts 06, 10-worker)

## Tasks

### Task 1: Rewrite SubagentStop hook for report-only behavior
**Files:** `.cnogo/hooks/hook-subagent-stop.py`
**Action:**
Complete rewrite. The new hook must: (1) Parse stdin JSON (same shape: last_assistant_message, cwd, etc). (2) Look for structured footer 'TASK_DONE: [cn-xxx, cn-yyy]' in last_assistant_message using regex pattern r'TASK_DONE:\s*\[([^\]]+)\]'. Parse the comma-separated IDs. (3) For each extracted ID, call report-done (NOT close): `python3 .cnogo/scripts/workflow_memory.py report-done <id> --actor subagent-stop-hook`. This calls report_done() which validates type=TASK and owner before setting DONE_BY_WORKER. (4) Remove ALL existing close logic — no _close_memory_id, no _fallback_session_close, no regex-scanning cn-* from message body. (5) Keep: < 3 second timeout, always exit 0, stderr logging, shebang. (6) If the structured footer is not found, do nothing (log 'no TASK_DONE footer found' to stderr).

**Verify:**
```bash
python3 -m py_compile .cnogo/hooks/hook-subagent-stop.py
echo '{"last_assistant_message":"Done.\nTASK_DONE: [cn-abc123]","cwd":"/tmp"}' | python3 .cnogo/hooks/hook-subagent-stop.py 2>&1; echo "exit: $?"
```

**Done when:** [Observable outcome]

### Task 2: Rewrite bridge.py for minimal worker prompts
**Files:** `.cnogo/scripts/memory/bridge.py`
**Action:**
Rewrite generate_implement_prompt() to produce minimal worker context per Contract 10. The new prompt format: (1) '# Implement: {task_name}' heading. (2) action text. (3) '**Files (ONLY touch these):** file1, file2' (4) '**Verify (must ALL pass):**' with bullet list. (5) If memory_id: '**Memory:** `{memory_id}`' followed by '- Claim: `python3 .cnogo/scripts/workflow_memory.py claim {memory_id} --actor implementer`' and '- Report done: `python3 .cnogo/scripts/workflow_memory.py report-done {memory_id} --actor implementer`' and '- Context: `python3 .cnogo/scripts/workflow_memory.py show {memory_id}`'. (6) Remove ALL close instructions — no 'Close:' command, no 'CRITICAL LIFECYCLE' close step. (7) Add: '**On completion:** Add this footer as the LAST line of your final message: `TASK_DONE: [{memory_id}]`'. (8) Keep failure/retry instructions but change 'close' references to 'report done'. (9) Add: '**NEVER close issues. Only report_done. The leader handles closure.**'

**Verify:**
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.bridge import generate_implement_prompt; p = generate_implement_prompt(task_name='test', action='do thing', files=['a.py'], verify=['true'], memory_id='cn-abc123'); assert 'report-done' in p; assert 'TASK_DONE' in p; assert 'Close:' not in p; assert 'CRITICAL LIFECYCLE' not in p or 'close this issue' not in p; print('OK')"
```

**Done when:** [Observable outcome]

### Task 3: Update agent definition and command files
**Files:** `.claude/agents/implementer.md`, `.claude/commands/implement.md`
**Action:**
In implementer.md: (1) Replace step 7 'Close: Run the memory close command' with 'Report Done: Run the memory report-done command from your task description'. (2) Add: 'NEVER close memory issues — only report done. The leader handles closure.' (3) Add: 'Your LAST line must be a TASK_DONE footer: `TASK_DONE: [cn-xxx]`'. In implement.md: (1) In the success path where it says 'close memory ID', change to 'report-done on memory ID'. (2) Remove any direct close commands. (3) Add the TASK_DONE footer requirement to the success output section.

**Verify:**
```bash
python3 -c "f=open('.claude/agents/implementer.md').read(); assert 'report' in f.lower() or 'TASK_DONE' in f; assert 'Close: Run the memory close' not in f; print('OK')"
python3 -c "f=open('.claude/commands/implement.md').read(); assert 'TASK_DONE' in f or 'report-done' in f; print('OK')"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile .cnogo/hooks/hook-subagent-stop.py
python3 -m py_compile scripts/memory/bridge.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(deterministic-coordination): rewrite hook and worker prompts for report-only behavior
```
