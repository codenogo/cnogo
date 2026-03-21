# Plan 02: Align standards: unify severity scales across skills, add missing principles to root CLAUDE.md, consolidate perf skills

## Goal
Align standards: unify severity scales across skills, add missing principles to root CLAUDE.md, consolidate perf skills

## Tasks

### Task 1: Unify severity scales across skills
**Files:** `.claude/skills/security-scan.md`, `.claude/skills/code-review.md`, `.claude/skills/boundary-and-sdk-enforcement.md`
**Action:**
Normalize all three skills to use the same 3-level severity scale: Critical (must fix before merge), Warning (should fix, creates tech debt), Info (consider improving). Update the Output sections of each skill file accordingly.

**Micro-steps:**
- Read all three skills to understand current severity terminology
- Normalize to: Critical (must fix) / Warning (should fix) / Info (suggestion)
- security-scan.md line 30: change 'Critical / High / Medium / Info' to 'Critical / Warning / Info'
- code-review.md lines 49-51: change 'Critical/Warning/Suggestion' to 'Critical/Warning/Info'
- boundary-and-sdk-enforcement.md lines 40-41: change 'Critical violations/Medium-risk gaps' to 'Critical/Warning/Info'

**TDD:**
- required: `false`
- reason: Documentation-only changes in markdown skill files

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Add missing principles to root CLAUDE.md
**Files:** `CLAUDE.md`
**Action:**
Add the 2 missing principles from .claude/CLAUDE.md to root CLAUDE.md Operating Principles section. Insert 'TDD Is Core' and 'Verification Before Completion' after item 4 (Goal-Driven Execution), then renumber the remaining items to 7-10.

**Micro-steps:**
- Read root CLAUDE.md Operating Principles section (lines 34-44)
- Insert 'TDD Is Core' as item 5 after Goal-Driven Execution
- Insert 'Verification Before Completion' as item 6 after TDD Is Core
- Renumber remaining items 7-10

**TDD:**
- required: `false`
- reason: Documentation-only change — adding principles that already exist in .claude/CLAUDE.md

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Consolidate perf-analysis into performance-review
**Files:** `.claude/skills/performance-review.md`, `.claude/skills/perf-analysis.md`
**Action:**
Merge the perf-analysis.md checklist (hotspot identification, complexity check, IO patterns, N+1, caching, backpressure/retries, payload handling, connection pooling) into performance-review.md as a subsection under Step B or as a new Step B2. Include the 'Process' section (measure-before, identify bottleneck, fix, measure-after, check regressions). Then delete perf-analysis.md.

**Micro-steps:**
- Read perf-analysis.md checklist items (8 items)
- Read performance-review.md Step B section
- Merge the unique perf-analysis checklist items into performance-review.md Step B or add a new 'Performance Deep Dive' subsection
- Delete perf-analysis.md
- Verify no other files reference perf-analysis.md

**TDD:**
- required: `false`
- reason: Documentation consolidation — merging two skill files into one

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
grep -r 'perf-analysis' .claude/ || echo 'no stale references'
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
docs(workflow): unify severity scales, add missing principles, consolidate perf skills
```
