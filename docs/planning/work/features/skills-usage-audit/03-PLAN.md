# Plan 03: Create the Performance Review (Final Gate) composite skill and integrate it into the /review command

## Goal
Create the Performance Review (Final Gate) composite skill and integrate it into the /review command

## Tasks

### Task 1: Create performance-review.md composite skill
**Files:** `.claude/skills/performance-review.md`
**Action:**
Create a new skill file with YAML frontmatter (name: performance-review, tags: [domain, quality, security, workflow], appliesTo: [review]) containing the Performance Review (Final Gate) specification: Purpose section, token-minimal inputs (pointers: diff_ref, run_ledger, validation paths), 6-step deterministic procedure (A: Scope+Intent, B: Code Review Checklist referencing code-review.md, C: Contract Compliance with multi-agent safety checks, D: Security/OWASP Quick Pass referencing security-scan.md, E: PRR-lite referencing release-readiness.md, F: Validation Baseline Diff), 7-axis scoring rubric (Correctness, Security, Contract Compliance, Performance, Maintainability, Test Coverage, Scope Discipline — each 0-2, pass >= 11/14 with no 0 in Correctness/Security/Contract Compliance), output format (Verdict/Blockers/Concerns/Improvements/Evidence/Next Actions). Sub-skills are referenced by path, never duplicated. Include multi-agent contract rules: workers cannot close PLAN/EPIC, SubagentStop marks DONE_BY_WORKER only, leader-only reconciliation.

**Verify:**
```bash
python3 -c "from pathlib import Path; from scripts.workflow_utils import parse_skill_frontmatter; r = parse_skill_frontmatter(Path('.claude/skills/performance-review.md')); assert r['name'] == 'performance-review'; assert 'review' in r['appliesTo']; print('frontmatter ok')"
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Integrate Performance Review into /review command
**Files:** `.claude/commands/review.md`
**Action:**
Update Step 3 (Focused Manual Pass) to use the Performance Review skill as the primary final-gate procedure. Replace the current bullet-list approach with: 'Apply `.claude/skills/performance-review.md` as the final-gate review procedure. This orchestrates code-review, security-scan, and release-readiness skills in a deterministic 6-step sequence with a 7-axis scoring rubric.' Keep the existing skill references as fallback context but make Performance Review the primary driver. Update the verdict section to reference the scoring rubric pass rule.

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "from pathlib import Path; from scripts.workflow_utils import discover_skills; skills = discover_skills(Path('.claude/skills')); names = [s['name'] for s in skills]; assert 'performance-review' in names; print(f'{len(skills)} skills including performance-review')"
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(skills-usage-audit): add performance review final gate skill and integrate into /review
```
