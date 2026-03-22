# Feature: Execution Event Log

**Slug**: execution-event-log
**Parent Shape**: autonomous-execution-loop
**Priority**: P0

## User Outcome

Structured observability for the autonomous execution loop. Every layer writes events, CLI commands surface them.

## Scope

1. `execution_events.py` — `log_execution_event(actor, feature, event, data)` appends to `.cnogo/execution-log.jsonl`
2. `loop-status` CLI — reads lane JSON + execution log + heartbeat files into unified view
3. `loop-history` CLI — tails execution log with optional feature filter
4. Agent heartbeat format: `.cnogo/agent-heartbeat-task-<N>.json` with agentId, taskIndex, lastAction, updatedAt
