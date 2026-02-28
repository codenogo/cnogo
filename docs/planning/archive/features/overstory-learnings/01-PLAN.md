# Plan 01: Adopt 4 Overstory patterns: agent failure modes, propulsion principle, doctor git check, merge tier logging

## Goal
Adopt 4 Overstory patterns: agent failure modes, propulsion principle, doctor git check, merge tier logging

## Tasks

### Task 1: Agent failure modes and propulsion principle
**Files:** `.claude/agents/implementer.md`, `.claude/agents/debugger.md`, `.claude/agents/resolver.md`
**Action:**
For each agent .md file, add to the existing Rules section: (1) 3-5 inline 'Do NOT' failure prevention rules specific to that agent role, and (2) a propulsion line 'Execute immediately — do not ask for confirmation or propose a plan.' Keep additions under 40 words per file. Specific failure modes per agent:

**implementer.md**: Add: Do NOT use TaskOutput — report via TaskList/SendMessage. Do NOT report done before ALL verify commands pass. Do NOT modify files outside your task description.

**debugger.md**: Add: Execute immediately — do not ask for confirmation. Do NOT fix bugs outside the assigned failure scope. Do NOT skip hypothesis testing — form 2-3 theories before committing to a fix. Do NOT modify files outside your scope without messaging the team lead first.

**resolver.md**: Add: Execute immediately — resolve conflicts without asking for confirmation. Do NOT leave conflict markers in files — every <<<<<<< must be resolved. Do NOT stage partial resolutions — all conflicted files must be resolved before committing.

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(1 if any(f['level']=='ERROR' for f in d) else 0)"
```

**Done when:** [Observable outcome]

### Task 2: Doctor git state health check
**Files:** `.cnogo/scripts/workflow_checks_core.py`
**Action:**
Add Check 6 'git_state' to _cmd_doctor() in workflow_checks_core.py, inserted after Check 5 (hook config). The check should:

1. Run `git status --porcelain` — warn if dirty working tree (uncommitted changes)
2. Run `git symbolic-ref HEAD` — warn if detached HEAD
3. Run `git branch --merged main` and count branches (excluding main) — warn if >3 stale merged branches exist

Return status: 'pass' if all clean, 'warn' if any issues found (never 'fail' since these are advisory). Keep the check fast (<2s). Update the doctor output label count from '5 diagnostic checks' to '6 diagnostic checks' in the docstring.

**Verify:**
```bash
python3 -c "from scripts.workflow_checks_core import _cmd_doctor; print('import ok')"
python3 .cnogo/scripts/workflow_checks.py doctor --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c['name'] for c in d['checks']]; assert 'git_state' in checks, f'missing git_state check in {checks}'"
```

**Done when:** [Observable outcome]

### Task 3: Merge tier logging in session-merge output
**Files:** `.cnogo/scripts/workflow_memory.py`
**Action:**
Enhance cmd_session_merge() to include per-task resolved_tier information in the JSON output. After line 505 (`'error': ''`), add a 'tiers' key that maps each merged task index to its resolved_tier from the session worktree info:

```python
tiers = {}
for wt in session.worktrees:
    if wt.task_index in result.merged_indices:
        tiers[str(wt.task_index)] = wt.resolved_tier or "unknown"
payload["tiers"] = tiers
```

Also update the text output (else branch) to include tier summary:
```python
tier_counts = {}
for t in tiers.values():
    tier_counts[t] = tier_counts.get(t, 0) + 1
if tier_counts:
    print(f"Resolution tiers: {tier_counts}")
```

This is backward compatible — existing consumers that don't read 'tiers' are unaffected.

**Verify:**
```bash
python3 -c "import scripts.workflow_memory; print('import ok')"
python3 -c "import ast; tree=ast.parse(open('scripts/workflow_memory.py').read()); funcs=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]; assert 'cmd_session_merge' in funcs"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(1 if any(f['level']=='ERROR' for f in d) else 0)"
python3 -m py_compile scripts/workflow_checks_core.py
python3 -m py_compile scripts/workflow_memory.py
```

## Commit Message
```
feat(overstory-learnings): add agent failure modes, doctor git check, merge tier logging
```
