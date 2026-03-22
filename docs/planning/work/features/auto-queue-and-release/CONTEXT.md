# Context: auto-queue-and-release

## Key Files

- `.cnogo/scripts/workflow/orchestration/dispatcher.py` — main integration point
- `.cnogo/scripts/workflow/orchestration/lane.py` — release_feature_lane()
- `.cnogo/scripts/workflow/orchestration/work_order.py` — sync_work_order() for auto-queue
- `docs/planning/work/ideas/*/SHAPE.json` — source of ready candidates
