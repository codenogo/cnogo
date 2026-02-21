# Overstory Pattern Adoptions

## Problem

Research into Overstory's swarm orchestration system identified patterns that cnogo would benefit from. Two major improvements (tiered merge, /doctor) already exist in the codebase. Four actionable gaps remain.

## Improvements

### 1. Named Failure Mode Rules (agents)

Add inline "Do NOT" rules to `implementer.md`, `debugger.md`, and `resolver.md`. Each agent gets 3-5 failure prevention lines based on its most common anti-patterns:

- **Implementer**: scope violation, premature done, TaskOutput misuse, silent failure
- **Debugger**: out-of-scope fixes, hypothesis-free debugging, scope creep during investigation
- **Resolver**: destructive resolution (dropping one side), incomplete staging, merge abort

Format: inline rules (team.md style), not named tables.

### 2. Propulsion Principle (agents)

Add "Execute immediately — do not ask for confirmation" to all three agent definitions. Prevents token-expensive approval loops. Quality gates (verify commands) are the checkpoint, not human approval.

### 3. Doctor Enhancement (git state check)

Add Check 6 to `_cmd_doctor()`: basic git health — dirty worktree detection, detached HEAD, stale local branches (merged into main but not deleted). Most common pre-work issue.

### 4. Merge Tier Logging (session-merge output)

`cmd_session_merge()` currently returns only success/failure. Add per-task `resolved_tier` values to the JSON output so post-run analysis can see how many conflicts were resolved mechanically (Tier 1 clean, Tier 2 auto-resolve) vs requiring the resolver agent.

## What Already Exists (no work needed)

- **Tiered merge**: `worktree.py:merge_session()` already has Tier 2 auto-resolve via `_check_disjoint_files()` + `_auto_resolve_keep_incoming()`
- **Doctor command**: `workflow_checks.py doctor` with 5 checks already implemented
- **Two-layer agent definitions**: `agents/*.md` + `bridge.py` prompt generation already in place

## Scope

- 3 agent `.md` files (add ~20 words each)
- 1 Python file: `workflow_checks_core.py` (add git state check ~30 lines)
- 1 Python file: `workflow_memory.py` (enhance `cmd_session_merge` JSON output ~10 lines)
