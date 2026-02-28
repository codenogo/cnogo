# Ship Current Changes
<!-- effort: high -->

Commit, push, and open a PR after review passes.

## Your Task

1. Optional phase warning (memory-enabled repos):
```bash
python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>
```
Warn if not in `ship` phase; continue only with confirmation.

2. Preflight:
- refuse to ship from `main/master`
- inspect `git status --porcelain`
- ensure review/verify artifacts are up to date
- require staged review + freshness gate:
```bash
python3 .cnogo/scripts/workflow_checks.py ship-ready --feature <feature-slug>
```
If this fails, stop and return the failing checks.

3. Commit (if needed):
```bash
git add -A
git commit -m "<conventional-commit-message>"
```
Choose `feat|fix|refactor|docs|test|chore` based on diff.

4. Push branch:
```bash
git push -u origin $(git branch --show-current)
```

5. Create PR:
```bash
gh pr create --title "<title>" --body "<summary/testing/links>"
```
PR body should include summary, key changes, testing evidence, and planning artifact links.

6. Memory sync (if enabled):
```bash
python3 .cnogo/scripts/workflow_memory.py sync
```
If feature IDs are known, close shipped issues and set phase accordingly.

7. Apply `.claude/skills/feature-lifecycle-closure.md` checklist before final handoff.
8. Optional local cleanup after confirmation (switch back to main and pull).

## Output

- PR URL
- commit(s) shipped
- verification summary
- any remaining follow-up actions
