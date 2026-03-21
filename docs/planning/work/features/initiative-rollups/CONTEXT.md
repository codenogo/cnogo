# Context: Initiative Rollups

Turn SHAPE.json into a live initiative rollup over child features and Work Orders.

## Decisions

### D1: Live computation over persisted rollup

Rollup is computed on demand by reading SHAPE.json, feature directories, and Work Order files. No persisted initiative-rollup artifact.

**Rationale:** Initiatives have 3-10 candidate features. Reading a handful of JSON files is cheap. Persisting would introduce another sync mechanism and staleness risk.

### D2: Cancelled status preserved as-is

Work Order status `cancelled` is surfaced directly in the initiative view, not mapped to `parked`. `parked` means intentionally deferred before or outside execution; `cancelled` means work started and was abandoned.

### D3: New module in orchestration package

Code lives in `.cnogo/scripts/workflow/orchestration/initiative_rollup.py`. CLI subcommands (`initiative-show`, `initiative-list`) added to `workflow_memory.py`.

### D4: Automatic initiative section in /status and /resume

When the current feature has a `parentShape` link, `/status` and `/resume` include a compact initiative section by default. No flag needed.

### D5: Review outcome as compact reviewVerdict field

Per-feature review signal uses `reviewVerdict: pending|pass|warn|fail`. Full review findings not inlined.

### D6: Unified status mapping

| Artifact state | Derived status |
|---|---|
| No FEATURE stub | SHAPE candidate status (draft/parked/blocked) |
| FEATURE stub exists | discuss-ready |
| CONTEXT.json exists | discussing |
| PLAN exists, no WO | planned |
| Work Order exists | WO status (implementing/reviewing/shipping/blocked/completed/cancelled) |

### D7: Read-only on SHAPE.json

The rollup never writes to SHAPE.json. shapeFeedback is collected from child CONTEXT.json files and displayed as pending items. Only `/shape` writes to SHAPE.json.

## Constraints

- Python stdlib only
- Read-only on SHAPE.json
- Work Orders are source of truth for execution status
- Backward compatible — features without parentShape unaffected
- Validation coverage required

## Open Questions

- **Q1 (low):** Should initiative-list scan for orphaned features (parentShape pointing to deleted SHAPE.json)?
- **Q2 (medium):** Should initiative-level next action respect recommendedSequence ordering?

## Related Code

| File | Role |
|---|---|
| `.cnogo/scripts/workflow/orchestration/work_order.py` | Work Order model, build_work_order() |
| `.cnogo/scripts/workflow/validate/contracts_shape.py` | SHAPE.json validation |
| `.cnogo/scripts/workflow/validate/contracts_feature.py` | FEATURE.json + parentShape validation |
| `.cnogo/scripts/workflow/validate/common.py` | SHAPE_CANDIDATE_STATUSES |
| `.cnogo/scripts/workflow_memory.py` | CLI entrypoint for initiative-show/list |
| `.cnogo/scripts/workflow_render.py` | Rendering engine |
| `.claude/commands/status.md` | Needs initiative section |
| `.claude/commands/resume.md` | Needs initiative section |
| `.claude/commands/shape.md` | Creates SHAPE.json + FEATURE stubs |

---
*Generated: 2026-03-21*
