# Plan 02: Command Logic and Documentation

## Goal
Update `/implement` to use the `parallelizable` hint, update `/status` to display claim age with stale indicator, and document version pinning.

## Prerequisites
- [ ] Plan 01 complete (WORKFLOW.json has `staleIndicatorMinutes`, validate accepts `parallelizable`)

## Tasks

### Task 1: Update /implement detection logic for parallelizable flag
**Files:** `.claude/commands/implement.md`
**Action:**
Update Step 1c ("Team Mode") detection logic to use the `parallelizable` field from plan JSON. The new logic should be:

1. If `$ARGUMENTS` contains `--team` → delegate to `/team implement`
2. If plan JSON has `"parallelizable": true` AND Agent Teams available → auto-delegate (still run `detect_file_conflicts()` and warn if conflicts exist, but proceed)
3. If plan JSON has `"parallelizable": false` → serial execution (override auto-detection)
4. If `parallelizable` not present → fall back to existing heuristic (>2 tasks, non-overlapping files, Agent Teams available)

Also update the Arguments section to mention that `parallelizable` in plan JSON influences auto-detection.

**Verify:**
```bash
grep -q 'parallelizable' .claude/commands/implement.md && echo "PASS: implement.md mentions parallelizable" || echo "FAIL"
```

**Done when:** `/implement` Step 1c documents the `parallelizable`-aware detection logic.

### Task 2: Update /status to display claim age
**Files:** `.claude/commands/status.md`
**Action:**
Update Step 3b ("Memory Status") → "Team Implementation Progress" section. Enhance the Python snippet that displays in-progress epics to also show claim age for each active task.

For each child task with `status == 'in_progress'`:
- Calculate minutes since `updated_at` (the last memory operation)
- Read `staleIndicatorMinutes` from WORKFLOW.json `agentTeams` section (default 10)
- Display: `🔄 cn-xxx Task Title (@assignee) — claimed 5m ago`
- If age > threshold: `⚠️ cn-xxx Task Title (@assignee) — claimed 23m ago (stale?)`

The Python snippet should:
1. Import `datetime` and `json`
2. Load WORKFLOW.json to get `staleIndicatorMinutes` (default 10)
3. For each in-progress child, compute age from `updated_at`
4. Use ⚠️ icon instead of 🔄 when age exceeds threshold

**Verify:**
```bash
grep -q 'staleIndicatorMinutes' .claude/commands/status.md && echo "PASS: status.md reads stale config" || echo "FAIL"
grep -q 'updated_at' .claude/commands/status.md && echo "PASS: status.md uses updated_at" || echo "FAIL"
```

**Done when:** `/status` displays claim age for active tasks and highlights stale ones.

### Task 3: Document version pinning in PROJECT.md and CLAUDE.md
**Files:** `docs/planning/PROJECT.md`, `CLAUDE.md`
**Action:**
Per CONTEXT.md decision: "Document in PROJECT.md + CLAUDE.md — lightweight, no runtime check needed."

In `docs/planning/PROJECT.md`:
- Add a row to the Constraints table: `Agent Teams requires Claude Code >= 2.1 with CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | `Experimental feature — pin to known-good version`
- Add a row to Key Decisions: `Pin Agent Teams to Claude Code >= 2.1` | `Feature is experimental; version pinning prevents breakage` | `2026-02`

In `CLAUDE.md`:
- In the existing project overview or a suitable section, add a brief note: "Agent Teams requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` environment variable and Claude Code >= 2.1."

Keep changes minimal — just the version pin documentation.

**Verify:**
```bash
grep -q 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' docs/planning/PROJECT.md && echo "PASS: PROJECT.md has env var" || echo "FAIL"
grep -q 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' CLAUDE.md && echo "PASS: CLAUDE.md has env var" || echo "FAIL"
```

**Done when:** Both docs reference the required env var and minimum Claude Code version.

## Verification

After all tasks:
```bash
grep -q 'parallelizable' .claude/commands/implement.md
grep -q 'staleIndicatorMinutes' .claude/commands/status.md
grep -q 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' docs/planning/PROJECT.md
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(multi-agent-enhancements): command logic and version pinning docs

- Update /implement to use parallelizable hint from plan JSON
- Update /status to display claim age with stale indicator
- Document Agent Teams version pinning in PROJECT.md and CLAUDE.md
```

---
*Planned: 2026-02-14*
