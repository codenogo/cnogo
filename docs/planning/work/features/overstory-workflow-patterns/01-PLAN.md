# Plan 01: Add tiered merge conflict resolution (tiers 1-2) with resolution tracking to worktree.py

## Goal
Add tiered merge conflict resolution (tiers 1-2) with resolution tracking to worktree.py

## Tasks

### Task 1: Add resolvedTier to dataclasses
**Files:** `scripts/memory/worktree.py`
**Action:**
Add `resolved_tier` field (str, default '') to MergeResult and WorktreeInfo dataclasses. Add it to to_dict/from_dict serialization (camelCase: 'resolvedTier'). Valid tiers: 'clean-merge', 'auto-resolve', '' (unresolved). MergeResult gets resolved_tier to record which tier succeeded for the overall merge. WorktreeInfo gets resolved_tier to record per-branch resolution.

**Verify:**
```bash
python3 -c "from scripts.memory.worktree import MergeResult, WorktreeInfo; r = MergeResult(success=True, resolved_tier='clean-merge'); assert r.resolved_tier == 'clean-merge'; w = WorktreeInfo(task_index=0, name='t', branch='b', path='/tmp'); d = w.to_dict(); assert 'resolvedTier' in d; w2 = WorktreeInfo.from_dict(d); assert w2.resolved_tier == ''"
```

**Done when:** [Observable outcome]

### Task 2: Implement tier 2 auto-resolve in merge_session
**Files:** `scripts/memory/worktree.py`
**Action:**
In merge_session(), after a CONFLICT is detected (the except block at line ~388), before returning the MergeResult with success=False: (1) Import detect_file_conflicts from bridge module. (2) Check if the conflicting branch's files are disjoint from already-merged branches' files by calling _has_disjoint_files() — a new helper that reads plan task files[] and checks overlap. (3) If disjoint: abort the failed merge (git merge --abort), then re-attempt with auto-resolve strategy: run git merge, then for each conflicted file parse conflict markers and keep the incoming (agent) changes (everything between ======= and >>>>>>>), then git add and git commit. Set resolved_tier='auto-resolve' on the WorktreeInfo. (4) If NOT disjoint (files overlap): skip tier 2, keep the conflict state, return MergeResult with success=False as before. (5) On clean merge (no conflict), set resolved_tier='clean-merge'. Add helper function _auto_resolve_keep_incoming(root, conflict_files) that reads each file, strips conflict markers keeping incoming side, writes back, and stages.

**Verify:**
```bash
python3 -m py_compile scripts/memory/worktree.py
```

**Done when:** [Observable outcome]

### Task 3: Update merge recovery skill for tiers
**Files:** `.claude/skills/worktree-merge-recovery.md`
**Action:**
Update the worktree-merge-recovery skill to document the new tiered resolution. Add a section explaining: Tier 1 (clean-merge) happens automatically. Tier 2 (auto-resolve-keep-incoming) activates when files are disjoint. The resolver agent is Tier 3 (manual). Update the triage step to check resolved_tier in session state before attempting manual resolution.

**Verify:**
```bash
test -f .claude/skills/worktree-merge-recovery.md
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/memory/worktree.py
python3 -c "from scripts.memory.worktree import MergeResult; r = MergeResult(success=True, resolved_tier='auto-resolve'); assert r.resolved_tier == 'auto-resolve'"
```

## Commit Message
```
feat(merge): add tiered conflict resolution with auto-resolve for disjoint files
```
