# Plan 03: Command Restructuring

## Goal
Trim team.md to ~120 lines (orchestration only), update implement.md to remove eager loading, and update spawn.md to use skills instead of deleted agents.

## Prerequisites
- [ ] Plan 02 complete (agents restructured, bridge updated)

## Tasks

### Task 1: Trim team.md to ~120 lines
**Files:** `.claude/commands/team.md`
**Action:**
Rewrite team.md keeping only orchestration logic. Remove:
- **Agent table** (lines 20-35) — the bridge module handles agent selection
- **Recommended Team Compositions section** (lines 39-65) — move to a one-liner: "See `.claude/skills/` for available domain expertise"
- **Keyboard Shortcuts section** (lines 74-83) — not command-specific, users discover these naturally
- **Examples section** (lines 270-291) — 20 lines of examples, trim to 3 lines max
- **Best Practices section** (lines 258-267) — trim to 2-3 key points inline
- **Notes section** (lines 294-300) — trim to 1-2 essential notes

Keep:
- Action table (create, implement, status, message, dismiss)
- Step 0: Verify Agent Teams Enabled
- Step 1: Parse Action
- Step 2: Execute Action (all 5 actions, but trimmed)
- Step 3: Report template

For the `implement` action specifically:
- Remove the inline Python code blocks for bridge and conflict detection — reference the functions but don't embed 20 lines of boilerplate
- Simplify to: "Call `plan_to_task_descriptions()`, check `detect_file_conflicts()`, create team, spawn implementers"

For the `create` action:
- Instead of referencing agent files, say: "Spawn `general-purpose` teammates with relevant `.claude/skills/` preloaded via the `skills` frontmatter"
- This is the key pattern change: review teams become general-purpose agents + skills, not specialized agent files

**Verify:**
```bash
wc -l .claude/commands/team.md
```
Expected: under 140 lines.

**Done when:** team.md is under 140 lines, references skills instead of agent files for non-implementer roles, and all 5 actions still work.

### Task 2: Update implement.md — remove eager loading
**Files:** `.claude/commands/implement.md`
**Action:**
1. **Remove the Principle Reminder section** (lines 18-24) that says "Apply Karpathy Principles from docs/skills.md". These are now inline in CLAUDE.md — no need to re-reference.
2. **Simplify Step 1** — keep reading PLAN.md and PLAN.json, but remove the instruction to read CONTEXT.md. The plan JSON is the contract; CONTEXT.md was for discussion, not execution.
3. **Remove skills.md references** throughout the file.
4. **Update Step 1c (Team Mode)** — reference should say "delegate to `/team implement`" without re-explaining what the bridge does (team.md handles that).
5. **Trim inline code blocks** — the memory claim/close commands don't need 6-line Python blocks; use 2-line versions:
   ```bash
   python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import claim; claim('<id>', actor='session', root=__import__('pathlib').Path('.'))"
   ```

Target: ~150 lines (from current 202).

**Verify:**
```bash
wc -l .claude/commands/implement.md
grep -c 'skills.md' .claude/commands/implement.md
```
Expected: under 160 lines, 0 references to skills.md.

**Done when:** implement.md is under 160 lines with no skills.md references and no CONTEXT.md read instruction.

### Task 3: Update spawn.md to use skills
**Files:** `.claude/commands/spawn.md`
**Action:**
Rewrite spawn.md to reflect the new architecture:
1. **Remove the agent definition table** (lines 12-21) that maps specializations to `.claude/agents/` files — those files no longer exist
2. **Replace with skills-based spawning**: each specialization loads a `.claude/skills/` file into a `general-purpose` subagent
3. **Simplify**: spawn.md should explain that `/spawn <specialization> <task>` creates a focused subagent with the relevant skill preloaded

New specialization table:
```
| Specialization | Skill Loaded | Best For |
|----------------|-------------|----------|
| security | .claude/skills/security-scan.md | Vulnerability audits |
| tests | .claude/skills/test-writing.md | Test generation |
| perf | .claude/skills/perf-analysis.md | Performance analysis |
| api | .claude/skills/api-review.md | API design review |
| review | .claude/skills/code-review.md | Code quality review |
| refactor | .claude/skills/refactor-safety.md | Safe refactoring |
```

Remove the inline fallback agent profiles entirely (lines 50+).

Target: ~80 lines (from current 274).

**Verify:**
```bash
wc -l .claude/commands/spawn.md
grep -c 'agents/' .claude/commands/spawn.md
```
Expected: under 100 lines, 0 references to `.claude/agents/` (except possibly implementer/debugger).

**Done when:** spawn.md references skills instead of agent files and is under 100 lines.

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
wc -l .claude/commands/team.md .claude/commands/implement.md .claude/commands/spawn.md
grep -r 'skills.md' .claude/commands/ | grep -v '.json'  # Should be 0
```

## Commit Message
```
refactor(agent-architecture): command restructuring — lean team.md, skills-based spawn

- Trim team.md to ~120 lines (orchestration only, no agent table)
- Update implement.md: remove eager CONTEXT.md/skills.md loading
- Rewrite spawn.md: skills-based specializations instead of agent files
```

---
*Planned: 2026-02-14*
