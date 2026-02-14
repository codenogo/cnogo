# Plan 02: Install + Session Commands

## Goal
Update install.sh to remove STATE.md and auto-init memory, then migrate the four most complex STATE.md-dependent commands (pause, resume, status, sync) to use memory exclusively.

## Prerequisites
- [ ] Plan 01 complete (prime() enhanced, feature inference from memory, validation updated)

## Tasks

### Task 1: Update install.sh — Remove STATE.md, Add Auto-Delete, Auto-Init Memory
**Files:** `install.sh`
**Action:**
Three changes:

1. **Remove STATE.md from template loop** (line 177): Change `for file in PROJECT.md STATE.md ROADMAP.md WORKFLOW.json` to `for file in PROJECT.md ROADMAP.md WORKFLOW.json`

2. **Add auto-delete migration** — after the docs/planning section, add:
```bash
# Migration: remove STATE.md (replaced by memory engine)
if [ -f "$TARGET_DIR/docs/planning/STATE.md" ]; then
    echo -e "   ├── STATE.md ${YELLOW}(removed — replaced by memory engine)${NC}"
    rm "$TARGET_DIR/docs/planning/STATE.md"
fi
```

3. **Add memory auto-init** — after the "Done" banner, before "Next steps", add:
```bash
# Initialize memory engine
python3 "$TARGET_DIR/scripts/workflow_memory.py" init 2>/dev/null && echo -e "${GREEN}Memory engine initialized${NC}" || echo -e "${YELLOW}Memory engine init skipped (run manually: python3 scripts/workflow_memory.py init)${NC}"
```

This enforces CONTEXT.md decisions #1 (memory required at install) and #8 (auto-delete on install).

**Verify:**
```bash
bash -n install.sh && echo "Syntax OK"
```

**Done when:** install.sh no longer copies STATE.md, auto-deletes existing copies, and auto-initializes memory.

### Task 2: Migrate pause.md + resume.md — Handoff via Memory Metadata
**Files:** `.claude/commands/pause.md`, `.claude/commands/resume.md`
**Action:**

**pause.md changes:**
- Step 2: Remove `cat docs/planning/STATE.md | head -20`. Replace with memory query:
  ```bash
  python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; from pathlib import Path; print(prime(root=Path('.')))"
  ```
- Step 3: Replace "Update `docs/planning/STATE.md` with handoff section" with "Store handoff in memory". Write handoff metadata to the active epic:
  ```python
  from scripts.memory import list_issues, update, create
  epics = list_issues(issue_type='epic', status='in_progress', root=root)
  if not epics:
      epics = list_issues(issue_type='epic', status='open', root=root)
  if epics:
      update(epics[0].id, metadata={'handoff': { ... }}, root=root)
  else:
      # No active epic — create transient session issue
      create('Session Handoff', issue_type='task', metadata={'handoff': { ... }}, labels=['session'], root=root)
  ```
- Step 3b: Keep memory sync as-is
- Step 4: Remove `cat docs/planning/STATE.md | grep -A 30 "Session Handoff"`. Replace with memory verification:
  ```bash
  python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import list_issues; from pathlib import Path; epics = list_issues(issue_type='epic', root=Path('.')); [print(f'{e.id}: handoff={e.metadata.get(\"handoff\",\"none\")}') for e in epics if e.metadata.get('handoff')]"
  ```
- Remove all remaining references to STATE.md

**resume.md changes:**
- Step 1: Replace `cat docs/planning/STATE.md` with memory query for handoff:
  ```python
  from scripts.memory import list_issues, show
  epics = list_issues(issue_type='epic', root=root)
  for e in epics:
      full = show(e.id, root=root)
      if full and full.metadata.get('handoff'):
          # Found handoff
  ```
- Step 3b: Keep memory context loading as-is
- Step 6: Replace "update STATE.md" with clearing handoff metadata:
  ```python
  update(epic_id, metadata={'handoff': None}, root=root)
  ```
- Remove all remaining references to STATE.md and "Session Handoff" markdown sections

**Verify:**
```bash
# Check no STATE.md references remain
grep -c "STATE.md" .claude/commands/pause.md .claude/commands/resume.md || echo "Clean: 0 references"
```

**Done when:** pause.md writes handoff to memory metadata, resume.md reads from memory metadata. Zero STATE.md references in either file.

### Task 3: Migrate status.md + sync.md — Drop STATE.md, Use Memory Only
**Files:** `.claude/commands/status.md`, `.claude/commands/sync.md`
**Action:**

**status.md changes:**
- Step 1: Replace `cat docs/planning/STATE.md` with:
  ```bash
  python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime, stats; from pathlib import Path; root=Path('.'); print(prime(root=root)); print(); s=stats(root=root); print(f'Total: {s.get(\"total\",0)} | Open: {s.get(\"open\",0)} | Active: {s.get(\"in_progress\",0)} | Closed: {s.get(\"closed\",0)}')"
  ```
- Remove the separate "Step 3b: Memory Status" section — memory IS the status now, not an optional add-on
- Remove all STATE.md references

**sync.md changes:**
- Remove "Solution A: Manual Sync File (Modes 1-4)" entirely (CONTEXT.md decision #4)
- Remove the "Choosing a Mode" table entries for Modes 1-4
- Make "Solution B: Memory Engine (Mode 7)" the primary sync mechanism
- Keep "Solution C: Agent Teams (Modes 5-6)" as-is
- Remove all STATE.md grep commands (lines 61, 81)
- Update the problem statement to remove "Each has its own STATE.md"

**Verify:**
```bash
# Check no STATE.md references remain
grep -c "STATE.md" .claude/commands/status.md .claude/commands/sync.md || echo "Clean: 0 references"
```

**Done when:** status.md and sync.md use memory exclusively. Zero STATE.md references. Modes 1-4 removed from sync.md.

## Verification

After all tasks:
```bash
# install.sh syntax
bash -n install.sh

# No STATE.md refs in migrated commands
for f in pause resume status sync; do
    count=$(grep -c "STATE.md" ".claude/commands/$f.md" 2>/dev/null || echo 0)
    echo "$f.md: $count STATE.md refs"
done

# Validation still passes
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(kill-state-md): migrate install + session commands off STATE.md

- Remove STATE.md from install.sh template loop + add auto-delete migration
- Add memory auto-init to install.sh
- Migrate pause/resume to store handoff in memory metadata
- Migrate status/sync to use memory-only state
- Remove sync Modes 1-4 (manual grep-based)
```

---
*Planned: 2026-02-14*
