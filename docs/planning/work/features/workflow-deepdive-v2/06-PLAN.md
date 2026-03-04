# Plan 06: Polish documentation: DRY rationalization in commands, fix skill/agent docs, and clean up command formatting

## Goal
Polish documentation: DRY rationalization in commands, fix skill/agent docs, and clean up command formatting

## Tasks

### Task 1: DRY rationalization in command files
**Files:** `.claude/commands/discuss.md`, `.claude/commands/plan.md`, `.claude/commands/implement.md`, `.claude/commands/review.md`, `.claude/commands/ship.md`, `.claude/commands/quick.md`
**Action:**
Audit all 6 command files for DRY violations. Standardize: (1) branch verification wording (same phrasing for the git commands), (2) phase check blocks (same format), (3) memory sync/validate steps (same final sections). Trim verbose code examples to compact form. Each command must remain self-contained (no cross-references to other commands).

**Micro-steps:**
- Identify repeated boilerplate across commands (branch verify, phase check, memory sync, validate)
- Standardize wording for shared patterns without losing self-containment
- Remove verbose examples where compact form suffices
- Verify all commands stay within token budget

**TDD:**
- required: `false`
- reason: Documentation cleanup validated by workflow_validate token budgets

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Fix skill and agent documentation accuracy
**Files:** `.claude/skills/code-review.md`, `.claude/skills/security-scan.md`, `.claude/skills/release-readiness.md`, `.claude/agents/implementer.md`
**Action:**
Review and fix: (1) code-review.md, security-scan.md, release-readiness.md for stale file path references and outdated patterns, (2) implementer.md for alignment with TaskDesc V2 protocol (structured fields, micro_steps, tdd contract, completion_footer). Fix any paths that reference deleted or renamed files.

**Micro-steps:**
- Review skills for stale references or broken file paths
- Ensure implementer.md reflects TaskDesc V2 bridge protocol
- Fix any inaccurate descriptions or outdated patterns

**TDD:**
- required: `false`
- reason: Documentation accuracy fixes validated by workflow_validate

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Clean up context, team, and spawn command formatting
**Files:** `.claude/commands/context.md`, `.claude/commands/team.md`, `.claude/commands/spawn.md`
**Action:**
Fix formatting and accuracy: (1) context.md — ensure consistent Step numbering and code examples, (2) team.md — verify action descriptions match current WORKFLOW.json config and bridge V2 protocol, (3) spawn.md — ensure it references current agent types (implementer, debugger, resolver) and doesn't reference removed skills.

**Micro-steps:**
- Fix context.md formatting to match other command patterns
- Update team.md for current agent teams protocol and worktree mode
- Update spawn.md for current implementation after perf-analysis removal

**TDD:**
- required: `false`
- reason: Documentation formatting and accuracy fixes

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
docs(polish): DRY rationalization, skill/agent doc fixes, command formatting cleanup
```
