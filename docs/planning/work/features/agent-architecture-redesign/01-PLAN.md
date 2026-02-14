# Plan 01: Context Foundation

## Goal
Replace always-loaded placeholder content with real project instructions, dissolve skills.md into lazy-loaded `.claude/skills/` files, and add auto-compaction safety net.

## Prerequisites
- [x] CONTEXT.md with all decisions finalized
- [x] Research artifact completed

## Tasks

### Task 1: Rewrite CLAUDE.md with real project content
**Files:** `CLAUDE.md`
**Action:**
Replace the entire CLAUDE.md with real content for cnogo:
- **Project Overview**: cnogo is a universal development workflow pack for Claude Code providing 28+ slash commands, a SQLite-backed memory engine, and Agent Teams support for enterprise-grade SDLC workflows.
- **Quick Reference**: `python3 scripts/workflow_validate.py` (validate), `python3 scripts/workflow_memory.py stats` (memory stats), `python3 scripts/workflow_memory.py prime` (context summary)
- **Code Organisation**: `scripts/memory/` (Python package, stdlib only), `.claude/commands/` (slash commands), `.claude/agents/` (team teammates only — implementer + debugger), `.claude/skills/` (lazy-loaded domain expertise), `docs/planning/` (planning docs)
- **Conventions**: Python stdlib only, kebab-case slugs for features, `type(scope): description` commits
- **Karpathy Principles**: Inline the 4 principles as bullet points directly (NOT a reference to skills.md)
- **Memory Engine section**: Keep the existing CLI/Python reference (it's useful)
- **Planning Docs section**: Keep as-is
- Remove: Skills Library reference to `docs/skills.md`, all `[placeholder]` text, generic Common Tasks/Troubleshooting sections
- Target: ~100 lines of real, project-specific content

**Verify:**
```bash
python3 scripts/workflow_validate.py
```

**Done when:** CLAUDE.md has zero placeholder brackets `[...]` and is under 120 lines.

### Task 2: Create .claude/skills/ from docs/skills.md
**Files:** `.claude/skills/code-review.md`, `.claude/skills/security-scan.md`, `.claude/skills/perf-analysis.md`, `.claude/skills/api-review.md`, `.claude/skills/test-writing.md`, `.claude/skills/debug-investigation.md`, `.claude/skills/refactor-safety.md`, `.claude/skills/release-readiness.md`
**Action:**
Create the `.claude/skills/` directory and extract each domain skill from `docs/skills.md` into its own file. Each skill file should:
- Be a standalone markdown file (no YAML frontmatter — skills don't need it)
- Contain only the checklist/playbook for that domain
- Be concise: ~15-30 lines per file
- NOT include Memory Engine Integration boilerplate (that's the agent's job, not the skill's)

Mapping from docs/skills.md sections:
- "Security Review (OWASP)" + "Auth/AuthZ Review" → `security-scan.md`
- "Bug Triage" + "Debug Investigation" + "Root Cause Analysis (RCA)" → `debug-investigation.md`
- "API Design" → `api-review.md`
- "Test Strategy" + "Integration Testing" → `test-writing.md`
- "Performance Profiling" → `perf-analysis.md`
- "Refactor Safety" → `refactor-safety.md`
- "Release Readiness" + "Incident / Hotfix" → `release-readiness.md`
- "Docs Quality" → fold into `release-readiness.md` (too small for its own file)
- Code review patterns from `.claude/agents/code-reviewer.md` → `code-review.md`

Keep "Team Implementation" and "Memory Task Management" sections — these move to CLAUDE.md (they're always-relevant workflow patterns, not domain skills).

Do NOT delete `docs/skills.md` yet — that happens in Plan 02 when agents are restructured.

**Verify:**
```bash
ls .claude/skills/*.md | wc -l
```
Expected: 8 skill files.

**Done when:** 8 skill files exist in `.claude/skills/`, each under 30 lines, covering all domain expertise from docs/skills.md.

### Task 3: Add auto-compaction to settings.json
**Files:** `.claude/settings.json`
**Action:**
Add `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to the `env` section in `.claude/settings.json`:
```json
"env": {
  "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
  "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "60"
}
```
This triggers compaction at 60% context usage instead of the default 95%, giving subagents more headroom.

**Verify:**
```bash
python3 -c "import json; d=json.load(open('.claude/settings.json')); print(d['env']['CLAUDE_AUTOCOMPACT_PCT_OVERRIDE'])"
```
Expected output: `60`

**Done when:** settings.json has the new env var and parses as valid JSON.

## Verification

After all tasks:
```bash
python3 scripts/workflow_validate.py
grep -c '\[' CLAUDE.md  # Should be 0 placeholder brackets
ls .claude/skills/*.md | wc -l  # Should be 8
python3 -c "import json; json.load(open('.claude/settings.json'))"  # Valid JSON
```

## Commit Message
```
refactor(agent-architecture): context foundation — CLAUDE.md, skills, auto-compaction

- Rewrite CLAUDE.md with real project content, inline Karpathy principles
- Create .claude/skills/ with 8 domain skill files extracted from docs/skills.md
- Add CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60 to settings.json
```

---
*Planned: 2026-02-14*
