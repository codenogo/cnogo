# Install & Template Sync — Implementation Context

## Problem

After the `agent-architecture-redesign` feature (3 commits: `5c3ef1c`, `95349c9`, `dd6dd48`), several files are out of sync with the new architecture:

1. **Root CLAUDE.md** serves dual duty — cnogo dev docs AND installable template. Contains cnogo-specific content that's wrong for target projects.
2. **install.sh** tries to copy deleted `docs/skills.md`, doesn't install `.claude/skills/`, claims "10 agent definitions" (now 2).
3. **Stack templates** (`docs/templates/CLAUDE-*.md`) lack workflow docs (memory engine, Karpathy principles). When `/init` copies a stack template over CLAUDE.md, workflow docs are lost.
4. **Existing projects** that already have a CLAUDE.md get no workflow documentation at all — install.sh skips their CLAUDE.md and `/init` would overwrite it.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| CLAUDE.md ownership | Three-file model | Root = cnogo dev only; `docs/templates/CLAUDE-generic.md` = template for new projects; `.claude/CLAUDE.md` = workflow docs for all targets |
| Workflow delivery | `.claude/CLAUDE.md` always installed | Claude Code auto-loads both root and `.claude/CLAUDE.md`. Workflow docs (memory engine, principles, planning refs) go in `.claude/CLAUDE.md` which is cnogo's domain — safe to always write/overwrite |
| Existing project CLAUDE.md | Never touch root CLAUDE.md | `.claude/CLAUDE.md` handles workflow docs; root file is the project's own |
| `.claude/CLAUDE.md` on upgrade | Always overwrite | It's cnogo's file, not the user's. Safe to update on reinstall |
| Skills installation | Install all 8 `.claude/skills/*.md` | Stack-agnostic playbooks useful in any project. Commands lazy-load them |
| `/init` safety | Ask before replacing root CLAUDE.md | If CLAUDE.md differs from generic template, prompt user before overwriting with stack template |
| Stack templates cleanup | Remove Planning Docs section | All workflow references live in `.claude/CLAUDE.md` — single source of truth |
| install.sh stale refs | Remove `docs/skills.md` block, fix agent count | `docs/skills.md` was deleted in agent-architecture-redesign Plan 02. Only 2 agents remain |
| Unknown stack fallback | Use `docs/templates/CLAUDE-generic.md` | init.md line 150 currently falls back to root CLAUDE.md (cnogo-specific content) |

## File Model After Fix

```
In cnogo repo:
  CLAUDE.md                          # cnogo dev docs (never leaves this repo via install.sh)
  .claude/CLAUDE.md                  # Workflow docs (installed to ALL targets, always overwritable)
  docs/templates/CLAUDE-generic.md   # Generic template for target root CLAUDE.md (NEW)
  docs/templates/CLAUDE-python.md    # Stack template (Planning Docs section removed)
  docs/templates/CLAUDE-*.md         # Other stack templates (Planning Docs section removed)

In target project after install:
  CLAUDE.md                          # From CLAUDE-generic.md (skip-if-exists) or user's own
  .claude/CLAUDE.md                  # From cnogo's .claude/CLAUDE.md (always overwritten)
  .claude/skills/*.md                # All 8 skill files (always overwritten)
  .claude/commands/*.md              # All commands (always overwritten)
  .claude/agents/*.md                # 2 agents: implementer, debugger (always overwritten)
```

## `.claude/CLAUDE.md` Content (Workflow Docs)

Sections to include (extracted from current root CLAUDE.md):
- Memory Engine (CLI + Python API)
- Planning Docs (directory references)
- Karpathy Operating Principles
- Skills Library reference (`.claude/skills/`)
- Security (pre-commit hooks, secret scanning)

## Root CLAUDE.md Content (cnogo Dev Only)

Sections to keep:
- Project Overview (cnogo description)
- Quick Reference (cnogo scripts)
- Code Organisation (cnogo file structure)
- Conventions (naming, code style, git)
- Key Files (bridge.py, WORKFLOW.json, etc.)

## Constraints

- Python stdlib only (no external deps)
- install.sh must remain idempotent
- Backward compatible — existing target projects must not break
- `.claude/CLAUDE.md` content must work for any stack (stack-agnostic)

## Related Code

- `CLAUDE.md` — root, currently dual-purpose
- `install.sh:222-227` — CLAUDE.md copy (needs source change)
- `install.sh:236-247` — stale `docs/skills.md` copy (needs removal)
- `install.sh:274` — "10 agent definitions" (needs fix → 2)
- `.claude/commands/init.md:126-161` — stack template copy (needs safety check)
- `.claude/commands/init.md:149-150` — unknown stack fallback (needs fix)
- `docs/templates/CLAUDE-python.md:139-148` — Planning Docs section (remove)
- `docs/templates/CLAUDE-java.md` — Planning Docs section (remove)
- `docs/templates/CLAUDE-typescript.md` — Planning Docs section (remove)
- `docs/templates/CLAUDE-go.md` — Planning Docs section (remove)
- `docs/templates/CLAUDE-rust.md` — Planning Docs section (remove)
- `.claude/skills/*.md` — 8 files (need install loop in install.sh)

---
*Discussed: 2026-02-14*
