# Opus 4.6 Agents Workflow Improvements - Implementation Context

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Scope | All 3 phases in one feature branch | User wants comprehensive upgrade: agent defs, memory, Agent Teams, effort hints |
| /spawn fate | Keep both /spawn and .claude/agents/ | /spawn stays as convenience wrapper delegating to agent definitions; direct invocation also works |
| Agent memory | All agents except docs-writer get persistent memory | Maximize institutional knowledge; docs-writer regenerates from current state anyway |
| Memory VCS | Project scope, checked in | `memory: project` (.claude/agent-memory/) — team shares knowledge via version control |
| Agent Teams | Always enabled in settings.json | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` by default; users get it immediately |
| Model routing | Tiered by task weight | haiku: explorer, docs-writer. sonnet: code-reviewer, security-scanner, perf-analyzer, api-reviewer. inherit (opus): debugger, test-writer, refactorer, migrate |
| Effort hints | Comments in command .md files | `<!-- effort: high -->` metadata in each command file; informational, no enforcement |
| /sync migration | Dual mode | /sync detects Agent Teams active state; uses shared task list if yes, manual coordination if no |
| Agent count | 10 agents total | 7 original + api-reviewer + refactorer + migrate; matches all /spawn specializations plus explorer |

## Agent Definitions (10 total)

| Agent | Model | Tools | Memory | Preloaded Skills |
|-------|-------|-------|--------|-----------------|
| `explorer` | haiku | Read, Grep, Glob | none | (none — fast scanning) |
| `code-reviewer` | sonnet | Read, Grep, Glob, Bash | project | Security Review, Refactor Safety |
| `security-scanner` | sonnet | Read, Grep, Glob, Bash | project | Security Review, Auth/AuthZ Review |
| `test-writer` | inherit | Read, Edit, Write, Bash, Grep, Glob | project | Test Strategy, Integration Testing |
| `debugger` | inherit | Read, Edit, Bash, Grep, Glob | project | Debug Investigation, RCA |
| `docs-writer` | haiku | Read, Write, Grep, Glob | none | Docs Quality |
| `perf-analyzer` | sonnet | Read, Grep, Glob, Bash | project | Performance Profiling |
| `api-reviewer` | sonnet | Read, Grep, Glob, Bash | project | API Design |
| `refactorer` | inherit | Read, Edit, Write, Bash, Grep, Glob | project | Refactor Safety |
| `migrate` | inherit | Read, Edit, Write, Bash, Grep, Glob | project | Data & Migrations |

## Constraints

- stdlib-only Python (no external deps) — applies to any new scripts
- install.sh must remain a single portable installer
- Agent definitions must be stack-agnostic (no language-specific assumptions)
- Agent Teams env var always set, but /team command should document experimental status
- Must not break existing /spawn usage — agent defs complement, not replace
- WORKFLOW.json schema must remain backward-compatible (additive changes only)

## Open Questions

- [ ] How to handle agent memory file conflicts on multi-developer teams (git merge of .claude/agent-memory/)
- [ ] Should /team command create a new TEAM.md artifact in docs/planning/work/ for session tracking?
- [ ] Exact TeammateIdle and TaskCompleted hook implementations — need more usage data from Agent Teams preview
- [ ] Whether to add `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to settings.json for compaction tuning

## Related Code

- `.claude/commands/spawn.md` — Current /spawn implementation with inline agent prompts (to be updated)
- `.claude/commands/sync.md` — Current /sync for parallel session coordination (to get dual-mode)
- `.claude/commands/background.md` — Background task launcher (related to agent orchestration)
- `.claude/settings.json` — Hooks, permissions, env vars (needs Agent Teams env var)
- `install.sh` — Must be updated to install .claude/agents/ directory
- `docs/skills.md` — Skills library to preload into agents
- `docs/planning/WORKFLOW.json` — May need agentTeams config section

## Research

- `docs/planning/work/research/opus-46-agents-workflow-improvements/RESEARCH.md`

---
*Discussed: 2026-02-10*
