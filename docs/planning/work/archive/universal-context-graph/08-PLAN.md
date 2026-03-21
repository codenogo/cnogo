# Plan 08: Complete ContextGraph class (all 21 methods), workflow.py integration, CLI verification, and full test suite

## Goal
Complete ContextGraph class (all 21 methods), workflow.py integration, CLI verification, and full test suite

## Tasks

### Task 1: Complete ContextGraph class with all 21 public methods
**Files:** `.cnogo/scripts/context/__init__.py`, `tests/test_context_core.py`, `tests/test_context_query.py`
**Action:**
Complete the ContextGraph class in __init__.py with all 21 public methods preserving exact API signatures. Wire up: search() -> HybridSearch, communities() -> Leiden, coupling() -> Jaccard+git, dead_code/flows/impact -> rebuilt phases, visualize() -> visualization.py. Add embedding generation as final step of index() pipeline.

**Micro-steps:**
- Write failing tests for remaining ContextGraph methods: context(), callers_with_confidence(), callees(), communities(), coupling(), dead_code(), flows(), search(), review_impact(), test_coverage(), contract_check(), prioritize_files(), visualize()
- Implement each method delegating to the rebuilt phases and search engine
- Ensure search() uses HybridSearch, communities() uses Leiden, coupling() uses Jaccard+git
- Wire embedding generation into index() pipeline (embed nodes after all phases complete)
- Verify all 21 methods match original API signatures exactly
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_core.py tests/test_context_query.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_core.py tests/test_context_query.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_core.py tests/test_context_query.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 2: Workflow integration functions
**Files:** `.cnogo/scripts/context/workflow.py`, `tests/test_context_workflow.py`
**Action:**
Rebuild workflow.py with same 6 public functions that workflow_memory.py imports. Each function creates a ContextGraph, calls the appropriate method, and returns structured results. Preserve the graceful degradation pattern (try/except returning {enabled, error}). Functions: test_coverage_report, suggest_scope, enrich_context, validate_scope, contract_warnings, prioritize_context.

**Micro-steps:**
- Write failing tests for all 6 workflow functions: test_coverage_report, suggest_scope, enrich_context, validate_scope, contract_warnings, prioritize_context
- Implement workflow.py with same 6 functions delegating to ContextGraph methods
- Preserve graceful degradation pattern: each function returns {enabled: True/False, error: ...} on failure
- Verify workflow_memory.py imports still work (lazy imports from scripts.context.workflow)
- Run passing tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_workflow.py -v 2>&1 | tail -10
```

**Done when:** [Observable outcome]

### Task 3: CLI verification and full test suite
**Files:** `tests/test_context_cli.py`
**Action:**
Verify all 19 graph CLI subcommands work end-to-end through workflow_memory.py. Each subcommand lazily imports from scripts.context — verify imports resolve, ContextGraph instantiates correctly, and output format matches expectations. Run the full context test suite and fix any remaining failures.

**Micro-steps:**
- Write/update test_context_cli.py testing all 19 graph CLI subcommands via workflow_memory.py
- Verify graph-index, graph-query, graph-impact, graph-context, graph-dead, graph-coupling, graph-blast-radius, graph-communities, graph-flows, graph-search, graph-status, graph-suggest-scope, graph-validate-scope, graph-enrich, graph-contract-check, graph-prioritize, graph-test-coverage, graph-viz all work
- Run full test suite: python3 -m pytest tests/test_context_*.py
- Fix any failures across the entire context test suite
- Verify no regressions in non-context tests

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x 2>&1 | tail -3`
- passingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x 2>&1 | tail -3`

**Verify:**
```bash
python3 -m pytest tests/test_context_cli.py -v 2>&1 | tail -10
python3 -m pytest tests/test_context_*.py --tb=no -q 2>&1 | tail -5
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_*.py --tb=no -q 2>&1 | tail -5
python3 .cnogo/scripts/workflow_memory.py graph-status 2>&1 | head -5
```

## Commit Message
```
feat(context-graph): complete integration — all 21 API methods, workflow, CLI, full test suite
```
