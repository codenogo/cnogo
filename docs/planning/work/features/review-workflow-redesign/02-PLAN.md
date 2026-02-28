# Plan 02: Rewrite review generation to output Security/Performance/Design Patterns sections instead of Karpathy Checklist

## Goal
Rewrite review generation to output Security/Performance/Design Patterns sections instead of Karpathy Checklist

## Tasks

### Task 1: Rewrite write_review() in workflow_checks_core.py
**Files:** `.cnogo/scripts/workflow_checks_core.py`
**Action:**
Rewrite the write_review() function: (1) Remove the principles parameter. (2) Replace the 'principles' key in REVIEW.json contract with three new arrays: 'securityFindings': [], 'performanceFindings': [], 'patternCompliance': [], and optional 'principleNotes': []. These are placeholder arrays populated by the manual review pass, not by automation. (3) In the REVIEW.md generation, replace '## Karpathy Checklist' table with three new sections: '## Security' (checklist: auth, input validation, secrets, injection, sensitive logging), '## Performance' (checklist: N+1 queries, unbounded loops, memory, timeouts), '## Design Patterns' (checklist: codebase pattern alignment, API consistency, abstractions). Each with a markdown table showing Area | Status | Notes. (4) Remove the _review_principles() helper function (no longer needed). (5) Update the call site in the main review flow to not pass principles.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_checks_core.py
! grep -q 'Karpathy' scripts/workflow_checks_core.py
```

**Done when:** [Observable outcome]

### Task 2: Update review.md command
**Files:** `.claude/commands/review.md`
**Action:**
In Step 3 (Focused Manual Pass): (1) Remove the line 'Use Karpathy principles from CLAUDE.md as the decision rubric. Do not restate full principle text in artifacts; fill principles[] status/notes in REVIEW.json.' (2) Replace with: 'Fill securityFindings[], performanceFindings[], patternCompliance[] in REVIEW.json based on manual review. Optionally add principleNotes[] if Operating Principles are relevant to specific findings.' Keep all other content unchanged.

**Verify:**
```bash
! grep -qi 'karpathy' .claude/commands/review.md
```

**Done when:** [Observable outcome]

### Task 3: Align code-review.md skill with new review structure
**Files:** `.claude/skills/code-review.md`
**Action:**
Add three review focus sections to the checklist matching the new REVIEW.md structure: Security (auth, input validation, secrets, injection), Performance (queries, loops, memory, timeouts), Design Patterns (codebase alignment, API consistency, abstractions). Keep existing checklist items that overlap (they already cover some of this). Remove any Karpathy references if present.

**Verify:**
```bash
grep -q 'Security' .claude/skills/code-review.md
grep -q 'Performance' .claude/skills/code-review.md
grep -q 'Design Patterns' .claude/skills/code-review.md
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/workflow_checks_core.py
! grep -rqi 'karpathy' scripts/workflow_checks_core.py .claude/commands/review.md .claude/skills/code-review.md
```

## Commit Message
```
feat(review-workflow): rewrite review generation with Security/Performance/Patterns focus
```
