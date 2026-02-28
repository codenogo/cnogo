# Plan 03: Add enrich_context() function to workflow.py, add graph-enrich CLI subcommand, and wire into /discuss command for automatic related code discovery and architecture surfacing.

## Goal
Add enrich_context() function to workflow.py, add graph-enrich CLI subcommand, and wire into /discuss command for automatic related code discovery and architecture surfacing.

## Tasks

### Task 1: Add enrich_context() and tests
**Files:** `scripts/context/workflow.py`, `tests/test_context_workflow.py`
**Action:**
Add enrich_context(repo_path, keywords, limit=20) to scripts/context/workflow.py. The function: (1) instantiates ContextGraph(repo_path), (2) auto-indexes, (3) for each keyword, runs graph.search(keyword, limit), (4) for top results, gets graph.context(node_id) to discover callers, callees, heritage, (5) deduplicates by node id, (6) returns {enabled: true, related_code: [{path, name, label, relationship, confidence}], architecture: {communities_hint: <count of unique files touched>}}. Graceful degradation via try/except. Add 5 tests to test_context_workflow.py.

**Micro-steps:**
- Write test_enrich_context_returns_enabled_structure — verify structure with empty graph returns empty related_code
- Write test_enrich_context_with_keywords — index a small codebase, verify keyword search returns related code with callers/callees
- Write test_enrich_context_includes_heritage — verify parent/child class relationships appear in results
- Write test_enrich_context_graceful_degradation — verify {enabled: false, error: ...} on failure
- Write test_enrich_context_deduplication — verify duplicate symbols across multiple keywords are deduplicated
- Run tests to verify RED
- Implement enrich_context(repo_path, keywords, limit) in workflow.py
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_workflow.py::test_enrich_context_returns_enabled_structure -x -q`
- passingVerify:
  - `python3 -m pytest tests/test_context_workflow.py -x -q`

**Verify:**
```bash
python3 -m pytest tests/test_context_workflow.py -x -q
python3 -m py_compile scripts/context/workflow.py
```

**Done when:** [Observable outcome]

### Task 2: Add graph-enrich CLI subcommand
**Files:** `scripts/workflow_memory.py`
**Action:**
Add graph-enrich subcommand to workflow_memory.py. Register argparse with: --keywords (comma-separated, required), --repo, --limit (default 20), --json. Handler function cmd_graph_enrich(): parse args, call enrich_context() from scripts.context.workflow, output JSON or human-readable table of related code grouped by relationship type. Add to _graph_cmds and dispatch.

**Micro-steps:**
- Add 'graph-enrich' to _graph_cmds exclusion set
- Register argparse subparser: graph-enrich with --keywords, --repo, --limit, --json
- Implement cmd_graph_enrich() handler
- Add dispatch entry in command routing dict
- Run py_compile to verify syntax

**TDD:**
- required: `false`
- reason: Thin CLI wrapper — tested via integration through the Python function tests

**Verify:**
```bash
python3 -m py_compile scripts/workflow_memory.py
python3 scripts/workflow_memory.py graph-enrich --keywords test --json
```

**Done when:** [Observable outcome]

### Task 3: Update /discuss command to call graph-enrich
**Files:** `.claude/commands/discuss.md`
**Action:**
Add a context enrichment step to discuss.md in Step 2 (Read Lightweight Context), after the rg search. Add a bash call: `python3 scripts/workflow_memory.py graph-enrich --keywords "<feature keywords>" --json`. Instruct Claude to use the enriched results to auto-populate relatedCode[] in CONTEXT.json and to surface architectural constraints (callers, callees, heritage) during the decision conversation. Keep the addition under 40 words.

**Micro-steps:**
- Read current discuss.md Step 2 content
- Add graph-enrich bash call after rg search, before Step 3
- Instruct Claude to use enriched results when populating relatedCode[] in CONTEXT.json
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
python3 -m pytest tests/test_context_graph.py -x -q
python3 -m py_compile scripts/context/workflow.py
python3 -m py_compile scripts/workflow_memory.py
python3 scripts/workflow_memory.py graph-enrich --keywords test --json
```

## Commit Message
```
feat(graph-active-workflow): add enrich_context() and graph-enrich CLI for /discuss context enrichment
```
