# Plan 01: Extract Hooks to Scripts & Fix Critical Path

## Goal
Extract inline hook commands from settings.json into maintainable shell scripts, fix the broken PostToolUse path, and remove the pre-commit test runner.

## Prerequisites
- [ ] CONTEXT.md decisions finalized

## Tasks

### Task 1: Create hook scripts
**Files:** `.cnogo/hooks/hook-dangerous-cmd.sh`, `.cnogo/hooks/hook-sensitive-file.sh`, `.cnogo/hooks/hook-pre-commit-secrets.sh`
**Action:**
Extract the 3 PreToolUse hooks from `.claude/settings.json` into standalone shell scripts:

1. **`.cnogo/hooks/hook-dangerous-cmd.sh`** — Dangerous command blocker (from settings.json line 12).
   - Use `printf '%s' "$CLAUDE_TOOL_INPUT"` instead of `echo` to avoid shell injection (finding #3).
   - Expand patterns to catch evasions: split flags (`rm -r -f`), absolute paths (`/bin/rm`), `command rm` (finding #7).

2. **`.cnogo/hooks/hook-sensitive-file.sh`** — Sensitive file reader blocker (from settings.json line 21).
   - Use `printf '%s'` for safe input handling.

3. **`.cnogo/hooks/hook-pre-commit-secrets.sh`** — Pre-commit secret scanner (from settings.json line 30).
   - Combine 8 separate `grep -qE` calls into a single combined alternation pattern per file (finding #12).
   - Add missing patterns: Stripe (`sk_live_`, `pk_live_`), Twilio (`SK[a-fA-F0-9]{32}`), SendGrid, Firebase (`AIza`), DB connection strings (`postgres://.*:.*@`, `mongodb+srv://`) (finding #13).
   - Remove the `.md|.txt|.example|.sample` skip list — scan all files (finding H4).

All scripts: `#!/bin/bash`, `set -e`, read `$CLAUDE_TOOL_INPUT` from environment. Exit 0 for pass, exit 1 with error message for block.

**Verify:**
```bash
bash -n .cnogo/hooks/hook-dangerous-cmd.sh
bash -n .cnogo/hooks/hook-sensitive-file.sh
bash -n .cnogo/hooks/hook-pre-commit-secrets.sh
ls scripts/hook-*.sh | wc -l  # 3
```

**Done when:** 3 hook scripts exist, all pass syntax check.

### Task 2: Update settings.json hooks
**Files:** `.claude/settings.json`
**Action:**
1. Replace the 3 inline PreToolUse hook commands with calls to the extracted scripts:
   - Dangerous cmd: `bash .cnogo/hooks/hook-dangerous-cmd.sh`
   - Sensitive file: `bash .cnogo/hooks/hook-sensitive-file.sh`
   - Pre-commit secrets: `bash .cnogo/hooks/hook-pre-commit-secrets.sh`
2. **Remove the pre-commit test runner hook entirely** (the second Bash hook at line 33-34) (finding #5).
3. **Fix PostToolUse hook path**: Change `python3 $HOME/.claude/scripts/workflow_hooks.py post_edit` to `python3 .cnogo/scripts/workflow_hooks.py post_edit` (finding #2).
4. Result: PreToolUse should have 2 Bash matchers (one for dangerous cmd + pre-commit secrets, one for sensitive file on Read) and 1 Read matcher.

**Verify:**
```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid JSON')"
grep 'hook-dangerous-cmd.sh' .claude/settings.json
grep 'hook-sensitive-file.sh' .claude/settings.json
grep 'hook-pre-commit-secrets.sh' .claude/settings.json
grep -c 'HOME/.claude/scripts' .claude/settings.json  # 0 (old path removed)
grep -c 'mvn test\|npm test\|pytest\|go test\|cargo test' .claude/settings.json  # 0 (test runner removed)
```

**Done when:** settings.json calls extracted scripts, old inline hooks gone, PostToolUse path fixed, test runner removed.

### Task 3: Update review.md to reference script instead of inline bash
**Files:** `.claude/commands/review.md`
**Action:**
Replace the inline secret scanning bash block in review.md (the ~80-line Security Scanning section) with a call to the extracted script:
```bash
echo "🔒 Running secret scanner..."
bash .cnogo/hooks/hook-pre-commit-secrets.sh
```
Keep the dependency vulnerability scanning and SAST sections as-is (those are different tools).
This eliminates the 3rd copy of the secret patterns (finding #6).

**Verify:**
```bash
grep 'hook-pre-commit-secrets.sh' .claude/commands/review.md
grep -c 'AKIA' .claude/commands/review.md  # 0 (inline patterns removed)
```

**Done when:** review.md delegates to the script, no inline secret patterns remain.

## Verification

After all tasks:
```bash
# All hook scripts exist and are valid
bash -n .cnogo/hooks/hook-dangerous-cmd.sh && bash -n .cnogo/hooks/hook-sensitive-file.sh && bash -n .cnogo/hooks/hook-pre-commit-secrets.sh
# settings.json valid
python3 -c "import json; json.load(open('.claude/settings.json')); print('OK')"
# No old patterns
grep -c 'HOME/.claude/scripts' .claude/settings.json  # 0
# Workflow validation
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
fix(review-findings-remediation): extract hooks to scripts, fix critical path

- Extract 3 inline PreToolUse hooks to scripts/hook-*.sh
- Fix shell injection via printf instead of echo
- Fix PostToolUse hook path (project-relative)
- Remove pre-commit test runner (10-120s per commit)
- Deduplicate secret scanning (single source in script)
- Expand secret patterns (Stripe, Twilio, SendGrid, Firebase, DB URIs)
- Combine per-file grep calls into single alternation pattern
```

---
*Planned: 2026-02-10*
