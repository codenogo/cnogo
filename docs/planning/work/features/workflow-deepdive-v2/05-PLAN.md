# Plan 05: Add phase transition docs, improve graph failure alerting, and update stale ROADMAP/PROJECT docs

## Goal
Add phase transition docs, improve graph failure alerting, and update stale ROADMAP/PROJECT docs

## Tasks

### Task 1: Add phase transition state machine documentation
**Files:** `.claude/CLAUDE.md`
**Action:**
In .claude/CLAUDE.md, add a 'Phase Transitions' subsection under Memory Engine. Content: 'Phases: discuss → plan → implement → review → ship (forward-only, advisory). Use phase-get/phase-set commands. Backward transitions emit stderr warnings.' Keep to 2-3 lines to stay within token budget.

**Micro-steps:**
- Add compact Phase Transitions subsection under Memory Engine
- Document valid phases and forward-only rule
- Note advisory mode default
- Stay within bootstrapContext.workflowClaudeWordMax budget

**TDD:**
- required: `false`
- reason: Documentation addition validated by workflow_validate token budgets

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Improve graph failure alerting in hooks
**Files:** `.cnogo/scripts/workflow_hooks.py`
**Action:**
In workflow_hooks.py post_commit_graph(), replace the single except handler with two: (1) except ImportError: print setup instructions pointing to .cnogo/requirements-graph.txt, (2) except Exception as exc: print structured warning with exception type and suggestion to check graph DB. Both return 0 (never block).

**Micro-steps:**
- In post_commit_graph() exception handler, distinguish ImportError from other errors
- Add actionable setup instructions for ImportError
- Add structured warning format for other errors

**TDD:**
- required: `false`
- reason: Error reporting improvement; no behavior change for successful graph operations

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
```

**Done when:** [Observable outcome]

### Task 3: Update ROADMAP and PROJECT staleness
**Files:** `docs/planning/ROADMAP.md`, `docs/planning/PROJECT.md`
**Action:**
Update ROADMAP.md: mark workflow-audit-fixes as completed, add workflow-deepdive-v2 as in-progress under current milestone. Update PROJECT.md: ensure project description and current status reflect actual state. Remove any references to completed or abandoned features that are no longer relevant.

**Micro-steps:**
- Read current ROADMAP.md and PROJECT.md
- Mark workflow-audit-fixes as completed
- Add workflow-deepdive-v2 as current in-progress work
- Remove or archive stale items

**TDD:**
- required: `false`
- reason: Documentation update with no code changes

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
docs(workflow): add phase transition docs, graph alerting, update ROADMAP/PROJECT
```
