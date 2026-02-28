# Plan 01: Eliminate all 14 REVIEW.json schemaVersion errors and 3 ambiguous-path warnings from the validator

## Goal
Eliminate all 14 REVIEW.json schemaVersion errors and 3 ambiguous-path warnings from the validator

## Tasks

### Task 1: Batch-upgrade 14 REVIEW.json files to schemaVersion 4
**Files:** `docs/planning/work/features/multi-agent-enhancements/REVIEW.json`, `docs/planning/work/features/skills-usage-audit/REVIEW.json`, `docs/planning/work/features/team-implement-integration/REVIEW.json`, `docs/planning/work/features/agent-architecture-redesign/REVIEW.json`, `docs/planning/work/features/template-self-separation/REVIEW.json`, `docs/planning/work/features/compaction-resilience/REVIEW.json`, `docs/planning/work/features/kill-state-md/REVIEW.json`, `docs/planning/work/features/execution-coordination/REVIEW.json`, `docs/planning/work/features/memory-engine-fixes/REVIEW.json`, `docs/planning/work/features/deterministic-coordination/REVIEW.json`, `docs/planning/work/features/review-workflow-redesign/REVIEW.json`, `docs/planning/work/features/install-template-sync/REVIEW.json`, `docs/planning/work/features/worktree-parallel-agents/REVIEW.json`, `docs/planning/work/features/workflow-dead-code-cleanup/REVIEW.json`
**Action:**
Write and run a Python script that batch-upgrades all 14 REVIEW.json files. For each file: set schemaVersion to 4, add a stageReviews array with two stages (spec-compliance and code-quality) derived from existing verdict/manualFindings/principles. Preserve all existing fields. Mark stageReviews as retroactive.

**Micro-steps:**
- Read one REVIEW.json to confirm current schema shape
- Write a Python batch script that: reads each file, sets schemaVersion to 4, adds retroactive stageReviews from existing data (verdict → both stages pass, manualFindings/principles → evidence), writes back
- Run the batch script
- Spot-check 2-3 files to confirm structure matches cnogo-packaging/REVIEW.json pattern

**TDD:**
- required: `false`
- reason: JSON schema migration of historical artifacts — no behavioral code to test

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); errors=[x for x in d if x['level']=='ERROR']; print(f'{len(errors)} errors'); sys.exit(1 if errors else 0)"
```

**Done when:** [Observable outcome]

### Task 2: Fix ambiguous file paths in workflow-dead-code-cleanup/02-PLAN.json
**Files:** `docs/planning/work/features/workflow-dead-code-cleanup/02-PLAN.json`
**Action:**
Remove trailing slashes from the 3 archive directory paths in task 1 files[]: 'docs/planning/work/archive/event-hardening/', 'docs/planning/work/archive/context-engineering-fixes/', 'docs/planning/work/archive/overstory-workflow-patterns/'.

**Micro-steps:**
- Read 02-PLAN.json and identify the 3 trailing-slash paths
- Remove trailing slashes from all 3 archive directory paths in files[]
- Verify no ambiguous-path warnings remain for this file

**TDD:**
- required: `false`
- reason: Simple trailing-slash removal in historical plan artifact

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); ambig=[x for x in d if 'ambiguous' in x['message']]; print(f'{len(ambig)} ambiguous warnings'); sys.exit(1 if ambig else 0)"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py --json 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); errors=[x for x in d if x['level']=='ERROR']; ambig=[x for x in d if 'ambiguous' in x['message']]; print(f'{len(errors)} errors, {len(ambig)} ambiguous'); sys.exit(1 if errors or ambig else 0)"
```

## Commit Message
```
chore(planning): fix 14 REVIEW.json schemaVersion errors and 3 ambiguous-path warnings
```
