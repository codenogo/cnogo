# Verification (CI): context-engineering-fixes

**Timestamp:** 2026-02-18T00:09:18Z

## Summary

- Lint: **pass**
- Types: **skipped**
- Tests: **skipped**
- Invariants: **0 fail / 11 warn**
- Token savings: **0 tokens** (0.0%, 1 checks)

## Per-Package Results

### cnogo-scripts (`scripts`)
- lint: **pass** (`python3 -m py_compile scripts/workflow_validate.py scripts/workflow_validate_core.py scripts/workflow_checks.py scripts/workflow_checks_core.py scripts/workflow_detect.py scripts/workflow_utils.py scripts/workflow_render.py scripts/workflow_hooks.py scripts/workflow_memory.py`, cwd `.`)
  - tokenTelemetry: in=0 out=0 saved=0 (0.0%)
- typecheck: **skipped**
- test: **skipped**

## Invariant Findings

- [warn] `scripts/workflow_checks_core.py:43` Line length 143 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:550` Line length 146 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:553` Line length 148 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:584` Line length 146 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:587` Line length 145 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:590` Line length 148 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:625` Line length 150 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:659` Line length 147 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:720` Line length 152 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:998` Line length 142 exceeds 140. (max-line-length)
- [warn] `scripts/workflow_validate_core.py:1058` Line length 142 exceeds 140. (max-line-length)
