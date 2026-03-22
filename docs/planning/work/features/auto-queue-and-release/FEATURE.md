# Feature: Auto-Queue from Shape and Auto-Release Lanes

**Slug**: auto-queue-and-release
**Parent Shape**: autonomous-execution-loop
**Priority**: P0

## User Outcome

No manual `work-sync` or lane management. Dispatcher auto-queues ready features from SHAPE.json and auto-releases completed lanes.

## Scope

1. `auto_queue_from_shape(root)` — scan all SHAPE.json, find ready candidates without Work Orders, create queued orders
2. `release_completed_lanes(root)` — find lanes where ship completed, release lane, clean up worktree
3. Wire both into `dispatch_ready_work()` — auto-queue before leasing, auto-release after
