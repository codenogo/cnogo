# Plan 04: Address documentation gaps: update ROADMAP.md with context graph subsystem, add graph config to WORKFLOW.json, expand secret redaction patterns

## Goal
Address documentation gaps: update ROADMAP.md with context graph subsystem, add graph config to WORKFLOW.json, expand secret redaction patterns

## Tasks

### Task 1: Add context graph subsystem to ROADMAP.md
**Files:** `docs/planning/ROADMAP.md`
**Action:**
Add a 'Context Graph' section to ROADMAP.md documenting the graph subsystem: storage layer, proximity queries, heritage tracking, flow analysis, graph DB (kuzu), post-commit indexing hooks, and the resolver agent. Include file references for .cnogo/scripts/context/ directory.

**Micro-steps:**
- Read current ROADMAP.md to understand structure
- List all context graph files (.cnogo/scripts/context/)
- Add a Context Graph section covering: phases (storage, proximity, heritage, flows), graph DB, indexing hooks
- Reference the resolver agent documentation gap

**TDD:**
- required: `false`
- reason: Documentation-only change

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 2: Add graph config and fix debug composition in WORKFLOW.json
**Files:** `docs/planning/WORKFLOW.json`
**Action:**
Add a 'graph' section to WORKFLOW.json with: dbPath (.cnogo/graph.db), venvPath (.cnogo/.venv), indexOnCommit (true). Review the debug composition and differentiate debugger entries if they are identical. Extend cascadePatterns to include shell/markdown/json if currently Python-only.

**Micro-steps:**
- Read current WORKFLOW.json to understand structure
- Add a 'graph' config section with db path, venv path, index-on-commit toggle
- Fix debug composition if it has 3 identical debuggers
- Add cascadePatterns for common non-Python file types

**TDD:**
- required: `false`
- reason: Configuration-only change — validated by JSON parse and workflow_validate.py

**Verify:**
```bash
python3 -c "import json; json.load(open('docs/planning/WORKFLOW.json'))"
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Expand secret redaction patterns in workflow_hooks.py
**Files:** `.cnogo/scripts/workflow_hooks.py`
**Action:**
Find the secret redaction patterns in workflow_hooks.py and add: Bearer token pattern (Bearer [A-Za-z0-9._-]+), PEM block detection (-----BEGIN.*PRIVATE KEY-----), and long base64 string pattern (strings > 40 chars of [A-Za-z0-9+/=]). Keep patterns conservative to avoid false positives.

**Micro-steps:**
- Find the secret redaction code in workflow_hooks.py
- Add patterns for: Bearer tokens, PEM block headers, base64-encoded secrets (long base64 strings)
- Run py_compile to verify

**TDD:**
- required: `false`
- reason: Regex pattern addition — verified by py_compile; no test infrastructure for hook secret scanning

**Verify:**
```bash
python3 -m py_compile .cnogo/scripts/workflow_hooks.py
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
docs(workflow): ROADMAP graph coverage, WORKFLOW.json graph config, expanded secret patterns
```
