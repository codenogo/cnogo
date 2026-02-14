# Agent Architecture Redesign - Implementation Context

## Problem Statement

Subagents spawned by `/team implement` consistently hit "Context limit reached" because cnogo's commands were designed for interactive sessions (~200K budget) but subagents inherit compressed context windows. The `.claude/agents/` directory serves double duty (subagents + teammates) and commands eagerly load 5-8K tokens of overhead before any code is read.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Agent role | `.claude/agents/` = team teammates only | Subagents and teammates have different context requirements. Subagent work uses built-in types (Explore, general-purpose) or inline prompts. Keeps agent files focused on one execution model. |
| Context passing | ID-based retrieval via memory engine | Pass a memory ID in the task description; agent retrieves details at runtime via `memory.show()`. Minimal prompt payload. Aligns with Gas Town pattern (persistent state, ephemeral sessions). |
| Memory dependency | Required for team workflows | Memory engine must be initialized for `/team` workflows. `/init` ensures it. Simplifies agent code — no `if memory exists` branches. |
| Agent size | Ultra-lean: ~30-40 lines | Define the role, the claim→implement→verify→close cycle, and how to communicate. Everything else comes from the task description or memory retrieval. |
| Command structure | Single `/team` command, trimmed to ~120 lines | Strip out agent table, inline compositions, examples. Bridge module handles task generation — command just orchestrates. |
| Non-implementer agents | Convert to skills | code-reviewer, security-scanner, perf-analyzer, api-reviewer, test-writer, refactorer, docs-writer, migrate, explorer → become skills loadable via `skills` frontmatter. Domain expertise shouldn't require a full agent. |
| Retained agents | implementer + debugger only | These two need to act independently (claim tasks, modify files, communicate with lead). Everything else is a skill injected into agents as needed. |
| CLAUDE.md | Trim and fill with real content | Replace all placeholders. Move Karpathy principles into CLAUDE.md as 4 bullet points. |
| skills.md | Dissolve into CLAUDE.md and named skills | Delete `docs/skills.md` as a separate file. Karpathy principles become 4 lines in CLAUDE.md. Domain skills (review patterns, security checks) become `.claude/skills/` files for lazy loading. |

## Architecture (After Redesign)

```
.claude/
├── agents/                    # Team teammates ONLY (2 files)
│   ├── implementer.md         # ~30-40 lines: role + claim→close cycle
│   └── debugger.md            # ~30-40 lines: role + investigate→fix cycle
├── skills/                    # Domain expertise (lazy-loaded)
│   ├── code-review.md         # Review patterns, checklist
│   ├── security-scan.md       # Vulnerability patterns, OWASP checks
│   ├── perf-analysis.md       # Performance patterns, profiling
│   ├── api-review.md          # API design patterns, contract checks
│   ├── test-writing.md        # Test patterns, coverage guidance
│   └── ...                    # Other domain skills
├── commands/                  # Workflow commands
│   └── team.md                # Trimmed to ~120 lines (orchestration only)
└── settings.json              # CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60

CLAUDE.md                      # Filled in, includes Karpathy principles inline
docs/skills.md                 # DELETED — dissolved into CLAUDE.md + .claude/skills/
```

### Context Flow (Before vs After)

**Before (current):**
```
Teammate spawned → loads implementer.md (125 lines)
                 → loads CLAUDE.md (163 lines, placeholders)
                 → task description says "read CONTEXT.md, PLAN.json, skills.md"
                 → agent reads 3+ files (~3K tokens)
                 → agent calls memory.prime() (~1K tokens)
                 → THEN starts reading actual code
                 → Total overhead: 5-8K tokens before real work
```

**After (redesigned):**
```
Teammate spawned → loads implementer.md (~35 lines)
                 → loads CLAUDE.md (~100 lines, real content)
                 → task description: memory ID + action + files + verify
                 → agent calls memory.show(id) → gets focused task details
                 → starts reading actual code
                 → Total overhead: ~2K tokens before real work
```

## Constraints

- Python stdlib only (no external deps) — existing constraint
- Memory engine must be initialized before any `/team` workflow
- Agent files must stay under ~40 lines to keep system prompt within 2-5K token budget
- Skills are lazy-loaded — only injected when referenced in agent `skills` frontmatter
- Bridge module generates task descriptions with memory IDs (not full plan content)
- Backward compatibility: `/implement` without `--team` still works (serial, single-agent)

## Open Questions

- [ ] Should debugger agent use the same claim→close cycle as implementer, or a simpler investigate→report cycle?
- [ ] How to handle `/team create` for review/debug teams if code-reviewer and others are now skills? — Likely: spawn general-purpose agents with relevant skills preloaded
- [ ] Should we keep `/spawn` command or deprecate it in favor of skills?
- [ ] What's the migration path for existing agent files? Delete immediately or deprecate with warnings?
- [ ] Should `.claude/skills/` live in the repo (project-level) or in `~/.claude/skills/` (user-level)?

## Related Code

- `.claude/agents/implementer.md` — current 125-line agent (to be trimmed to ~35)
- `.claude/agents/code-reviewer.md` — becomes `.claude/skills/code-review.md`
- `.claude/commands/team.md` — 307 lines (to be trimmed to ~120)
- `scripts/memory/bridge.py` — generates task descriptions (needs to output memory IDs instead of full content)
- `scripts/memory/__init__.py` — public API, `show()` becomes the primary agent-facing function
- `docs/skills.md` — 287 lines (to be dissolved)
- `CLAUDE.md` — 163 lines of placeholders (to be filled and trimmed)

## Research

- `docs/planning/work/research/subagent-context-patterns/RESEARCH.md` — Full research on context management patterns from Anthropic, Gas Town, Superpowers, and community best practices

---
*Discussed: 2026-02-14*
