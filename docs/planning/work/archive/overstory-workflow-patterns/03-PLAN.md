# Plan 03: Add agent health monitoring (watchdog) and unified /doctor diagnostic command

## Goal
Add agent health monitoring (watchdog) and unified /doctor diagnostic command

## Tasks

### Task 1: Create watchdog.py stale task detector
**Files:** `.cnogo/scripts/memory/watchdog.py`, `.cnogo/scripts/memory/__init__.py`
**Action:**
Create new module scripts/memory/watchdog.py (stdlib only). Implement: (1) check_stale_tasks(root, stale_minutes=10) -> list[dict]: read worktree-session.json, find tasks with status='executing' whose timestamp is older than stale_minutes. Return list of {task_index, name, branch, minutes_stale, memory_id}. (2) check_stale_issues(root, stale_days=30) -> list[dict]: query memory DB for issues that are open, unassigned, and created_at older than stale_days. Return list of {id, title, days_stale}. (3) record_stale_event(root, stale_info, actor='watchdog'): record a 'stale_detected' event in memory DB for each stale task/issue. (4) run_all_checks(root, config) -> dict: run both checks using thresholds from WORKFLOW.json agentTeams.staleIndicatorMinutes and freshness.contextMaxAgeDays. Return {stale_tasks: [...], stale_issues: [...], checked_at: timestamp}. In __init__.py: add watchdog exports to __all__ with lazy imports (check_stale_tasks, check_stale_issues, run_watchdog_checks).

**Verify:**
```bash
python3 -m py_compile scripts/memory/watchdog.py
python3 -c "from scripts.memory.watchdog import check_stale_tasks, check_stale_issues; print('OK')"
```

**Done when:** [Observable outcome]

### Task 2: Add doctor subcommand to workflow_checks
**Files:** `.cnogo/scripts/workflow_checks_core.py`
**Action:**
Add 'doctor' subcommand to workflow_checks_core.py. In main(): add parser for 'doctor' with optional --json flag. Implement _cmd_doctor(root, wf, json_output=False) -> int that runs 5 checks sequentially: (1) Workflow validation: subprocess.run(['python3', 'scripts/workflow_validate.py'], capture_output) — pass/fail based on exit code. (2) Memory DB integrity: open .cnogo/memory.db, run 'PRAGMA integrity_check', pass if result is 'ok'. Skip if DB doesn't exist. (3) Orphaned worktrees: run 'git worktree list --porcelain', compare against worktree-session.json — warn on worktrees not tracked by any session. (4) Stale issues: import watchdog.check_stale_issues(), warn if any found. (5) Hook config sanity: check .claude/settings.json exists, verify hook script paths in settings point to existing files. Print pass/warn/fail per check. Return 0 if all pass/warn, 1 if any fail. JSON mode outputs {checks: [{name, status, details}]}.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_checks_core.py
python3 .cnogo/scripts/workflow_checks.py doctor --help
```

**Done when:** [Observable outcome]

### Task 3: Create /doctor slash command
**Files:** `.claude/commands/doctor.md`
**Action:**
Create .claude/commands/doctor.md slash command. Content: run `python3 .cnogo/scripts/workflow_checks.py doctor` and report results. Include guidance on interpreting pass/warn/fail. Mention that --json flag is available for programmatic consumption. Reference the 5 checks (workflow validation, DB integrity, orphaned worktrees, stale issues, hook config) so users know what's being checked.

**Verify:**
```bash
test -f .claude/commands/doctor.md
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/memory/watchdog.py
python3 -m py_compile scripts/workflow_checks_core.py
python3 .cnogo/scripts/workflow_checks.py doctor --help
```

## Commit Message
```
feat(doctor): add unified diagnostics and agent health monitoring
```
