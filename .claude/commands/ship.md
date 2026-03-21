# Ship Changes
<!-- effort: high -->

## Your Task

### Step 0: Branch Verification

```bash
git branch --show-current
git status --porcelain
```

Rules:
- Refuse to ship from `main/master`.
- Must be on `feature/<feature-slug>`. Otherwise stop.

**Step 0a: Clean merged branches**

```bash
git branch --merged main | grep -v '^\*\|main' | xargs -r git branch -d
git remote prune origin
```

### Step 1: Phase Check + Preflight

```bash
python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>
```

Warn if not in `ship` phase.
- Load the latest Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-show <feature-slug> --json`.
- Stop unless `ship.status == ready`, unless the Delivery Run already has `ship.status == in_progress|completed`.
- Run the staged review/freshness gate:
```bash
python3 .cnogo/scripts/workflow_checks.py ship-ready --feature <feature-slug>
```
If this fails, stop.

### Step 1a: Start Ship Tracking

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-start <feature-slug>
```
This sets `ship.status = in_progress`.

### Step 2: Commit (if needed)

```bash
git add -A
git commit -m "<conventional-commit-message>"
```
Choose `feat|fix|refactor|docs|test|chore` from the diff.

### Step 3: Push Branch

```bash
git push -u origin $(git branch --show-current)
```

### Step 4: Create PR

```bash
gh pr create --title "<title>" --body "<summary/testing/links>"
```
Include summary, testing, and planning links.

### Step 4a: Record Ship Completion

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-complete <feature-slug> <commit-sha> --branch <branch> --pr-url <pr-url>
```

If commit, push, or PR creation fails, record it with:

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-fail <feature-slug> --error "<summary>"
```

### Step 5: Memory Sync (if enabled)

```bash
python3 .cnogo/scripts/workflow_memory.py sync
```
If feature IDs are known, close shipped issues and update phase.

### Step 6: Feature Lifecycle Closure

Apply `.claude/skills/feature-lifecycle-closure.md` checklist before final handoff.

### Step 7: Local Cleanup

Optional cleanup.

## Output

- PR URL
- commit(s) shipped
- verification summary
- any remaining follow-up actions
