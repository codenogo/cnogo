# Plan 01: Create the ship draft engine that computes commit surface (with hardcoded exclude patterns), generates commit message from plan contracts, and generates terse deterministic PR body from plan/summary/review artifacts.

## Goal
Create the ship draft engine that computes commit surface (with hardcoded exclude patterns), generates commit message from plan contracts, and generates terse deterministic PR body from plan/summary/review artifacts.

## Profile
`feature-delivery`

## Tasks

### Task 1: Create ship_draft.py module
**Files:** `.cnogo/scripts/workflow/orchestration/ship_draft.py`
**Context links:**
- D1
- D2
- D3
- D5
- D8
**Action:**
Create the ship draft module with: SHIP_EXCLUDE_PATTERNS constant for runtime-only paths (.cnogo/runs/, .cnogo/work-orders/ except .gitkeep, .cnogo/feature-phases.json, .cnogo/watch/, .cnogo/worktree-session.json); compute_commit_surface(root, feature) that unions task files[] from delivery run plans with planning artifact paths and tests, excludes SHIP_EXCLUDE_PATTERNS, and falls back to git diff --name-only detection via subprocess; generate_commit_message(root, feature) that reads latest plan commitMessage field; generate_pr_body(root, feature) that composes terse ## Summary / ## Test Plan / ## Review / ## Planning References / ## Follow-ups (only on warn verdict); build_ship_draft(root, feature) that composes all into a single dict with commitSurface[], excludedFiles[], commitMessage, prTitle, prBody, branch, and gitAddCommand.

**Micro-steps:**
- Add imports and module docstring — stdlib only (json, pathlib, typing, subprocess, re, fnmatch)
- Define SHIP_EXCLUDE_PATTERNS as a tuple of path prefixes/patterns for runtime-only files
- Implement _read_json(path) helper for safe JSON loading
- Implement _is_excluded(path, patterns) checking if a file path matches any exclude pattern
- Implement _load_plan_files(root, feature) collecting task files[] from all plan JSONs in the feature directory
- Implement _load_planning_artifacts(root, feature) listing all files under docs/planning/work/features/<slug>/
- Implement _load_changed_files(root) calling git diff --name-only main...HEAD as fallback via subprocess
- Implement compute_commit_surface(root, feature) unioning plan files + planning artifacts + changed tests, filtering through exclude patterns, returning sorted deduplicated list
- Implement generate_commit_message(root, feature) reading latest plan commitMessage, falling back to derived conventional commit
- Implement generate_pr_body(root, feature) composing terse bullet sections from plan goals, SUMMARY.json verification, REVIEW.json verdict/reviewers, artifact paths; adding Follow-ups only on warn verdict or open review items
- Implement build_ship_draft(root, feature) composing all helpers into a single dict with gitAddCommand convenience
- Error path: handle missing plan/summary/review gracefully — return partial draft with warnings
- Error path: handle subprocess failure in _load_changed_files (not in a git repo, no main branch)

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_ship_draft.py -v`
- passingVerify:
  - `python3 -m pytest tests/test_ship_draft.py -v`

**Verify:**
```bash
PYTHONPATH=.cnogo python3 -c "from scripts.workflow.orchestration.ship_draft import build_ship_draft, compute_commit_surface, generate_pr_body, generate_commit_message; print('import ok')"
python3 -m pytest tests/test_ship_draft.py -v
```

**Done when:** [Observable outcome]

### Task 2: Write comprehensive tests for ship draft
**Files:** `tests/test_ship_draft.py`
**Context links:**
- D1
- D2
- D3
- D8
**Action:**
Write tests covering: SHIP_EXCLUDE_PATTERNS correctly filters runtime paths; _is_excluded matches prefixes and patterns; compute_commit_surface includes plan files, planning artifacts, and excludes runtime state; generate_commit_message reads plan commitMessage and falls back correctly; generate_pr_body produces correct sections with bullets, includes Follow-ups only on warn; build_ship_draft returns complete dict with all fields including gitAddCommand; error paths for missing artifacts.

**Micro-steps:**
- Set up test fixtures: tmp_path with plan JSONs, SUMMARY.json, REVIEW.json, feature directory, .cnogo/work-orders/ files
- Test SHIP_EXCLUDE_PATTERNS contains all required runtime paths from D1
- Test _is_excluded correctly matches .cnogo/runs/, .cnogo/work-orders/foo.json, .cnogo/feature-phases.json, .cnogo/watch/
- Test _is_excluded does NOT match .cnogo/work-orders/.gitkeep
- Test compute_commit_surface includes task files from plans and planning artifacts
- Test compute_commit_surface excludes runtime state files
- Test generate_commit_message reads commitMessage from latest plan
- Test generate_commit_message falls back to derived message when commitMessage missing
- Test generate_pr_body produces ## Summary, ## Test Plan, ## Review, ## Planning References sections
- Test generate_pr_body adds ## Follow-ups only when REVIEW.json verdict is warn
- Test generate_pr_body omits ## Follow-ups when verdict is pass
- Test build_ship_draft returns commitSurface, excludedFiles, commitMessage, prTitle, prBody, branch, gitAddCommand
- Error path: missing SUMMARY.json produces partial draft with warnings
- Error path: missing REVIEW.json produces partial draft with warnings

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_ship_draft.py -v --tb=short`
- passingVerify:
  - `python3 -m pytest tests/test_ship_draft.py -v --tb=short`

**Verify:**
```bash
python3 -m pytest tests/test_ship_draft.py -v --tb=short
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_ship_draft.py -v
PYTHONPATH=.cnogo python3 -c "from scripts.workflow.orchestration.ship_draft import build_ship_draft, compute_commit_surface, generate_pr_body, generate_commit_message; print('public API ok')"
```

## Commit Message
```
feat(workflow): add ship draft engine

Add ship_draft.py module that computes commit surface with
hardcoded runtime exclusions, generates commit messages from
plan contracts, and produces terse deterministic PR bodies
from plan/summary/review artifacts.
```
