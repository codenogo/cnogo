# Plan 01: Split test_context_graph.py into logical modules to clear the max-file-lines invariant and add test coverage mapping via CALLS edges

## Goal
Split test_context_graph.py into logical modules to clear the max-file-lines invariant and add test coverage mapping via CALLS edges

## Tasks

### Task 1: Split test_context_graph.py into logical test modules
**Files:** `tests/test_context_graph.py`, `tests/conftest_context.py`, `tests/test_context_core.py`, `tests/test_context_analysis.py`, `tests/test_context_types_exports.py`
**Action:**
Split the 1026-line test file into 3 focused test modules plus a shared conftest. Group: core (construction/indexing/queries/calls/search/exports API), analysis (dead-code/coupling/impact/community/flows), types+exports (type annotations/exports phase). Extract shared fixtures into conftest_context.py. All existing tests must pass unchanged.

**Micro-steps:**
- Read test_context_graph.py and identify shared fixtures and helpers
- Create tests/conftest_context.py with shared fixtures (sample code strings, graph setup helper)
- Create tests/test_context_core.py with construction, indexing, queries, call analysis, search, and package export tests
- Create tests/test_context_analysis.py with dead code, coupling, impact, community, and flow tests
- Create tests/test_context_types_exports.py with type annotation and exports phase tests
- Delete tests/test_context_graph.py
- Run all test modules to verify all existing tests pass

**TDD:**
- required: `false`
- reason: Pure refactoring of existing tests — no new behavior to test-first

**Verify:**
```bash
python3 -m pytest tests/test_context_core.py tests/test_context_analysis.py tests/test_context_types_exports.py -v
python3 -c "import pathlib; files = list(pathlib.Path('tests').glob('test_context_*.py')); assert all(sum(1 for _ in open(f)) <= 800 for f in files), f'file over 800 lines'"
```

**Done when:** [Observable outcome]

### Task 2: Add test coverage mapping phase
**Files:** `scripts/context/phases/test_coverage.py`, `scripts/context/storage.py`, `scripts/context/__init__.py`, `tests/test_context_core.py`
**Action:**
Add test coverage mapping using CALLS edges. Detect test files via path convention (test_*.py, *_test.py, files under tests/ directories). Walk CALLS edges from test file symbols to production symbols. Return {covered_symbols: [...], uncovered_symbols: [...], coverage_by_file: {...}, summary: {total, covered, uncovered, percentage}}. Add get_test_file_nodes() to GraphStorage.

**Micro-steps:**
- Write failing test for ContextGraph.test_coverage() in test_context_core.py
- Run test to verify RED
- Add get_test_file_nodes() query to GraphStorage for efficient test file lookup
- Create scripts/context/phases/test_coverage.py with analyze_test_coverage(storage) function
- Add test_coverage() public method to ContextGraph returning coverage mapping
- Run test to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_core.py -v -k test_coverage`
- passingVerify:
  - `python3 -m pytest tests/test_context_core.py -v -k test_coverage`

**Verify:**
```bash
python3 -m pytest tests/test_context_core.py -v -k test_coverage
```

**Done when:** [Observable outcome]

### Task 3: Add graph-test-coverage CLI command and workflow integration
**Files:** `scripts/workflow_memory.py`, `scripts/context/workflow.py`, `tests/test_context_core.py`
**Action:**
Add graph-test-coverage CLI command outputting coverage report (JSON with --json flag, human-readable by default). Add test_coverage_report(repo_path) to workflow.py following the graceful degradation pattern (returns {enabled: false, error: ...} on failure). This surfaces untested symbols during /review as warnings.

**Micro-steps:**
- Write failing test for test_coverage_report() workflow function
- Run test to verify RED
- Add graph-test-coverage subcommand to workflow_memory.py CLI
- Add test_coverage_report() to workflow.py following the graceful degradation pattern
- Run test to verify GREEN
- Verify CLI command end-to-end

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_core.py -v -k test_coverage_workflow`
- passingVerify:
  - `python3 -m pytest tests/test_context_core.py -v -k test_coverage_workflow`

**Verify:**
```bash
python3 -m pytest tests/test_context_core.py -v -k coverage
python3 scripts/workflow_memory.py graph-test-coverage --help 2>&1 | grep -q coverage
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_core.py tests/test_context_analysis.py tests/test_context_types_exports.py -v
python3 -c "import pathlib; files = list(pathlib.Path('tests').glob('test_context_*.py')); assert all(sum(1 for _ in open(f)) <= 800 for f in files)"
python3 scripts/workflow_memory.py graph-test-coverage --help 2>&1 | grep -q coverage
```

## Commit Message
```
feat(context-graph-next): split test file into modules and add test coverage mapping
```
