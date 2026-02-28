# Plan 02: Add validate_scope() function to workflow.py, add graph-validate-scope CLI subcommand, and wire into /implement command for automatic blast-radius validation after each task.

## Goal
Add validate_scope() function to workflow.py, add graph-validate-scope CLI subcommand, and wire into /implement command for automatic blast-radius validation after each task.

## Tasks

### Task 1: Add validate_scope() and tests
**Files:** `scripts/context/workflow.py`, `tests/test_context_workflow.py`
**Action:**
Add validate_scope(repo_path, declared_files, changed_files=None) to scripts/context/workflow.py. The function: (1) instantiates ContextGraph(repo_path), (2) auto-indexes, (3) if changed_files is None, uses declared_files as changed_files, (4) runs graph.review_impact(changed_files) to get blast-radius, (5) compares affected_files against declared_files to find violations (files affected but not declared), (6) returns {enabled: true, within_scope: bool, declared: [...], changed: [...], blast_radius: [{path, symbols, depth}], violations: [{path, reason}], warnings: [{path, confidence, low_confidence: true}]}. Fuzzy edges (confidence <= 0.5) appear in warnings with low_confidence: true. Graceful degradation via try/except. Add 5 tests to test_context_workflow.py.

**Micro-steps:**
- Write test_validate_scope_within_scope — declared files match changed files, expect within_scope: true
- Write test_validate_scope_violation — changed files extend beyond declared scope, expect violations list
- Write test_validate_scope_blast_radius — verify blast-radius symbols from impact analysis are included
- Write test_validate_scope_low_confidence_warnings — verify fuzzy edges appear with low_confidence: true in warnings
- Write test_validate_scope_graceful_degradation — verify {enabled: false, error: ...} on failure
- Run tests to verify RED
- Implement validate_scope(repo_path, declared_files, changed_files) in workflow.py
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_workflow.py::test_validate_scope_within_scope -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_workflow.py -x -q
python3 -m py_compile scripts/context/workflow.py
```

**Done when:** [Observable outcome]

### Task 2: Add graph-validate-scope CLI subcommand
**Files:** `scripts/workflow_memory.py`
**Action:**
Add graph-validate-scope subcommand to workflow_memory.py. Register argparse with: --declared (comma-separated declared file paths, required), --changed (comma-separated changed file paths, optional), --repo, --json. Handler function cmd_graph_validate_scope(): parse args, call validate_scope() from scripts.context.workflow, output JSON or human-readable summary showing within_scope status, violations, and warnings. Add to _graph_cmds and dispatch.

**Micro-steps:**
- Add 'graph-validate-scope' to _graph_cmds exclusion set
- Register argparse subparser: graph-validate-scope with --declared, --changed, --repo, --json
- Implement cmd_graph_validate_scope() handler
- Add dispatch entry in command routing dict
- Run py_compile to verify syntax

**TDD:**
- required: `false`
- reason: Thin CLI wrapper — tested via integration through the Python function tests

**Verify:**
```bash
python3 -m py_compile scripts/workflow_memory.py
python3 scripts/workflow_memory.py graph-validate-scope --declared scripts/context/workflow.py --json
```

**Done when:** [Observable outcome]

### Task 3: Update /implement command to call graph-validate-scope
**Files:** `.claude/commands/implement.md`
**Action:**
Add a scope validation step to implement.md in Step 3 (Execute Tasks), after running verify commands (step 4) and before claiming success (step 5). Add a bash call: `python3 scripts/workflow_memory.py graph-validate-scope --declared "<task file_scope paths>" --changed "<actually modified files>" --json`. Instruct Claude to warn the user if violations are found (files outside declared scope affected) but not block task completion. Keep the addition under 40 words.

**Micro-steps:**
- Read current implement.md Step 3 content
- Add graph-validate-scope bash call after task execution (step 3.4), before claiming success
- Instruct Claude to warn user if violations found but not block implementation
- Keep addition concise (word budget constraint)

**TDD:**
- required: `false`
- reason: Markdown template — no testable code

**Verify:**
```bash
python3 scripts/workflow_validate.py --feature graph-active-workflow
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_workflow.py -x -q
python3 -m py_compile scripts/context/workflow.py
python3 -m py_compile scripts/workflow_memory.py
python3 scripts/workflow_memory.py graph-validate-scope --declared scripts/context/workflow.py --json
```

## Commit Message
```
feat(graph-active-workflow): add validate_scope() and graph-validate-scope CLI for /implement blast-radius validation
```
