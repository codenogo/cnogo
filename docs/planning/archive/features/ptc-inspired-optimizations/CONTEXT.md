# Context: PTC-Inspired Optimizations

**Date:** 2026-02-22 | **Status:** Research complete, no code changes planned

## Background

Research into Anthropic's Programmatic Tool Calling (PTC) feature — GA Feb 2026 — identified four potential improvements for cnogo. After examining the codebase, two were downgraded and two remain future candidates.

## Decisions

### Skill lazy-loading — Deprioritized

Initial hypothesis: skills are bulk-loaded, wasting tokens. Reality: `/spawn` already has explicit specialization->skill mappings (16 entries) and `/review` loads skills in a defined sequence. No change needed.

### TaskDescV2 examples — Future candidate (low effort)

PTC research showed `input_examples` improved tool accuracy from 72% to 90%. The same principle could apply to `bridge.py`'s `generate_implement_prompt()`: adding 2-3 exemplar task descriptions could reduce agent misfires. Worth doing when evidence of misfires accumulates.

### Batched verification — Marginal

Compound verify scripts would reduce Bash tool call round-trips, but Claude Code agents execute Bash calls sequentially anyway. The savings are architectural rather than practical.

### Headless mode — Deferred (high effort)

A stdlib `urllib.request` wrapper against the Claude Messages API would enable plan execution without Claude Code (CI, cron, scripts). Strategic but conflicts with the stdlib-only constraint if the anthropic SDK is desired. Needs its own research artifact if pursued.

## Open Questions

- Will Claude Code Agent Teams leverage PTC internally?
- When will MCP tools become PTC-callable?
- Are agent misfires on TaskDescV2 prompts frequent enough to justify examples?
- Should headless mode be a separate feature or part of a larger API integration story?

## Related

- Research: `docs/planning/work/research/programmatic-tool-calling/`
- Bridge: `scripts/memory/bridge.py`
- Skills mapping: `.claude/commands/spawn.md`
