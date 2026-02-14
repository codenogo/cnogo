# Plan 01: Core Worktree Module

## Goal
Create `scripts/memory/worktree.py` with all worktree lifecycle primitives — session state, setup, merge, and cleanup.

## Prerequisites
- [x] CONTEXT.md complete with all decisions

## Tasks

### Task 1: State Dataclasses + Git Helpers + State File I/O
**Files:** `scripts/memory/worktree.py`
**Action:**
Create the new module with:

1. **Dataclasses** (use `dataclasses` stdlib module):
   - `WorktreeInfo`: task_index, name, branch, path (absolute), status (created|executing|completed|merged|conflict|cleaned), memory_id, conflict_files (list[str])
   - `MergeResult`: success (bool), merged_indices (list[int]), conflict_index (int|None), conflict_files (list[str])
   - `WorktreeSession`: schema_version (1), feature, plan_number, base_commit, base_branch, phase (setup|executing|agents_complete|merging|merged|verified|committed|cleaned), worktrees (list[WorktreeInfo]), merge_order (list[int]), merged_so_far (list[int]), timestamp

2. **State file I/O** — read/write `.cnogo/worktree-session.json`:
   - `save_session(session, root)` — serialize to JSON, write atomically (write to temp file, rename)
   - `load_session(root)` → `WorktreeSession | None` — read and deserialize, None if no file
   - `delete_session_file(root)` — remove the file

3. **Git helpers** (use `subprocess.run`):
   - `_run_git(*args, cwd=None)` → `subprocess.CompletedProcess` — raises on non-zero exit
   - `_current_commit(root)` → str — `git rev-parse HEAD`
   - `_current_branch(root)` → str — `git branch --show-current`

Constants: `_SESSION_FILE = ".cnogo/worktree-session.json"`, `_CNOGO_DIR = ".cnogo"`, `_BRANCH_PREFIX = "agent/"`.

**Verify:**
```bash
python3 -c "compile(open('scripts/memory/worktree.py').read(), 'worktree.py', 'exec'); print('PASS')"
```
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.worktree import WorktreeSession, WorktreeInfo, MergeResult, save_session, load_session; print('PASS')"
```

**Done when:** Module imports cleanly, dataclasses and I/O functions are available.

### Task 2: create_session() — Setup Primitives
**Files:** `scripts/memory/worktree.py`
**Action:**
Add `create_session(plan_json_path, root, task_descriptions)` → `WorktreeSession`:

1. Read plan JSON for feature + planNumber
2. Record `base_commit` via `_current_commit(root)` and `base_branch` via `_current_branch(root)`
3. Compute project name from `root.resolve().name` for worktree directory naming
4. For each non-skipped task in `task_descriptions`:
   a. Branch name: `agent/<feature>-<plan>-task-<N>` (per CONTEXT.md decision)
   b. Create branch: `git branch <branch-name> <base_commit>`
   c. Worktree path: `../<project>-wt-<feature>-<plan>-<N>/` (sibling directory, per CONTEXT.md)
   d. Create worktree: `git worktree add <path> <branch-name>`
   e. Symlink `.cnogo/`: `os.symlink(root/.cnogo (absolute), worktree_path/.cnogo)`
   f. Record `WorktreeInfo` with status `"created"`
5. Compute `merge_order` = list of non-skipped task indices in order
6. Set `phase = "setup"`
7. Call `save_session()` to write checkpoint
8. Update `phase = "executing"`, save again

**Error handling:** If any step fails, clean up all worktrees created so far (remove worktree + delete branch), then raise.

**Verify:**
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.worktree import create_session; print('PASS')"
```

**Done when:** `create_session` creates worktrees with symlinked `.cnogo/` and writes session state file.

### Task 3: merge_session() + cleanup_session()
**Files:** `scripts/memory/worktree.py`
**Action:**
Add two functions:

**`merge_session(session, root)`** → `MergeResult`:
1. Update phase to `"merging"`, save
2. For each task_index in `session.merge_order`, skipping `session.merged_so_far`:
   a. Find the worktree info for this task_index
   b. Run `git merge --no-ff <branch-name>` from `root`
   c. If clean (exit code 0):
      - Append task_index to `session.merged_so_far`
      - Update worktree status to `"merged"`, save
   d. If conflict (exit code 1, stderr contains "CONFLICT"):
      - Parse conflicted files from `git diff --name-only --diff-filter=U`
      - Update worktree status to `"conflict"`, set `conflict_files`, save
      - Return `MergeResult(success=False, merged_indices=session.merged_so_far, conflict_index=task_index, conflict_files=...)`
3. If all merged cleanly:
   - Update phase to `"merged"`, save
   - Return `MergeResult(success=True, merged_indices=session.merged_so_far, conflict_index=None, conflict_files=[])`

**`get_conflict_context(session, task_index, plan_json_path, root)`** → `dict`:
1. Read the conflicted files (with markers) from the working tree
2. Read the plan JSON to get the conflicting task's action text
3. Get the list of already-merged task descriptions for context
4. Return `{"conflict_files": [...], "conflict_content": {file: content}, "task_action": "...", "merged_tasks": [...]}`

**`cleanup_session(session, root)`**:
1. For each worktree in session (status != "cleaned"):
   a. `git worktree remove --force <path>` (force in case of uncommitted changes)
   b. `git branch -D <branch>` (delete branch)
   c. Update worktree status to `"cleaned"`, save
2. `git worktree prune` (clean up stale references)
3. `delete_session_file(root)`

**Verify:**
```bash
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.worktree import merge_session, cleanup_session, get_conflict_context; print('PASS')"
```

**Done when:** Merge, conflict context, and cleanup functions are importable and handle the full lifecycle.

## Verification

After all tasks:
```bash
python3 -c "compile(open('scripts/memory/worktree.py').read(), 'worktree.py', 'exec'); print('PASS')"
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory.worktree import WorktreeSession, WorktreeInfo, MergeResult, create_session, merge_session, cleanup_session, get_conflict_context, save_session, load_session; print('ALL IMPORTS PASS')"
```
```bash
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(worktree-parallel-agents): core worktree module with setup, merge, and cleanup

- Add scripts/memory/worktree.py with full lifecycle primitives
- State file checkpointing for crash recovery
- Sequential merge with conflict detection
- Resolver context preparation for agent-assisted conflict resolution
```

---
*Planned: 2026-02-14*
