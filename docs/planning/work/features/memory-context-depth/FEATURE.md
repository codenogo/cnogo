# Feature: Memory Context Depth

**Slug**: memory-context-depth
**Parent Shape**: control-plane-consolidation
**Priority**: P0

## User Outcome

prime() produces rich, feature-aware context summaries with work order status, lane health, grouped observations, and contradictions.

## Scope

1. Add `--feature` flag to prime CLI
2. Render work order status + lane health + automation state in prime output
3. Group observations by kind (decision, blocker, review_finding, etc.)
4. Show observation source references
