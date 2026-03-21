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

### Step 1: Phase Check + Preflight

```bash
python3 .cnogo/scripts/workflow_memory.py phase-get <feature-slug>
```

Warn if not in `ship` phase.
- Load the feature-level Work Order with `python3 .cnogo/scripts/workflow_memory.py work-show <feature-slug> --json`.
- Load the latest Delivery Run with `python3 .cnogo/scripts/workflow_memory.py run-show <feature-slug> --json`.
- Treat the run's resolved profile as ship policy context.
- Stop unless `ship.status == ready`, unless the Delivery Run already has `ship.status == in_progress|completed`.
- Run the ship gate:
```bash
python3 .cnogo/scripts/workflow_checks.py ship-ready --feature <feature-slug>
```
If this fails, stop.

### Step 1a: Start Ship Tracking

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-start <feature-slug>
```
This sets `ship.status = in_progress`.

### Step 2: Compute Ship Draft

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-draft <feature-slug> --json
```

Review the returned draft before proceeding.

### Step 3: Commit + Push

Use the draft output to stage and commit:

```bash
<gitAddCommand from draft>
git commit -m "$(cat <<'EOF'
<commitMessage from draft>

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
git push -u origin $(git branch --show-current)
```

### Step 4: Create PR

Use the draft `prTitle` and `prBody`:

```bash
gh pr create --title "<prTitle from draft>" --body "$(cat <<'EOF'
<prBody from draft>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Step 4a: Record Ship Completion

Auto-infer mode:

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-complete <feature-slug> --pr-url <pr-url>
```

Then confirm the Work Order rolled up to shipped state:

```bash
python3 .cnogo/scripts/workflow_memory.py work-next <feature-slug> --json
```

If commit, push, or PR creation fails, record it with:

```bash
python3 .cnogo/scripts/workflow_memory.py run-ship-fail <feature-slug> --error "<summary>"
```

### Step 5: Memory Sync (if enabled)

```bash
python3 .cnogo/scripts/workflow_memory.py sync
```
This exports `.cnogo/issues.jsonl` without staging it. Use `sync --stage` only if you intentionally want it in git.

### Step 6: Feature Lifecycle Closure

Apply `.claude/skills/feature-lifecycle-closure.md` before final handoff.

### Step 7: Local Cleanup

Optional.

## Output

- PR URL
- shipped commit(s)
- Work Order completion state
- verification summary
- follow-up actions
