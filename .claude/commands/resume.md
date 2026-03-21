# Resume
<!-- effort: low -->

Restore context from handoff and memory/git state.

## Your Task

### Step 1: Load Handoff + Memory

```bash
cat docs/planning/work/HANDOFF.md 2>/dev/null || echo "No handoff file"
python3 .cnogo/scripts/workflow_memory.py prime --limit 8
python3 .cnogo/scripts/workflow_memory.py checkpoint
python3 .cnogo/scripts/workflow_memory.py ready --limit 10
```

### Step 1.5: Initiative Context (If Applicable)

```bash
python3 .cnogo/scripts/workflow_memory.py initiative-current --json
```

If `found=true`, include initiative context in Step 5 (Next):
- Initiative progress (N/M features completed)
- Blocked features that need attention
- Pending shapeFeedback count
- Initiative-level recommended next action

If `found=false`, skip this step silently.

### Step 2: Verify Git

```bash
git branch --show-current
git status --porcelain
git stash list
```

If needed:

```bash
git stash pop
```

### Step 3: Rehydrate Working Context

Open handoff-mentioned or active files.

### Step 4: Team Recovery (If Relevant)

If resuming team execution:

```bash
python3 .cnogo/scripts/workflow_memory.py list --type epic --status in_progress --limit 5
python3 .cnogo/scripts/workflow_memory.py session-status --json
python3 .cnogo/scripts/workflow_memory.py session-reconcile
```

`session-status --json` is the source of truth. When it returns a linked `deliveryRun`, inspect its `status`, `integration`, and `reviewReadiness` before choosing `/team implement`, more verification, or `/review`.
If unclear, inspect `python3 .cnogo/scripts/workflow_memory.py work-list --needs-attention --json`, `work-show <feature> --json`, or `run-watch-patrol --feature <feature>`.

If reconcile found orphaned issues, rerun `python3 .cnogo/scripts/workflow_memory.py prime`.

Active session: continue with `/team implement <feature> <plan>`; otherwise use `/implement`.

### Step 5: Next

Summarize:
- where execution stopped
- readiness
- exact next command

## Output

- Restored context summary
- One next step
