# Review Report — template-self-separation

**Date:** 2026-02-14
**Branch:** main
**Commits:** `799e8a5` (Plan 01), `1727c2a` (Plan 02)
**Reviewer:** Claude (3 parallel review agents)

## Automated Checks

| Check | Result |
|-------|--------|
| Linting (py_compile) | ✅ Passed |
| Workflow validation | ⚠️ Warnings (empty test/typecheck — expected) |
| Secret scanning | ✅ Passed |
| Memory smoke test | ✅ Passed (0 open issues) |
| Install E2E test | ✅ Passed |

## Issues Found

### ❌ Blockers (must fix)

None.

### ⚠️ Warnings (should fix)

| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| W1 | `CHANGELOG.md` | 35 | Says "Total commands increased from 15 to **27**" but actual count is **28** (.claude/commands/ has 28 files) | Medium |
| W2 | `CLAUDE.md` | 70 | Smoke test command `from scripts.memory import prime; print(prime(...))` will throw if memory not initialized — needs `is_initialized()` guard | Medium |
| W3 | `docs/planning/WORKFLOW.json` | 22 | Lint command only checks 3 of 7 Python files (`workflow_validate.py`, `workflow_checks.py`, `workflow_detect.py`) — misses `workflow_utils.py`, `workflow_render.py`, `workflow_hooks.py`, `workflow_memory.py` | Medium |
| W4 | `docs/planning/ROADMAP.md` | 23 | `quick` appears in both v1.0's "15 commands" and v1.1's "13 new commands" list — possible double-count (15 + 13 = 28 works if `quick` was genuinely new in v1.1) | Low |

### 💡 Suggestions (optional)

| # | File | Line | Suggestion |
|---|------|------|------------|
| S1 | `install.sh` | 179 | Add comment documenting parameter expansion: `# Transform: PROJECT.md → PROJECT-TEMPLATE.md (source) → PROJECT.md (dest)` |
| S2 | `install.sh` | 192, 195 | ADR-TEMPLATE.md and CONTEXT-TEMPLATE.md still live in `docs/planning/` subdirs, not `docs/templates/` — consolidation would improve consistency |
| S3 | `CLAUDE.md` | 95-111 | Memory Engine section duplicates Quick Reference CLI examples (lines 11-16) — consider consolidating |

## Manual Review Notes

### Security
| Check | Status |
|-------|--------|
| No hardcoded credentials | ✅ |
| Path traversal prevention | ✅ SCRIPT_DIR canonicalized via `cd && pwd` |
| Variable quoting | ✅ All paths double-quoted |
| No user input in template paths | ✅ Hardcoded loop list |

### Code Quality
| Check | Status |
|-------|--------|
| Functions ≤50 lines | ✅ |
| Clear naming | ✅ |
| Error handling present | ✅ |
| Consistent with patterns | ✅ |

### Verification
| Check | Status |
|-------|--------|
| Templates are properly generic | ✅ No cnogo-specific content in templates |
| cnogo docs contain real content | ✅ PROJECT.md, ROADMAP.md filled accurately |
| install.sh behavior preserved | ✅ Skip-if-exists unchanged, only source paths changed |
| Bug fix correct | ✅ `kind_counts.keys() - {"other"}` is the right fix |
| No similar bugs elsewhere | ✅ Searched codebase, no other dict-set patterns |

### Karpathy Checklist

| Principle | Status | Notes |
|----------|--------|-------|
| Think Before Coding | ✅ | CONTEXT.md captured all decisions before implementation |
| Simplicity First | ✅ | Minimal changes — copy templates, update one line in install.sh, fill docs |
| Surgical Changes | ✅ | Only touched files listed in plan; one opportunistic bugfix (latent TypeError) |
| Goal-Driven Execution | ✅ | Each task had explicit verify commands; E2E test caught cp destination bug |

## Verdict

⚠️ **Conditional** — 4 warnings found, no blockers.

**Recommended fixes before ship:**
1. Fix CHANGELOG.md command count (27 → 28)
2. Add `is_initialized()` guard to CLAUDE.md smoke test
3. Expand WORKFLOW.json lint to cover all 7 Python files

**Can defer:**
- W4 (ROADMAP quick double-count) — needs investigation
- S1-S3 (suggestions) — nice-to-have

---
*Reviewed: 2026-02-14*
