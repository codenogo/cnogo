# Roadmap

High-level phases and progress tracking.

## Current Milestone: v1.1 — Extended Commands + Memory Engine

### Phase 1: Foundation (v1.0)
**Status:** ✅ Complete

Initial release with 15 core slash commands covering the full development lifecycle.

- [x] 15 slash commands (discuss, plan, implement, verify, review, ship, quick, tdd, status, pause, resume, sync, context, debug, changelog, release)
- [x] Parallel session coordination (Boris Cherny style)
- [x] Secret scanning in pre-commit hooks
- [x] Stack auto-detection (Java, TypeScript, Python, Go, Rust)
- [x] Enterprise templates (ADR, CODEOWNERS, PR template)

### Phase 2: Extended Commands (v1.1)
**Status:** ✅ Complete

Expanded to 28 commands with workflow contracts, memory engine, and Agent Teams.

- [x] 13 new commands (bug, brainstorm, close, research, validate, verify-ci, rollback, init, mcp, background, spawn, team, quick)
- [x] Machine-checkable workflow contracts (JSON + MD pairs)
- [x] `workflow_validate.py` validator with optional pre-commit enforcement
- [x] Stack-specific CLAUDE.md templates
- [x] Enhanced secret scanning (8 patterns)
- [x] PreToolUse security hooks

### Phase 3: Memory + Agent Architecture (v1.1)
**Status:** ✅ Complete

SQLite-backed memory engine and agent architecture redesign for reliable multi-agent workflows.

- [x] SQLite memory engine (CRUD, dependency graph, JSONL sync)
- [x] Agent Teams with bridge module for plan-to-task translation
- [x] Three-file CLAUDE.md model (root project, .claude/ workflow, generic template)
- [x] Skills library (8 domain playbooks)
- [x] Template self-separation (docs/templates/ for installs, docs/planning/ for own docs)

---

## Completed Features

| Feature | Description |
|---------|-------------|
| `team-implement-integration` | Bridge module, implementer agent, team/implement wiring |
| `agent-architecture-redesign` | Ultra-lean agents, skills migration, CLAUDE.md restructure |
| `install-template-sync` | Sync install.sh with redesigned architecture |
| `kill-state-md` | Remove STATE.md, memory engine as single source of truth |
| `template-self-separation` | Separate install templates from cnogo's own docs |

---

## Future Milestones

### v2.0 — Test Infrastructure + CI
- [ ] Test suite for memory engine and workflow scripts
- [ ] pyproject.toml for optional dev tooling (pytest, ruff)
- [ ] CI integration via GitHub Actions
- [ ] MCP tool integrations (Jira, Sentry, Figma)

### v2.1 — Advanced Features
- [ ] Cross-session memory persistence and context sharing
- [ ] Plugin system for custom command extensions
- [ ] Dashboard/reporting for workflow metrics

---

## Parking Lot

Ideas captured but not scheduled:

- [ ] Test infrastructure (pytest, coverage)
- [ ] pyproject.toml for dev tooling
- [ ] CI pipeline (GitHub Actions)
- [ ] MCP integration templates
- [ ] SBOM generation automation
- [ ] Workflow visualization

---
*Last updated: 2026-02-14*
