# Plan 09: Wire context graph into daily workflow: fix review blast-radius import, add PostCommit hook for auto-reindex, add graph-status CLI for plan workflow

## Goal
Wire context graph into daily workflow: fix review blast-radius import, add PostCommit hook for auto-reindex, add graph-status CLI for plan workflow

## Tasks

### Task 1: Fix _graph_impact_section() sys.path for review blast-radius
**Files:** `scripts/workflow_checks_core.py`, `tests/test_workflow_checks.py`
**Action:**
Add a test that invokes _graph_impact_section() with a temp repo containing Python files and asserts enabled=true. Fix the sys.path bug by inserting root into sys.path before 'from scripts.context import ContextGraph', following the exact pattern at lines 544-546 and 1912-1914 in the same file.

**Micro-steps:**
- Write test: call _graph_impact_section() on a repo with Python files and verify it returns enabled=true (not the 'No module named scripts' error)
- Run test to verify RED (import fails without sys.path fix)
- Add sys.path.insert(0, str(root)) before the ContextGraph import in _graph_impact_section()
- Run test to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_workflow_checks.py -x -k graph_impact`
- passingVerify:
  - `python3 -m pytest tests/test_workflow_checks.py -x -k graph_impact`

**Verify:**
```bash
python3 -m pytest tests/test_workflow_checks.py -x
```

**Done when:** [Observable outcome]

### Task 2: Add PostCommit hook for synchronous graph reindex
**Files:** `scripts/workflow_hooks.py`, `scripts/hook-post-commit-graph.sh`, `.claude/settings.json`, `tests/test_workflow_hooks_graph.py`
**Action:**
Create post_commit_graph() function in workflow_hooks.py that: (1) reads CLAUDE_TOOL_INPUT to detect git commit, (2) resolves repo root via git rev-parse, (3) imports ContextGraph and calls index(), (4) prints status message. Create hook-post-commit-graph.sh shell wrapper following hook-commit-confirm.sh pattern. Register in .claude/settings.json PostToolUse Bash hooks. Write tests verifying reindex works on temp repos.

**Micro-steps:**
- Write test: post_commit_graph() with a temp repo containing Python files runs incremental reindex and returns 0
- Write test: post_commit_graph() with no graph.db creates fresh index
- Write test: post_commit_graph() is idempotent (calling twice produces same result)
- Run tests to verify RED
- Implement post_commit_graph() in workflow_hooks.py: detect git commit in CLAUDE_TOOL_INPUT, import and run ContextGraph.index()
- Add post_commit_graph dispatch in main()
- Create hook-post-commit-graph.sh shell wrapper (follows hook-commit-confirm.sh pattern: extract command, detect git commit, call workflow_hooks.py post_commit_graph)
- Register new hook in .claude/settings.json PostToolUse Bash hooks array
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_workflow_hooks_graph.py -x`
- passingVerify:
  - `python3 -m pytest tests/test_workflow_hooks_graph.py -x`

**Verify:**
```bash
python3 -m pytest tests/test_workflow_hooks_graph.py -x
```

**Done when:** [Observable outcome]

### Task 3: Add graph-status CLI command for plan workflow integration
**Files:** `scripts/workflow_memory.py`, `tests/test_context_cli.py`
**Action:**
Add graph-status CLI subcommand that reports: (1) whether graph.db exists, (2) node/relationship counts, (3) number of stale files (files whose content hash differs from indexed hash), (4) last index timestamp. Supports --repo and --json flags. This gives /plan and /review workflows a fast staleness check before deciding to reindex.

**Micro-steps:**
- Write test: graph-status --help shows usage
- Write test: graph-status on empty repo reports no graph
- Write test: graph-status on indexed repo reports node count and freshness
- Write test: graph-status --json returns valid JSON with expected keys
- Run tests to verify RED
- Implement cmd_graph_status() handler: check if graph.db exists, report node count, check file hashes for staleness, output human or JSON
- Register graph-status in argparse + dispatch dict + _graph_cmds set
- Run tests to verify GREEN

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x -k TestGraphStatus`
- passingVerify:
  - `python3 -m pytest tests/test_context_cli.py -x -k TestGraphStatus`

**Verify:**
```bash
python3 -m pytest tests/test_context_cli.py -x -k TestGraphStatus
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_workflow_checks.py tests/test_workflow_hooks_graph.py tests/test_context_cli.py -x
python3 scripts/workflow_memory.py graph-status --help
```

## Commit Message
```
feat(context-graph): wire graph into workflow — fix review blast-radius, add PostCommit hook, add graph-status CLI
```
