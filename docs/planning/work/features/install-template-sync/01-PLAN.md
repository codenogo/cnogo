# Plan 01: Create Template Files + Split CLAUDE.md

## Goal
Create the three-file CLAUDE.md model: root stays cnogo-dev, new generic template for targets, new `.claude/CLAUDE.md` for workflow docs.

## Prerequisites
- [x] CONTEXT.md complete with all 9 decisions

## Tasks

### Task 1: Create `docs/templates/CLAUDE-generic.md`
**Files:** `docs/templates/CLAUDE-generic.md`
**Action:**
Create a new generic template for target projects that don't match a specific stack. Structure it like the existing stack templates (CLAUDE-python.md, CLAUDE-java.md, etc.) but stack-agnostic:

- `# CLAUDE.md` heading (no stack suffix)
- `## Project Overview` — placeholder: `[One paragraph: what this project is, who it's for, what it does]`
- `## Quick Reference` — placeholder code block with `# Build`, `# Test`, `# Run locally`, `# Lint` comments
- `## Code Organisation` — placeholder tree
- `## Conventions` — generic naming/style/git sections with placeholders
- `## Architecture Rules` — Do/Don't with placeholders
- `## Key Files` — empty table
- `## Testing Requirements` — placeholders
- `## Security` — generic security reminders (never commit secrets, validate inputs)
- `## Dependencies` — generic dep evaluation checklist

Do NOT include a Planning Docs section (per CONTEXT.md decision — that moves to `.claude/CLAUDE.md`).

**Verify:**
```bash
test -f docs/templates/CLAUDE-generic.md && echo "OK" || echo "FAIL"
grep -q "Project Overview" docs/templates/CLAUDE-generic.md && echo "has overview" || echo "FAIL"
grep -qv "Planning Docs" docs/templates/CLAUDE-generic.md && echo "no planning docs section" || echo "FAIL"
```

**Done when:** `docs/templates/CLAUDE-generic.md` exists with placeholder sections, no Planning Docs section.

### Task 2: Create `.claude/CLAUDE.md` (Workflow Docs)
**Files:** `.claude/CLAUDE.md`
**Action:**
Create the workflow documentation file that gets installed to ALL target projects. Extract these sections from the current root CLAUDE.md and make them stack-agnostic:

```markdown
# cnogo Workflow

Workflow engine documentation. Claude reads this automatically alongside your project's CLAUDE.md.

## Operating Principles

[Karpathy principles — copy from root CLAUDE.md lines 39-46]

## Memory Engine

[Memory engine section — copy from root CLAUDE.md lines 57-71, but make paths generic]

## Planning Docs

- Current state: `docs/planning/STATE.md`
- Project vision: `docs/planning/PROJECT.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`
- Research: `docs/planning/work/research/`

## Skills Library

Reusable domain expertise, lazy-loaded by commands:
- `.claude/skills/` — code review, security scanning, performance analysis, API review, test writing, debug investigation, refactor safety, release readiness

## Security

- Never commit: secrets, keys, credentials, `.env` files
- Pre-commit hooks scan for secrets and dangerous commands
- Always validate user input at system boundaries
```

**Verify:**
```bash
test -f .claude/CLAUDE.md && echo "OK" || echo "FAIL"
grep -q "Operating Principles" .claude/CLAUDE.md && echo "has principles" || echo "FAIL"
grep -q "Memory Engine" .claude/CLAUDE.md && echo "has memory" || echo "FAIL"
grep -q "Planning Docs" .claude/CLAUDE.md && echo "has planning" || echo "FAIL"
grep -q "Skills Library" .claude/CLAUDE.md && echo "has skills" || echo "FAIL"
```

**Done when:** `.claude/CLAUDE.md` exists with all 5 workflow sections.

### Task 3: Trim Root `CLAUDE.md` to cnogo-dev Only
**Files:** `CLAUDE.md`
**Action:**
Remove workflow sections from root CLAUDE.md that now live in `.claude/CLAUDE.md`. Keep only cnogo-specific development content:

**Keep:**
- Project Overview (cnogo description)
- Quick Reference (cnogo scripts)
- Code Organisation (cnogo file structure)
- Conventions (naming, code style, git)
- Key Files (bridge.py, WORKFLOW.json, etc.)

**Remove (now in `.claude/CLAUDE.md`):**
- Operating Principles section (lines 39-46)
- Memory Engine section (lines 57-71)
- Planning Docs section (lines 73-79)
- Security section (lines 81-86)

**Verify:**
```bash
grep -q "cnogo" CLAUDE.md && echo "has cnogo content" || echo "FAIL"
grep -q "Key Files" CLAUDE.md && echo "has key files" || echo "FAIL"
grep -qv "Operating Principles" CLAUDE.md && echo "no principles (moved)" || echo "FAIL"
grep -qv "Memory Engine" CLAUDE.md && echo "no memory engine (moved)" || echo "FAIL"
grep -qv "Planning Docs" CLAUDE.md && echo "no planning docs (moved)" || echo "FAIL"
```

**Done when:** Root CLAUDE.md has only cnogo-dev sections. Workflow sections live in `.claude/CLAUDE.md`.

## Verification

After all tasks:
```bash
test -f docs/templates/CLAUDE-generic.md && echo "generic template: OK"
test -f .claude/CLAUDE.md && echo "workflow docs: OK"
grep -q "cnogo" CLAUDE.md && echo "root is cnogo-dev: OK"
grep -c "Memory Engine" .claude/CLAUDE.md | grep -q 1 && echo "memory in workflow: OK"
grep -qv "Memory Engine" CLAUDE.md && echo "memory NOT in root: OK"
```

## Commit Message
```
feat(install-template-sync): create three-file CLAUDE.md model

- Create docs/templates/CLAUDE-generic.md for target projects
- Create .claude/CLAUDE.md with workflow docs (principles, memory, planning, skills, security)
- Trim root CLAUDE.md to cnogo-dev content only
```

---
*Planned: 2026-02-14*
