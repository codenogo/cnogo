# Plan 02: Move hooks and templates, update all path references across commands, skills, and docs

## Goal
Move hooks and templates, update all path references across commands, skills, and docs

## Tasks

### Task 1: Move hook scripts to .cnogo/hooks/ and templates to .cnogo/templates/
**Files:** `.cnogo/hooks/hook-dangerous-cmd.sh`, `.cnogo/hooks/hook-pre-commit-secrets.sh`, `.cnogo/hooks/hook-sensitive-file.sh`, `.cnogo/hooks/hook-commit-confirm.sh`, `.cnogo/hooks/hook-post-commit-graph.sh`, `.cnogo/hooks/hook-subagent-stop.py`, `.cnogo/hooks/hook-pre-compact.py`, `.cnogo/hooks/install-githooks.sh`, `.cnogo/hooks/_bootstrap.py`, `.cnogo/templates/`
**Action:**
Create .cnogo/hooks/ directory. git mv all 5 shell hooks, 2 Python hooks, and install-githooks.sh from scripts/ to .cnogo/hooks/. Create .cnogo/hooks/_bootstrap.py (identical content to .cnogo/scripts/_bootstrap.py) so Python hooks can import from scripts.memory etc. Add bootstrap import to both Python hook files. git mv docs/templates/ to .cnogo/templates/.

**Micro-steps:**
- Create .cnogo/hooks/ directory
- git mv 5 shell hook scripts from scripts/ to .cnogo/hooks/
- git mv 2 Python hook scripts from scripts/ to .cnogo/hooks/
- git mv scripts/install-githooks.sh to .cnogo/hooks/
- Create .cnogo/hooks/_bootstrap.py (same as .cnogo/scripts/_bootstrap.py — adds .cnogo/ to sys.path)
- Add 'import _bootstrap  # noqa: F401' to both Python hook files
- git mv docs/templates/ to .cnogo/templates/
- Verify all hook files exist in new locations

**TDD:**
- required: `false`
- reason: File moves — no logic changes, verified by existence checks

**Verify:**
```bash
test -f .cnogo/hooks/hook-dangerous-cmd.sh
test -f .cnogo/hooks/hook-subagent-stop.py
test -f .cnogo/hooks/install-githooks.sh
test -f .cnogo/hooks/_bootstrap.py
test -f .cnogo/templates/CLAUDE-generic.md
test ! -f scripts/hook-dangerous-cmd.sh
test ! -d docs/templates
```

**Done when:** [Observable outcome]

### Task 2: Update .claude/settings.json hook paths and add _cnogo markers
**Files:** `.claude/settings.json`
**Action:**
Update all hook command paths in .claude/settings.json to reference new locations. Replace 'scripts/hook-' with '.cnogo/hooks/hook-' in shell hook commands. Replace 'scripts/workflow_hooks.py' with '.cnogo/scripts/workflow_hooks.py' in workflow hook commands. Replace 'scripts/hook-subagent-stop.py' with '.cnogo/hooks/hook-subagent-stop.py' and 'scripts/hook-pre-compact.py' with '.cnogo/hooks/hook-pre-compact.py'. Add '_cnogo': true to each hook entry for future update/uninstall identification. Update permission allowlist entries.

