# Multi-Agent Enhancements - Implementation Context

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Stale claims | Display claim age in `/status`, highlight at 10 min | No auto-release — variable task durations make fixed timeouts unreliable. User judges. |
| Stale threshold config | `agentTeams.staleIndicatorMinutes` in WORKFLOW.json | Project-level, easy to tune without code changes |
| Model selection | Keep in agent YAML frontmatter only | Already works for implementer (sonnet). Simple, no new config surface. |
| Debugger model | Change from `inherit` to `opus` | Opus is best for complex reasoning/root cause analysis. Worth the cost. |
| Parallelizable hints | Plan-level `"parallelizable": true/false` in NN-PLAN.json | Simple boolean for `/implement` auto-detection. Supplements existing blockedBy + file-conflict checks. |
| Version pinning | Document in PROJECT.md + CLAUDE.md | Lightweight — no runtime check in install.sh. Note required Claude Code version + env var. |
| Agent SDK | Deferred — out of scope | Wait until CI/CD automation features are needed (v2.0+) |

## Scope

4 implementation items from the Opus 4.6 multi-agent research recommendations:

1. **Heartbeat/claim age display** — Track and surface claim duration in `/status` output. Add `staleIndicatorMinutes` to WORKFLOW.json. Highlight tasks claimed longer than threshold.
2. **Model selection** — Set debugger agent to `model: opus`. Document model choices in agent YAML comments.
3. **Parallelizable hints** — Add optional `"parallelizable"` boolean to plan JSON schema. Update `/implement` detection logic to use it.
4. **Version pinning** — Document minimum Claude Code version and required env var in PROJECT.md and CLAUDE.md.

## Constraints

- Python stdlib only (no external dependencies)
- Memory schema changes must be backward-compatible (no migration needed for claim age — `updated_at` already exists)
- WORKFLOW.json schema change must not break `workflow_validate.py`
- Plan JSON schema change must be optional (backward-compatible with existing plans)

## Open Questions

- [ ] What minimum Claude Code version should we pin? (Need to identify when Agent Teams was introduced)

## Related Code

- `.cnogo/scripts/memory/storage.py` — `claim()` already sets `updated_at`; `_row_to_issue()` returns timestamps
- `.cnogo/scripts/memory/__init__.py` — public API for `claim()`, `list_issues()`, `show()`
- `.claude/agents/implementer.md` — currently `model: sonnet`
- `.claude/agents/debugger.md` — currently `model: inherit`, will change to `opus`
- `.claude/commands/implement.md` — Step 1c has the team-mode auto-detection logic
- `.claude/commands/status.md` — will surface claim age display
- `.cnogo/scripts/memory/bridge.py` — `plan_to_task_descriptions()` reads plan JSON
- `docs/planning/WORKFLOW.json` — will add `staleIndicatorMinutes`
- `.cnogo/scripts/workflow_validate.py` — must accept new WORKFLOW.json and plan JSON fields

## Research

- `docs/planning/work/research/opus-46-multi-agent/RESEARCH.md`

---
*Discussed: 2026-02-14*
