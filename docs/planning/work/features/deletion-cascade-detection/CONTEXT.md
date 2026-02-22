# Context: Deletion Cascade Detection

**Date:** 2026-02-22 | **Status:** Discussed, ready for plan

## Problem

When a plan deletes files, callers throughout the codebase may still reference removed symbols/modules. Plan 02 of `architecture-refresh-2026` demonstrated this: task scopes covered the deleted files and direct importers, but 13 caller files (-152 LOC) required a manual leader sweep. The workflow has no mechanism to detect or prevent this.

## Solution

Enhance `bridge.py` to auto-detect and expand file scopes when plans involve file deletions.

## Decisions

### 1. Detection: Explicit `deletions` field

Plan tasks gain an optional `deletions: ["path/to/file.py"]` array listing files being deleted. No heuristic parsing of action text.

```json
{
  "name": "Delete aspirational modules",
  "files": ["src/context/graphrag.py", "src/context/semantic.py"],
  "deletions": ["src/context/graphrag.py", "src/context/semantic.py"],
  "action": "Delete these 4 aspirational files",
  "verify": ["pytest -q"]
}
```

### 2. Expansion: Auto-expand next task's scope

In `plan_to_task_descriptions()`, after building all TaskDescV2 entries, run a post-pass:
1. For each task with `deletions`, scan the repo for files referencing those modules
2. Filter out files already covered by ANY task's `file_scope.paths`
3. Add uncovered callers to the next task's `file_scope.paths` and `auto_expanded_paths`

### 3. Scanning: Configurable per-language patterns

WORKFLOW.json gains a `cascadePatterns` section:

```json
{
  "cascadePatterns": [
    {
      "glob": "*.py",
      "importPattern": "(?:from|import)\\s+{module}"
    },
    {
      "glob": "*.{ts,tsx,js,jsx}",
      "importPattern": "(?:import|require).*['\"].*{module}['\"]"
    }
  ]
}
```

`{module}` is replaced with the deleted file's module path (stem, dotted path, etc.). Bridge walks the repo with `pathlib.Path.rglob()` and matches with `re`.

### 4. Schema changes

- **Plan JSON task**: `+ deletions: string[]` (optional)
- **TaskDescV2**: `+ auto_expanded_paths: string[]` (bridge-generated, not in plan)
- **WORKFLOW.json**: `+ cascadePatterns: CascadePattern[]`

### 5. Validation

`workflow_validate_core.py` adds a warning when a task has `deletions` but is the last task in the plan (no subsequent task to receive expanded callers).

## Constraints

- Python stdlib only (pathlib + re for scanning)
- Stack-agnostic (patterns in WORKFLOW.json)
- Backwards compatible (plans without `deletions` work unchanged)
- Max 3 tasks per plan still holds (expansion, not creation)

## Open Questions

- Should auto-expanded paths be logged/reported to the leader?
- Default cascadePatterns to ship? (Python at minimum)
- Expansion target: strictly next task, or any task with partial caller coverage?
- Performance ceiling for stdlib scan on large repos?
