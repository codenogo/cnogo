# Verification (CI): memory-engine-fixes

**Timestamp:** 2026-02-16T01:06:31Z

## Summary

- Lint: **pass**
- Types: **skipped**
- Tests: **skipped**
- Invariants: **0 fail / 6 warn**

## Per-Package Results

### cnogo-scripts (`scripts`)
- lint: **pass** (`python3 -m py_compile scripts/workflow_validate.py scripts/workflow_checks.py scripts/workflow_detect.py scripts/workflow_utils.py scripts/workflow_render.py scripts/workflow_hooks.py scripts/workflow_memory.py`, cwd `.`)
- typecheck: **skipped**
- test: **skipped**

## Invariant Findings

- [warn] `scripts/workflow_checks.py:1` File has 991 lines (max 800). (max-file-lines)
- [warn] `scripts/workflow_validate.py:1` File has 1464 lines (max 800). (max-file-lines)
- [warn] `scripts/workflow_validate.py:503` Line length 150 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate.py:537` Line length 147 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate.py:862` Line length 142 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate.py:922` Line length 142 exceeds 140. (max-line-length)
