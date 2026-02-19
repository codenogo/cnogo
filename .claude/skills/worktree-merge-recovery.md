# Worktree Merge Recovery

Use this skill when `session-merge` reports conflicts in team implementation.

## Goal

Resolve merge conflicts deterministically, preserve task order, and resume safely.

## Protocol

1. Capture current state:
```bash
python3 scripts/workflow_memory.py session-status --json
python3 scripts/workflow_memory.py session-merge --json
git status --porcelain
```

2. Triage conflict:
- identify `conflictIndex` and `conflictFiles`
- confirm whether conflict is mechanical (format/import/order) or semantic

3. Resolution rules:
- preserve already merged behavior unless conflict proves defect
- prefer smallest edit that satisfies both task intents
- keep change scoped to conflicted files only

4. Verify before retry:
```bash
<task verify commands>
<plan verify commands if available>
```

5. Retry merge:
```bash
python3 scripts/workflow_memory.py session-merge --json
```

6. Retry limits:
- max 2 resolver attempts
- if still blocked: `git merge --abort`, report unresolved conflict with context

## Output

- Conflict root cause
- Resolution applied
- Retry result and remaining risk
