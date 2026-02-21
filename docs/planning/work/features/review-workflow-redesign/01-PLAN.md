# Plan 01: Rename all Karpathy references to Operating Principles in config and documentation files

## Goal
Rename all Karpathy references to Operating Principles in config and documentation files

## Tasks

### Task 1: Rename WORKFLOW.json config keys
**Files:** `docs/planning/WORKFLOW.json`, `docs/templates/WORKFLOW-TEMPLATE.json`
**Action:**
In both files: rename enforcement.karpathyChecklist to enforcement.operatingPrinciples (keep same value 'warn'). Remove enforcement.reviewPrinciples array entirely (principles are no longer review-scoped). Keep all other config unchanged.

**Verify:**
```bash
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); e=d['enforcement']; assert 'operatingPrinciples' in e and 'karpathyChecklist' not in e and 'reviewPrinciples' not in e, f'keys: {list(e.keys())}'"
```

**Done when:** [Observable outcome]

### Task 2: Remove Karpathy attribution from CLAUDE.md files
**Files:** `.claude/CLAUDE.md`, `CLAUDE.md`
**Action:**
In .claude/CLAUDE.md: remove the 'Inspired by [forrestchang/andrej-karpathy-skills]...' attribution line. Keep the '## Operating Principles' header and all 8 principles unchanged. In root CLAUDE.md: already says 'Operating Principles' — no header change needed, just verify no Karpathy references exist.

**Verify:**
```bash
! grep -qi 'karpathy' .claude/CLAUDE.md
! grep -qi 'karpathy' CLAUDE.md
```

**Done when:** [Observable outcome]

### Task 3: Remove Karpathy references from README.md
**Files:** `README.md`
**Action:**
Rename the '### Karpathy-Inspired Claude Coding Principles' section to '### Operating Principles'. Remove the source attribution link to forrestchang/andrej-karpathy-skills. In the Monorepos section, rename the enforcement.karpathyChecklist reference to enforcement.operatingPrinciples. Keep all other content unchanged.

**Verify:**
```bash
! grep -qi 'karpathy' README.md
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.json')); assert 'operatingPrinciples' in d['enforcement']"
! grep -rqi 'karpathy' .claude/CLAUDE.md CLAUDE.md README.md docs/planning/WORKFLOW.json docs/templates/WORKFLOW-TEMPLATE.json
```

## Commit Message
```
refactor(review-workflow): rename Karpathy references to Operating Principles in config and docs
```