**Micro-steps:**
- Read current .claude/settings.json
- Update all 10 hook command paths: scripts/hook-*.sh → .cnogo/hooks/hook-*.sh, scripts/hook-*.py → .cnogo/hooks/hook-*.py, scripts/workflow_hooks.py → .cnogo/scripts/workflow_hooks.py
- Add '"_cnogo": true' to each cnogo hook entry for ownership marking
- Update permission allowlist: ./scripts/* → ./.cnogo/scripts/* and ./.cnogo/hooks/*
- Verify settings.json is valid JSON

**TDD:**
- required: `false`
- reason: Configuration update — verified by JSON parse and grep checks

**Verify:**
```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid JSON')"
grep -c '_cnogo' .claude/settings.json
grep -c '.cnogo/hooks/' .claude/settings.json
grep -c '.cnogo/scripts/workflow_hooks' .claude/settings.json
```

**Done when:** [Observable outcome]

### Task 3: Update all path references in commands, skills, and docs
**Files:** `.claude/commands/plan.md`, `.claude/commands/implement.md`, `.claude/commands/review.md`, `.claude/commands/team.md`, `.claude/commands/quick.md`, `.claude/commands/validate.md`, `.claude/commands/resume.md`, `.claude/commands/discuss.md`, `.claude/commands/sync.md`, `.claude/commands/verify.md`, `.claude/commands/ship.md`, `.claude/commands/brainstorm.md`, `.claude/commands/cnogo-init.md`, `.claude/commands/verify-ci.md`, `.claude/commands/research.md`, `.claude/commands/close.md`, `.claude/commands/status.md`, `.claude/commands/background.md`, `.claude/commands/doctor.md`, `.claude/commands/pause.md`, `.claude/skills/memory-sync-reconciliation.md`, `.claude/skills/feature-lifecycle-closure.md`, `.claude/skills/changed-scope-verification.md`, `.claude/skills/worktree-merge-recovery.md`, `.claude/skills/artifact-token-budgeting.md`, `.claude/skills/workflow-contract-integrity.md`, `.claude/CLAUDE.md`, `CLAUDE.md`
**Action:**
Bulk find-and-replace across 28 files (20 commands + 6 skills + 2 CLAUDE.md files). Primary replacements: 'python3 scripts/workflow_' → 'python3 .cnogo/scripts/workflow_', 'scripts/memory/' → '.cnogo/scripts/memory/', 'scripts/hook-' → '.cnogo/hooks/hook-', 'scripts/install-githooks' → '.cnogo/hooks/install-githooks', 'from scripts.memory' import examples updated to show sys.path.insert(0, '.cnogo') prefix. Total: ~89 references across 28 files.

**Micro-steps:**
- In all 20 command files: replace 'python3 scripts/workflow_' with 'python3 .cnogo/scripts/workflow_'
- In all 20 command files: replace 'scripts/install-githooks' with '.cnogo/hooks/install-githooks'
- In all 6 skill files: replace 'python3 scripts/workflow_' with 'python3 .cnogo/scripts/workflow_'
- In .claude/CLAUDE.md: update all script paths, Python import examples, and file path references
- In root CLAUDE.md: update all script paths and file path references
- In both CLAUDE.md files: update 'scripts/memory/' references to '.cnogo/scripts/memory/'
- Grep entire .claude/ and root for any remaining 'scripts/workflow_' or 'scripts/hook-' references
- Verify no old script path references remain

**TDD:**
- required: `false`
- reason: Mechanical text replacement — verified by grep for absence of old patterns

**Verify:**
```bash
! grep -r 'python3 scripts/workflow_' .claude/commands/ .claude/skills/ .claude/CLAUDE.md CLAUDE.md 2>/dev/null
! grep -r 'scripts/hook-' .claude/commands/ .claude/skills/ .claude/CLAUDE.md CLAUDE.md 2>/dev/null
! grep -r 'scripts/install-githooks' .claude/commands/ .claude/skills/ .claude/CLAUDE.md CLAUDE.md 2>/dev/null
grep -r '.cnogo/scripts/workflow_' .claude/commands/ | head -3
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
test ! -d scripts
test ! -d docs/templates
test -d .cnogo/hooks
test -d .cnogo/templates
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid JSON')"
! grep -r 'python3 scripts/workflow_' .claude/ CLAUDE.md 2>/dev/null
! grep -r 'scripts/hook-' .claude/ CLAUDE.md 2>/dev/null
python3 .cnogo/scripts/workflow_memory.py prime --limit 1
python3 -m pytest tests/ -x -q --tb=short 2>&1 | tail -5
```

## Commit Message
```
refactor(cnogo-packaging): move hooks/templates, update all path references
```
