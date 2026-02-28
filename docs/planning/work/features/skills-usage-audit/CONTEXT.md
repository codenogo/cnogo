# Skills System Rework

## Problem

15 skill files exist in `.claude/skills/` and are referenced by 11 commands, but there's no validation, no discoverability, and no metadata. Skills are convention-based documentation with no tooling support. Additionally, `code-review.md` and `REVIEW.md` generation now have duplicated checklist content after the review-workflow-redesign. There is also no unified final-gate review skill — existing skills (code-review, security-scan, perf-analysis, release-readiness) cover individual concerns but are invoked ad-hoc without a deterministic sequence or scoring rubric.

## Decisions

### Auto-Discovery via Frontmatter

Each skill file gets a YAML frontmatter header:

```markdown
---
name: code-review
tags: [domain, quality]
appliesTo: [review, spawn]
---
# Code Review
...
```

- **name** (required): machine-readable identifier
- **tags** (optional): categorization (domain, workflow, quality, etc.)
- **appliesTo** (optional): which commands use this skill

No WORKFLOW.json config needed. The validator scans `.claude/skills/` and parses frontmatter.

### Frontmatter Parser in workflow_utils.py

Stdlib-only parser (regex-based, no pyyaml). Returns structured dict with name, tags, appliesTo. Handles missing/malformed frontmatter gracefully.

### Validator Checks (WARN severity)

1. All `.claude/skills/*.md` files have valid frontmatter
2. All skill path references in `.claude/commands/*.md` resolve to existing files
3. Severity: WARN (non-blocking), consistent with other validator findings

### Skills Are Authoritative (Dedup)

`code-review.md` owns the Security/Performance/Design Patterns checklists. `REVIEW.md` generation in `workflow_checks_core.py` should reference skill definitions instead of hardcoding duplicate content.

### Schema Cleanup

Update `WORKFLOW.schema.json`: replace `karpathyChecklist` with `operatingPrinciples`, remove `reviewPrinciples`. (Follow-up from review-workflow-redesign.)

### Performance Review (Final Gate) Skill

A new **composite orchestrator skill** (`performance-review.md`) that sequences existing sub-skills into a deterministic 6-step final-gate review:

| Step | Name | Source Skill | New? |
|------|------|-------------|------|
| A | Scope + Intent | — | Lightweight (reads plan goal + diff summary) |
| B | Code Review Checklist | `code-review.md` | Subsumes all 5 sections |
| C | Contract Compliance | — | **New**: multi-agent safety checks |
| D | Security / OWASP Quick Pass | `security-scan.md` | Subsumes OWASP + Auth/AuthZ |
| E | PRR-lite | `release-readiness.md` | Subsumes release checklist |
| F | Validation Baseline Diff | — | **New**: verify-before vs verify-after |

**Skill hierarchy**: Sub-skills remain standalone for ad-hoc use (e.g., `/spawn` security agent uses `security-scan.md` directly). Performance Review references but never duplicates their content.

### Scoring Rubric

7-axis deterministic scoring (0-2 each):

| Axis | 0 = Blocker | 1 = Concern | 2 = Clear |
|------|-------------|-------------|-----------|
| Correctness | Logic error, broken contract | Edge case gap | Verified correct |
| Security | OWASP violation, secret leak | Missing validation | No issues |
| Contract Compliance | Worker closes plan/epic | Missing artifact field | Full compliance |
| Performance | O(n²) on hot path, unbounded | Missing pagination | Profiled clean |
| Maintainability | God function, no separation | Weak naming | Clean, readable |
| Test Coverage | No tests for changed behavior | Happy-path only | Edge cases covered |
| Scope Discipline | Drive-by refactor, feature creep | Minor tangent | Surgical |

**Pass rule**: Total ≥ 11/14, with no 0 (blocker) in Correctness, Security, or Contract Compliance.

Maps to REVIEW.json verdict: `0 in hard-blocker axis → fail`, `total < 11 → warn`, `else → pass`.

### Multi-Agent Contract Compliance (Step C)

- Workers/hooks NEVER close PLAN/EPIC/shared issues
- `SubagentStop` only marks `DONE_BY_WORKER`
- Closure is leader-only via reconciliation
- No `auto-close-parent` semantics
- Role enforcement: check that workers don't exceed their authority boundary

### Review Integration

Performance Review scoring integrates with existing REVIEW.json schema v3:
- Rubric scores populate `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]`
- Scoring rubric recorded in `principleNotes[]` for auditability
- Token-minimal inputs: pointers (`diff_ref`, `run_ledger` paths, validation dirs) — no full-file re-reads

## Constraints

- Stdlib-only Python
- Existing skill files must work without frontmatter during migration (WARN for missing)
- Frontmatter is metadata for tooling only — doesn't change how Claude reads skill content
- Performance Review inputs must be token-efficient (pointers, not full contents)
- Sub-skills remain standalone — orchestrator references, never duplicates
- Workers/hooks NEVER close PLAN/EPIC/shared issues — only `report-done`

## Open Questions

1. Should `/spawn` specialization mapping become frontmatter-driven?
2. Should there be a `/skills` command for runtime discovery?

## Related Code

- `.claude/skills/` (15 files + 1 new `performance-review.md`)
- `.claude/skills/code-review.md` → Performance Review Step B
- `.claude/skills/security-scan.md` → Performance Review Step D
- `.claude/skills/perf-analysis.md` → Performance Review Step B (performance axis)
- `.claude/skills/release-readiness.md` → Performance Review Step E
- `.cnogo/scripts/workflow_utils.py` (new frontmatter parser)
- `.cnogo/scripts/workflow_validate_core.py` (new validation rules)
- `.cnogo/scripts/workflow_checks_core.py` (REVIEW.md dedup + scoring integration)
- `.claude/commands/review.md` (Performance Review as final gate)
- `.claude/commands/` (11 commands reference skills)
- `docs/planning/WORKFLOW.schema.json` (schema cleanup)
