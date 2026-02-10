# Plan 02: Update Settings, /spawn Wrapper, and Effort Hints

## Goal
Update settings.json with Agent Teams env var, refactor /spawn to delegate to .claude/agents/ definitions, and add effort hint comments to all command files.

## Prerequisites
- [ ] Plan 01 complete (agent definitions must exist for /spawn to reference)

## Tasks

### Task 1: Update .claude/settings.json with Agent Teams env var
**Files:** `.claude/settings.json`
**Action:**
Add an `env` section to settings.json with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` set to `"1"`. Place it as a top-level key alongside `hooks` and `permissions`. Do NOT modify existing hooks or permissions — additive only.

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "hooks": { ... existing ... },
  "permissions": { ... existing ... }
}
```

**Verify:**
```bash
python3 -c "import json; d=json.load(open('.claude/settings.json')); assert d['env']['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] == '1'; print('OK')"
python3 -c "import json; d=json.load(open('.claude/settings.json')); assert 'hooks' in d and 'permissions' in d; print('Existing keys preserved')"
```

**Done when:** settings.json has env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1" and all existing hooks/permissions are intact.

### Task 2: Refactor /spawn to reference .claude/agents/ definitions
**Files:** `.claude/commands/spawn.md`
**Action:**
Update spawn.md to:

1. Keep the existing specialization table and argument parsing (backward compat)
2. Add a new section "Agent Definitions" explaining that each specialization now maps to a `.claude/agents/<name>.md` file
3. Update Step 3 (Launch Subagent) to instruct Claude to delegate to the matching `.claude/agents/` definition instead of using the inline prompt
4. Add mapping table: security → security-scanner, tests → test-writer, docs → docs-writer, perf → perf-analyzer, api → api-reviewer, refactor → refactorer, migrate → migrate, review → code-reviewer
5. Keep inline prompts as fallback if agent file doesn't exist
6. Add note that users can also invoke agents directly: "Use the code-reviewer agent to review my changes"

**Verify:**
```bash
grep "claude/agents" .claude/commands/spawn.md
grep "security-scanner" .claude/commands/spawn.md
grep "fallback" .claude/commands/spawn.md
```

**Done when:** /spawn references .claude/agents/ definitions with mapping table and fallback behavior.

### Task 3: Add effort hint comments to all command .md files
**Files:** `.claude/commands/brainstorm.md`, `.claude/commands/bug.md`, `.claude/commands/changelog.md`, `.claude/commands/close.md`, `.claude/commands/context.md`, `.claude/commands/debug.md`, `.claude/commands/discuss.md`, `.claude/commands/implement.md`, `.claude/commands/init.md`, `.claude/commands/mcp.md`, `.claude/commands/pause.md`, `.claude/commands/plan.md`, `.claude/commands/quick.md`, `.claude/commands/release.md`, `.claude/commands/research.md`, `.claude/commands/resume.md`, `.claude/commands/review.md`, `.claude/commands/rollback.md`, `.claude/commands/ship.md`, `.claude/commands/status.md`, `.claude/commands/sync.md`, `.claude/commands/tdd.md`, `.claude/commands/validate.md`, `.claude/commands/verify.md`, `.claude/commands/verify-ci.md`, `.claude/commands/background.md`, `.claude/commands/spawn.md`
**Action:**
Add an HTML comment at line 2 of each command file (after the `# Title` line) with the recommended effort level. Use this mapping from CONTEXT.md:

- `<!-- effort: low -->` — status, pause, resume, context, validate, close, changelog
- `<!-- effort: medium -->` — quick, init, rollback, sync, background, spawn, mcp
- `<!-- effort: high -->` — discuss, plan, implement, review, ship, tdd, verify, verify-ci, brainstorm, bug
- `<!-- effort: max -->` — research, debug, release

**Verify:**
```bash
grep -l "effort:" .claude/commands/*.md | wc -l  # Should be 27
grep -c "effort: low" .claude/commands/*.md | grep -v ":0$" | wc -l    # Should be 7
grep -c "effort: medium" .claude/commands/*.md | grep -v ":0$" | wc -l  # Should be 7
grep -c "effort: high" .claude/commands/*.md | grep -v ":0$" | wc -l    # Should be 10
grep -c "effort: max" .claude/commands/*.md | grep -v ":0$" | wc -l     # Should be 3
```

**Done when:** All 27 command files have effort hint comments on line 2.

## Verification

After all tasks:
```bash
python3 -c "import json; d=json.load(open('.claude/settings.json')); print('Agent Teams:', d['env']['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'])"
grep "claude/agents" .claude/commands/spawn.md | head -3
grep -l "effort:" .claude/commands/*.md | wc -l
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(opus-46-agents-workflow-improvements): settings, spawn wrapper, effort hints

- Add CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 to settings.json env
- Refactor /spawn to delegate to .claude/agents/ definitions with fallback
- Add effort hint comments (low/medium/high/max) to all 27 command files
```

---
*Planned: 2026-02-10*
