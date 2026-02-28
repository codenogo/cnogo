# Plan 03: Lifecycle Commands + Cleanup

## Goal
Migrate all remaining commands off STATE.md, update documentation, and delete STATE.md and its template.

## Prerequisites
- [ ] Plan 01 complete (Python foundation)
- [ ] Plan 02 complete (install + session commands migrated)

## Tasks

### Task 1: Migrate Core Workflow Commands (discuss, plan, implement, team)
**Files:** `.claude/commands/discuss.md`, `.claude/commands/plan.md`, `.claude/commands/implement.md`, `.claude/commands/team.md`
**Action:**

All four commands follow the same pattern: they read STATE.md at the start and write "Update STATE.md" at the end. Apply these mechanical changes:

**discuss.md:**
- Step 1 (line ~20): Remove `2. Read docs/planning/STATE.md for current context`. Replace with:
  ```
  2. Query memory for current state: `python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"`
  ```
- Step 6: Remove the entire "Update State" section that writes to STATE.md. The memory epic created in Step 5 already tracks the feature status.

**plan.md:**
- Step 1 (line ~19): Remove `3. Read docs/planning/STATE.md for current position`. Replace with:
  ```
  3. Query memory for current state: `python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"`
  ```
- Step 5: Remove the "Update State" section that writes Current Focus to STATE.md. The memory tasks created in Step 4 already track plan status.

**implement.md:**
- Step 6 (line ~120): Remove `Update docs/planning/STATE.md with plan completion status.` The memory `close()` calls in Step 2 already track completion.

**team.md:**
- Remove any `Update docs/planning/STATE.md` reference (line ~59). The bridge module's memory integration already tracks team implementation progress.

**Verify:**
```bash
grep -c "STATE.md" .claude/commands/discuss.md .claude/commands/plan.md .claude/commands/implement.md .claude/commands/team.md 2>/dev/null || echo "Clean: 0 references"
```

**Done when:** Zero STATE.md references in discuss.md, plan.md, implement.md, team.md.

### Task 2: Migrate Remaining Commands (ship, close, verify, verify-ci, rollback, review)
**Files:** `.claude/commands/ship.md`, `.claude/commands/close.md`, `.claude/commands/verify.md`, `.claude/commands/verify-ci.md`, `.claude/commands/rollback.md`, `.claude/commands/review.md`
**Action:**

**ship.md:**
- Remove STATE.md feature inference (line ~94). Replace with memory query or branch name parsing.
- Remove Step 5 "Update STATE.md" section. Memory `close()` already handles feature completion.

**close.md:**
- Remove Step 2 "Update STATE.md" section (lines ~27-34). The feature is already tracked via memory.
- Remove the purpose description referencing STATE.md (line ~4). Replace with "Post-merge cleanup. Closes memory epic and optionally archives feature artifacts."

**verify.md:**
- Remove Step 8 "Update STATE.md" section (lines ~187-190). Memory tracks verification status.

**verify-ci.md:**
- Remove Step 5 "Update STATE.md" reference (line ~104). The VERIFICATION-CI.json artifact is sufficient.

**rollback.md:**
- Remove Step 4 "Update STATE.md" section (lines ~116-118). Memory and git log track rollback decisions.

**review.md:**
- Replace the STATE.md conditional (lines ~14-18) with memory-based feature detection:
  ```
  If memory has an active feature (query: `list_issues(issue_type='epic', status='in_progress')`), write to:
    - `docs/planning/work/features/<feature>/REVIEW.md`
    - `docs/planning/work/features/<feature>/REVIEW.json`
  ```

**Verify:**
```bash
grep -c "STATE.md" .claude/commands/ship.md .claude/commands/close.md .claude/commands/verify.md .claude/commands/verify-ci.md .claude/commands/rollback.md .claude/commands/review.md 2>/dev/null || echo "Clean: 0 references"
```

**Done when:** Zero STATE.md references in all six commands.

### Task 3: Update Documentation + Delete STATE.md
**Files:** `.claude/CLAUDE.md`, `CLAUDE.md`, `docs/planning/STATE.md`
**Action:**

**.claude/CLAUDE.md:**
- Line 16: Change `Optional structured task tracking` to `Structured task tracking (initialized at install)`
- Line 40: Remove `- Current state: docs/planning/STATE.md`
- Remove any remaining STATE.md references

**CLAUDE.md:**
- Remove all STATE.md references (lines ~26, ~142, ~165, ~204, ~244, ~467, ~552, ~675)
- Replace with memory engine references where context is needed (e.g., "current state tracked via memory engine")
- Update the directory structure to remove STATE.md
- Update command descriptions that mention STATE.md
- Update the session persistence principle to reference memory instead

**Delete files:**
- `docs/planning/STATE.md` — the file itself
- Verify `docs/planning/STATE.md` template is already removed from install.sh (done in Plan 02)

**Verify:**
```bash
# No STATE.md refs in docs
grep -c "STATE.md" .claude/CLAUDE.md CLAUDE.md 2>/dev/null || echo "Clean: 0 references"

# STATE.md file is gone
test ! -f docs/planning/STATE.md && echo "STATE.md deleted" || echo "STATE.md still exists"

# Full validation
python3 .cnogo/scripts/workflow_validate.py

# Comprehensive check: zero STATE.md refs in all commands
grep -rl "STATE.md" .claude/commands/ 2>/dev/null || echo "All commands clean"
```

**Done when:** Zero STATE.md references anywhere in the project. `docs/planning/STATE.md` deleted. Validation passes.

## Verification

After all tasks:
```bash
# Nuclear check: zero STATE.md references in the entire project (excluding git history and this plan)
grep -rl "STATE.md" --include="*.md" --include="*.py" --include="*.sh" --include="*.json" . 2>/dev/null | grep -v "kill-state-md/" | grep -v ".git/" || echo "Project is STATE.md-free"

# Validation
python3 .cnogo/scripts/workflow_validate.py

# Memory still works
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"
```

## Commit Message
```
feat(kill-state-md): remove STATE.md entirely — memory is single source of truth

- Migrate discuss, plan, implement, team commands off STATE.md
- Migrate ship, close, verify, verify-ci, rollback, review commands off STATE.md
- Update .claude/CLAUDE.md and CLAUDE.md documentation
- Delete docs/planning/STATE.md
```

---
*Planned: 2026-02-14*
