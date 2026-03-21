# Plan 01: Create the core initiative rollup engine that reads SHAPE.json, feature directories, and Work Orders to produce a live initiative-level status view with unified status mapping, shapeFeedback aggregation, reviewVerdict per feature, and initiative-level next actions.

## Goal
Create the core initiative rollup engine that reads SHAPE.json, feature directories, and Work Orders to produce a live initiative-level status view with unified status mapping, shapeFeedback aggregation, reviewVerdict per feature, and initiative-level next actions.

## Profile
`feature-delivery`

## Tasks

### Task 1: Create initiative_rollup.py module
**Files:** `.cnogo/scripts/workflow/orchestration/initiative_rollup.py`
**Context links:**
- D1
- D2
- D5
- D6
- D7
**Action:**
Create the initiative rollup module with: build_initiative_rollup(root, shape_path) -> dict that reads a SHAPE.json, resolves each candidateFeature to its unified status by checking for FEATURE.json stubs, CONTEXT.json, PLAN files, and Work Orders; collects reviewVerdict (pending|pass|warn|fail) from Work Order review_summary; aggregates shapeFeedback[] from child CONTEXT.json files; computes initiative-level next action based on feature statuses and recommendedSequence; returns a structured dict with initiative metadata, per-feature rollup entries, aggregated feedback, and next action. Also add list_initiatives(root) -> list[dict] that scans docs/planning/work/ideas/ for SHAPE.json files and returns a summary per initiative.

**Micro-steps:**
- Add imports and module docstring — stdlib only (json, pathlib, typing)
- Define INITIATIVE_ROLLUP_STATUSES constant merging SHAPE candidate statuses with Work Order statuses
- Implement _read_json(path) helper for safe JSON loading
- Implement _derive_feature_status(root, slug) that checks artifact progression: no FEATURE.json -> shape candidate status, FEATURE.json -> discuss-ready, CONTEXT.json -> discussing, PLAN exists -> planned, Work Order exists -> WO status
- Implement _review_verdict(work_order_dict) extracting compact verdict from review_summary
- Implement _collect_shape_feedback(root, candidate_slugs) scanning child CONTEXT.json files for shapeFeedback[] entries
- Implement _compute_next_initiative_action(features_rollup, recommended_sequence) returning a prescriptive next action dict
- Implement build_initiative_rollup(root, shape_path) composing all helpers into a complete rollup dict
- Implement list_initiatives(root) scanning ideas/ for SHAPE.json files
- Error path: handle missing/corrupt SHAPE.json gracefully — return error dict instead of raising
- Error path: handle missing/corrupt Work Order JSON gracefully — default to artifact-based status

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_initiative_rollup.py -v`
- passingVerify:
  - `python3 -m pytest tests/test_initiative_rollup.py -v`

**Verify:**
```bash
python3 -c "from scripts.workflow.orchestration.initiative_rollup import build_initiative_rollup, list_initiatives; print('import ok')"
python3 -m pytest tests/test_initiative_rollup.py -v
```

**Done when:** [Observable outcome]

### Task 2: Write comprehensive tests for initiative rollup
**Files:** `tests/test_initiative_rollup.py`
**Context links:**
- D1
- D2
- D5
- D6
**Action:**
Write tests covering: unified status mapping for all artifact progression states (draft, discuss-ready, discussing, planned, implementing, reviewing, shipping, blocked, completed, cancelled); reviewVerdict extraction (pending, pass, warn, fail); shapeFeedback aggregation from multiple child CONTEXT.json files; initiative-level next action computation; list_initiatives scanning; error paths for missing/corrupt SHAPE.json and Work Order files; edge cases (empty candidateFeatures, no Work Orders, shape with no features started).

**Micro-steps:**
- Set up test fixtures: create tmp_path-based SHAPE.json with candidateFeatures, feature directories with various artifact combinations
- Test _derive_feature_status for each status tier: no FEATURE.json = shape status, FEATURE.json only = discuss-ready, CONTEXT.json = discussing, PLAN = planned, Work Order present = WO status
- Test cancelled Work Order status stays cancelled (not mapped to parked) — decision D2
- Test _review_verdict extraction from Work Order review_summary for each verdict value
- Test _collect_shape_feedback aggregation from multiple CONTEXT.json files with mixed string/object feedback
- Test _compute_next_initiative_action respecting blocked > shipping > reviewing > implementing > planned > draft priority
- Test build_initiative_rollup end-to-end with a realistic SHAPE.json + mixed feature states
- Test list_initiatives with zero, one, and multiple SHAPE.json files
- Error path: test graceful handling of corrupt SHAPE.json (invalid JSON)
- Error path: test graceful handling of missing Work Order directory

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_initiative_rollup.py -v --tb=short`
- passingVerify:
  - `python3 -m pytest tests/test_initiative_rollup.py -v --tb=short`

**Verify:**
```bash
python3 -m pytest tests/test_initiative_rollup.py -v --tb=short
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_initiative_rollup.py -v
python3 -c "from scripts.workflow.orchestration.initiative_rollup import build_initiative_rollup, list_initiatives; print('public API ok')"
```

## Commit Message
```
feat(workflow): add initiative rollup engine

Add initiative_rollup.py module that computes live rollups from
SHAPE.json, feature directories, and Work Orders with unified
status mapping, reviewVerdict per feature, shapeFeedback
aggregation, and initiative-level next actions.
```
