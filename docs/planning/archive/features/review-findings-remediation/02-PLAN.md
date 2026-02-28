# Plan 02: Installer Fixes & Security Hardening

## Goal
Fix install.sh to copy scripts/ and skip existing settings.json, harden permission deny rules, and restrict review agent tools.

## Prerequisites
- [ ] Plan 01 complete (hook scripts must exist for install.sh to copy)

## Tasks

### Task 1: Fix install.sh
**Files:** `install.sh`
**Action:**
1. **Add scripts/ copy section** after the `.claude/commands` section (finding #1):
   - `mkdir -p "$TARGET_DIR/scripts"`
   - Copy all `scripts/*.py` and `scripts/hook-*.sh` files
   - Make hook scripts executable: `chmod +x "$TARGET_DIR/scripts/hook-"*.sh`
   - Print each script installed

2. **Skip settings.json if exists** (finding #4):
   - Change line 77 from unconditional `cp` to:
     ```bash
     if [ ! -f "$TARGET_DIR/.claude/settings.json" ]; then
         cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/"
         echo "   ├── settings.json (hooks + permissions)"
     else
         echo -e "   ├── settings.json ${YELLOW}(skipped - exists)${NC}"
     fi
     ```

3. **Quote all `$(basename ...)` calls** (finding #20):
   - `$(basename "$cmd")` on line 83
   - `$(basename "$agent")` on line 91

**Verify:**
```bash
bash -n install.sh
grep 'scripts/' install.sh | head -5
grep '! -f.*settings.json' install.sh
grep 'basename "$cmd"' install.sh
grep 'basename "$agent"' install.sh
```

**Done when:** install.sh copies scripts/, skips settings.json if exists, all basenames quoted.

### Task 2: Harden permission deny rules
**Files:** `.claude/settings.json`
**Action:**
Add deny rules for (findings #8, #9, #14, #17):

1. **rm patterns** (finding #8):
   - `Bash(rm -rf .:*)`
   - `Bash(rm -rf ..:*)`
   - `Bash(rm -rf .git:*)`

2. **Sensitive file Bash access** (finding #9):
   - `Bash(cat .env:*)`, `Bash(cat .env.*:*)`
   - `Bash(head .env:*)`, `Bash(tail .env:*)`
   - `Bash(cat *credentials*:*)`, `Bash(cat *.pem:*)`, `Bash(cat *.key:*)`

3. **git force push** (finding #17):
   - `Bash(git push --force:*)`, `Bash(git push -f:*)`
   - `Bash(git push origin --delete:*)`

4. **Infrastructure destruction** (finding #17):
   - `Bash(docker run --privileged:*)`
   - `Bash(terraform destroy:*)`, `Bash(terraform apply -auto-approve:*)`
   - `Bash(kubectl delete namespace:*)`

5. **curl/wget exfiltration** (finding #14):
   - `Bash(curl -X POST -d:*)`, `Bash(curl --data:*)`
   - `Bash(wget --post-file:*)`

**Verify:**
```bash
python3 -c "import json; json.load(open('.claude/settings.json')); print('valid JSON')"
grep -c 'rm -rf \.' .claude/settings.json  # ≥3
grep 'cat .env' .claude/settings.json
grep 'git push --force' .claude/settings.json
grep 'terraform destroy' .claude/settings.json
```

**Done when:** All new deny rules present in settings.json.

### Task 3: Remove Bash from review agents
**Files:** `.claude/agents/code-reviewer.md`, `.claude/agents/security-scanner.md`, `.claude/agents/perf-analyzer.md`, `.claude/agents/api-reviewer.md`
**Action:**
Change `tools:` line in all 4 review/analysis agents from `Read, Grep, Glob, Bash` to `Read, Grep, Glob` (finding #10).

These are read-only analysis agents that don't need shell access. Removing Bash reduces attack surface without affecting their review capability.

**Verify:**
```bash
grep 'tools:' .claude/agents/code-reviewer.md .claude/agents/security-scanner.md .claude/agents/perf-analyzer.md .claude/agents/api-reviewer.md
# All should show "Read, Grep, Glob" without Bash
grep -c 'Bash' .claude/agents/code-reviewer.md  # 0
```

**Done when:** All 4 review agents have tools: Read, Grep, Glob (no Bash).

## Verification

After all tasks:
```bash
bash -n install.sh
python3 -c "import json; json.load(open('.claude/settings.json')); print('OK')"
grep -c 'Bash' .claude/agents/code-reviewer.md .claude/agents/security-scanner.md .claude/agents/perf-analyzer.md .claude/agents/api-reviewer.md  # all 0
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
fix(review-findings-remediation): installer fixes, security hardening, agent restrictions

- Fix install.sh: copy scripts/, skip settings.json if exists, quote basenames
- Add deny rules for rm -rf ., force push, docker privileged, terraform destroy
- Block Bash access to sensitive files (cat .env, head .pem, etc.)
- Block curl/wget data exfiltration patterns
- Remove Bash tool from 4 review-only agents
```

---
*Planned: 2026-02-10*
