# Context: Graph Active Workflow Integration

**Feature:** `graph-active-workflow`
**Date:** 2026-02-28

## Problem

The context graph is well-integrated for **passive analysis** (`/review` blast radius, PostCommit reindexing, 11 CLI subcommands) but **underutilized for active workflow assistance**. The three core workflow commands — `/plan`, `/implement`, `/discuss` — operate without graph awareness:

| Command | Current State | Gap |
|---------|--------------|-----|
| `/plan` | File scope is manually authored | No suggestions from graph |
| `/implement` | Scope discipline is instruction-based only | No blast-radius validation |
| `/discuss` | Related code discovered via grep | No semantic graph queries |

## Why It Wasn't Integrated Earlier

1. **Build order** — The 10-phase pipeline had to be built first (13 plans). Passive integrations were natural first consumers.
2. **Commands are Markdown** — `/plan`, `/implement`, `/discuss` are `.claude/commands/*.md` templates. They can only call the graph via bash subcommands, unlike `/review` which has a Python function (`_graph_impact_section()`).
3. **Critical-path risk** — Active integrations affect the critical path. Failures during `/plan` would block planning. Graceful degradation needed careful design.

## Architecture Decision

New module: **`scripts/context/workflow.py`** with three public functions:

| Function | Consumer | Purpose |
|----------|----------|---------|
| `suggest_scope(repo_path, keywords, related_files, limit)` | `/plan` | Suggest which files each task should touch |
| `validate_scope(repo_path, declared_files, changed_files)` | `/implement` | Verify changes don't exceed declared scope |
| `enrich_context(repo_path, keywords, limit)` | `/discuss` | Discover related code semantically |

Each function:
- Auto-instantiates `ContextGraph` and indexes for freshness
- Gracefully degrades: returns `{"enabled": false, "error": "..."}` on failure
- Includes fuzzy edges (confidence <= 0.5) with `"low_confidence": true` warning label

Three new CLI subcommands in `workflow_memory.py`:
- `graph-suggest-scope` — wraps `suggest_scope()`
- `graph-validate-scope` — wraps `validate_scope()`
- `graph-enrich` — wraps `enrich_context()`

Markdown commands updated to call these at the right steps.

## Integration Points

### `/plan` — File Scope Suggestion (Step 2-3)

After loading CONTEXT.json, before authoring tasks:
```bash
python3 scripts/workflow_memory.py graph-suggest-scope --keywords "feature keywords" --files "known/files" --json
```

Returns suggested files with reasons and confidence levels. Feeds into task `files[]` authoring.

### `/implement` — Scope Validation (Step 3)

After each task execution, before claiming success:
```bash
python3 scripts/workflow_memory.py graph-validate-scope --declared "f1.py,f2.py" --changed "f1.py,f2.py,f3.py" --json
```

Returns scope violations, blast-radius analysis, and warnings about unintended side effects.

### `/discuss` — Context Enrichment (Step 2)

During context discovery, after grep search:
```bash
python3 scripts/workflow_memory.py graph-enrich --keywords "feature topic" --json
```

Returns related code with callers/callees/heritage, auto-populates `relatedCode[]` in CONTEXT.json.

## Constraints

- Python 3.10+ stdlib only
- Graceful degradation — graph failures never block workflow
- Auto-indexing — no manual `graph-index` required
- Must not modify existing `ContextGraph` class or phase modules
- All SQL parameterized

## Build Sequence

1. `/plan` file scope suggestion (highest value)
2. `/implement` scope validation
3. `/discuss` context enrichment

## Open Questions

- Should `suggest_scope()` weight recently-committed files higher than old ones?
- Should `validate_scope()` auto-expand declared scope or only warn on violations?
