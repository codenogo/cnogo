# Plan 01: Create scripts/context/workflow.py with suggest_scope() function, add graph-suggest-scope CLI subcommand, and wire into /plan command for automatic file scope suggestions.

## Goal
Create scripts/context/workflow.py with suggest_scope() function, add graph-suggest-scope CLI subcommand, and wire into /plan command for automatic file scope suggestions.

## Tasks

### Task 1: Create workflow.py with suggest_scope() and tests
**Files:** `scripts/context/workflow.py`, `tests/test_context_workflow.py`
**Action:**
Create scripts/context/workflow.py with suggest_scope() function. The function: (1) instantiates ContextGraph(repo_path), (2) auto-indexes, (3) searches for keywords via graph.search(), (4) for each found symbol gets its file_path, (5) runs impact analysis on related_files if provided, (6) merges results deduplicating by file path, (7) returns {enabled: true, suggestions: [{path, reason, confidence, low_confidence?}]}. Graceful degradation: wrap in try/except, return {enabled: false, error: str(e)}. Include fuzzy edges with low_confidence: true for confidence <= 0.5. Create tests/test_context_workflow.py with 5+ tests covering keywords, related_files, graceful degradation, and low_confidence labeling.

**Micro-steps:**
- Write test_suggest_scope_returns_enabled_structure with empty graph — verify empty suggestions returned
- Write test_suggest_scope_with_keywords — index a small codebase, verify keyword search returns matching file paths
- Write test_suggest_scope_with_related_files — verify impact analysis on related_files returns blast-radius file suggestions
- Write test_suggest_scope_graceful_degradation — verify {enabled: false, error: ...} on failure
- Write test_suggest_scope_low_confidence_label — verify fuzzy edges get low_confidence: true
- Run tests to verify RED (all fail since workflow.py doesn't exist)
- Implement suggest_scope(repo_path, keywords, related_files, limit) in workflow.py
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_workflow.py -x -q
python3 -m py_compile scripts/context/workflow.py
```

**Done when:** [Observable outcome]

### Task 2: Add graph-suggest-scope CLI subcommand
**Files:** `.cnogo/scripts/workflow_memory.py`
**Action:**
Add graph-suggest-scope subcommand to workflow_memory.py. Register argparse with: --keywords (comma-separated), --files (comma-separated related file paths), --repo, --limit (default 20), --json. Handler function cmd_graph_suggest_scope(): parse args, call suggest_scope() from scripts.context.workflow, output JSON or human-readable table. Add 'graph-suggest-scope' to _graph_cmds set. Add dispatch entry.

**Micro-steps:**
- Add 'graph-suggest-scope' to _graph_cmds exclusion set
- Register argparse subparser: graph-suggest-scope with --keywords, --files, --repo, --limit, --json
- Implement cmd_graph_suggest_scope() handler following existing graph-* pattern (open graph, call suggest_scope, format output, close graph)
- Add dispatch entry in command routing dict
- Run py_compile to verify syntax

**TDD:**
- required: `false`
- reason: Thin CLI wrapper — tested via integration through the Python function tests

**Verify:**
```bash
python3 -m py_compile scripts/workflow_memory.py
python3 .cnogo/scripts/workflow_memory.py graph-suggest-scope --keywords test --json
```

**Done when:** [Observable outcome]

### Task 3: Update /plan command to call graph-suggest-scope
**Files:** `.claude/commands/plan.md`
**Action:**
Add a graph scope suggestion step to plan.md between Step 2 (Load Minimal Context) and Step 3 (Partition Work). Add a bash call: `python3 .cnogo/scripts/workflow_memory.py graph-suggest-scope --keywords "<feature keywords from CONTEXT.json>" --files "<relatedCode from CONTEXT.json>" --json`. Instruct Claude to use the suggestions when authoring task files[] arrays. Note that suggestions are advisory — graph failures don't block planning. Keep the addition under 40 words to respect word budget.

**Micro-steps:**
- Read current plan.md Step 2 content
- Add graph-suggest-scope bash call after loading CONTEXT.json, before Step 3
- Add brief instruction to use suggestions when authoring task files[]
- Keep addition concise (word budget constraint)

**TDD:**
- required: `false`
- reason: Markdown template — no testable code

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py --feature graph-active-workflow
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_context_workflow.py -x -q
python3 -m py_compile scripts/context/workflow.py
python3 -m py_compile scripts/workflow_memory.py
python3 .cnogo/scripts/workflow_memory.py graph-suggest-scope --keywords test --json
```

## Commit Message
```
feat(graph-active-workflow): add suggest_scope() and graph-suggest-scope CLI for /plan file scope suggestions
```
