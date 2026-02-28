# Plan 03: Add API contract break detection for changed function signatures and enhance suggest_scope with auto-populate support

## Goal
Add API contract break detection for changed function signatures and enhance suggest_scope with auto-populate support

## Tasks

### Task 1: Add signature snapshot and comparison logic
**Files:** `scripts/context/phases/contracts.py`, `scripts/context/python_parser.py`, `tests/test_context_contracts.py`
**Action:**
Add signature comparison using AST parsing. extract_current_signatures(file_path) parses a Python file and returns {qualified_name: signature_str} for all functions/methods. compare_signatures(stored_nodes, current_sigs) compares stored graph node signatures against fresh AST output and returns [{symbol, old_signature, new_signature, change_type}]. Change types: 'param_added', 'param_removed', 'default_changed', 'return_type_changed', 'signature_changed'. Reuse _build_signature() logic from python_parser.py.

**Micro-steps:**
- Write failing test for extract_current_signatures() and compare_signatures()
- Run test to verify RED
- Create scripts/context/phases/contracts.py with extract_current_signatures(file_path) using AST
- Add compare_signatures(stored_nodes, current_sigs) returning list of signature changes
- Run test to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_signature`
- passingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_signature`

**Verify:**
```bash
python3 -m pytest tests/test_context_contracts.py -v -k test_signature
```

**Done when:** [Observable outcome]

### Task 2: Add contract_check() method and graph-contract-check CLI
**Files:** `scripts/context/__init__.py`, `scripts/context/phases/contracts.py`, `.cnogo/scripts/workflow_memory.py`, `tests/test_context_contracts.py`
**Action:**
Add ContextGraph.contract_check(changed_files) that: (1) extracts current signatures from changed files via AST, (2) compares against stored graph node signatures, (3) for each changed signature, finds all callers via callers_with_confidence(), (4) returns {breaks: [{symbol, old_signature, new_signature, change_type, callers: [{name, file, confidence}]}], summary: {total_breaks, total_affected_callers}}. Add graph-contract-check CLI with --json flag.

**Micro-steps:**
- Write failing test for ContextGraph.contract_check(changed_files)
- Run test to verify RED
- Add contract_check(changed_files) to ContextGraph that detects signature changes and finds affected callers
- Add graph-contract-check subcommand to workflow_memory.py CLI
- Run test to verify GREEN
- Verify CLI outputs contract warnings

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_contract_check`
- passingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_contract_check`

**Verify:**
```bash
python3 -m pytest tests/test_context_contracts.py -v
python3 .cnogo/scripts/workflow_memory.py graph-contract-check --help 2>&1 | grep -q contract
```

**Done when:** [Observable outcome]

### Task 3: Integrate contract detection into review workflow and enhance suggest_scope auto-populate
**Files:** `scripts/context/workflow.py`, `tests/test_context_contracts.py`
**Action:**
Add contract_warnings(repo_path, changed_files) to workflow.py for /review integration. Returns {enabled, breaks: [...], summary: {...}} following the graceful degradation pattern. Enhance suggest_scope() to include an 'auto_populate' key containing the top-N most relevant files ranked by confidence, ready for direct insertion into plan task files[] arrays. Both functions return {enabled: false, error: ...} on failure.

**Micro-steps:**
- Write failing test for contract_warnings() workflow function
- Run test to verify RED
- Add contract_warnings(repo_path, changed_files) to workflow.py with graceful degradation
- Enhance suggest_scope() to include auto_populate key with confidence-ranked file list for plan files[]
- Run test to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_workflow`
- passingVerify:
  - `python3 -m pytest tests/test_context_contracts.py -v -k test_workflow`

**Verify:**
```bash
python3 -m pytest tests/test_context_contracts.py -v
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_contracts.py -v
python3 .cnogo/scripts/workflow_memory.py graph-contract-check --help 2>&1 | grep -q contract
```

## Commit Message
```
feat(context-graph-next): add API contract break detection and auto-populate plan files
```
