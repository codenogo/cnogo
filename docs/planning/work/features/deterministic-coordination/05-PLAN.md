# Plan 05: Add per-branch validation baseline with diff reporting (Contract 09)

## Goal
Add per-branch validation baseline with diff reporting (Contract 09)

## Tasks

### Task 1: Add baseline capture and storage to workflow_validate.py
**Files:** `.cnogo/scripts/workflow_validate.py`, `.cnogo/scripts/workflow_validate_core.py`, `.gitignore`
**Action:**
Add baseline infrastructure to workflow_validate.py. (1) Add a Warning dataclass or dict shape: {rule_id: str, file: str, line: int | None, message: str, signature: str} where signature = hash(rule_id + file + line_or_empty). (2) Refactor the existing validation logic so each warning produced during validation is captured as a structured Warning dict (in addition to the current print output). (3) Add save_baseline(warnings: list[dict], root: Path) that writes warnings to .cnogo/validate-baseline.json as JSON array, sorted by signature for determinism. (4) Add load_baseline(root: Path) -> list[dict] | None that reads .cnogo/validate-baseline.json, returns None if missing. (5) Add --save-baseline CLI flag that captures current warnings and saves them.

**Verify:**
```bash
python3 -m py_compile scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_validate.py --help 2>&1 | grep -q baseline || python3 .cnogo/scripts/workflow_validate.py 2>&1; echo "exit: $?"
```

**Done when:** [Observable outcome]

### Task 2: Add baseline diff and reporting
**Files:** `.cnogo/scripts/workflow_validate.py`, `.cnogo/scripts/workflow_validate_core.py`, `.gitignore`
**Action:**
Add diff_baselines(baseline: list[dict], current: list[dict]) -> dict function that compares by signature and returns {new: list[dict], resolved: list[dict], unchanged: list[dict]}. Add --diff-baseline CLI flag that: (1) Loads saved baseline, (2) Runs current validation to collect warnings, (3) Computes diff, (4) Prints report: '## Validation Diff' with sections for 'New warnings (N)', 'Resolved warnings (N)', 'Unchanged warnings (N)'. (5) Saves current as .cnogo/validate-latest.json. (6) Exit code: 0 if no new warnings, 1 if new warnings introduced. Also add a save after each successful validation run to .cnogo/validate-latest.json (so there's always a latest snapshot).

**Verify:**
```bash
python3 -m py_compile scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_validate.py --save-baseline 2>&1; python3 .cnogo/scripts/workflow_validate.py --diff-baseline 2>&1; echo "exit: $?"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m py_compile scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_validate.py
```

## Commit Message
```
feat(deterministic-coordination): add validation baseline with diff reporting
```
