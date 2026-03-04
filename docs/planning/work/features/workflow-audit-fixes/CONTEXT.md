# Workflow Audit Fixes

## Problem

Deep audit of the workflow system revealed 26 confirmed issues across slash commands, skills, scripts, configuration, and documentation. Issues range from runtime bugs to consistency gaps.

## Phasing

### Phase 1: Critical Runtime Fixes (Plan 01)
1. **Venv path inconsistency** — `workflow_memory.py` lines 73-74 use `.venv`, but lines 929-930 and `workflow_hooks.py` use `.cnogo/.venv`. Normalize to `.cnogo/.venv`.
2. **Quick SUMMARY.json validation gap** — `workflow_validate_core.py` only checks existence, not content. Add contract validation matching PLAN.json behavior.
3. **team.md epic_id derivation** — Step 12 references `<epic_id>` with no clear derivation path. Add explicit instruction to capture from memory create output.

### Phase 2: Standards Alignment (Plan 02)
1. **Unify severity scales** — Normalize to Critical/Warning/Info across security-scan.md, code-review.md, boundary-and-sdk-enforcement.md.
2. **Root CLAUDE.md missing principles** — Add "TDD Is Core" and "Verification Before Completion" to root CLAUDE.md.
3. **Consolidate perf skills** — Merge perf-analysis.md checklist into performance-review.md; remove perf-analysis.md.

### Phase 3: Command Consistency (Plan 03)
1. **Standardize step headings** — Convert all commands to `### Step N:` format (ship.md, performance-review.md, tdd.md).
2. **Add missing steps** — tdd.md needs validate step; ship.md needs Step format.
3. **Branch cleanup + implementer fix** — Add merged-branch cleanup to plan/implement/ship commands; fix `git add -A` in implementer agent.

### Phase 4: Documentation & Low-Priority (Plan 04)
- ROADMAP.md graph subsystem coverage
- WORKFLOW.json graph config section
- Missing renderers for CONTEXT/REVIEW/RESEARCH
- Dead code cleanup (unreachable ls-optimized branch)
- Secret redaction pattern expansion
- Missing commands (/stash, /archive, /hooks)
- cnogo-scripts package missing typecheck/test commands

## Dropped Finding

- **Bare except in validation** (original HIGH #2) — NOT CONFIRMED. All exceptions in `workflow_validate_core.py` are properly caught and reported.

## Scope

- 21 files across 4 phases
- Each phase is independently shippable
- Phase 1 has runtime impact; phases 2-4 are quality/consistency
