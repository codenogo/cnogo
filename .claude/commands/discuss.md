# Discuss: $ARGUMENTS
<!-- effort: medium -->

Deprecated compatibility entrypoint. New workflows should use `/shape`.

## Your Task

If a user invokes `/discuss`, treat it as a request to focus shaping on one feature inside the current or implied shape workspace.

1. Load the feature stub and any linked `SHAPE.json`.
2. Continue the readiness conversation inside shape, not as a separate lifecycle.
3. Persist or update `FEATURE.*` and `CONTEXT.*` for that feature.
4. Record any initiative follow-up as `shapeFeedback[]` in `CONTEXT.json` instead of editing `SHAPE.json` directly.
5. If the feature is now `ready`, queue it with `python3 .cnogo/scripts/workflow_memory.py work-sync <feature-slug>`.
6. Validate with `python3 .cnogo/scripts/workflow_validate.py`.

## Output

- clear note that `/discuss` is deprecated in favor of `/shape`
- updated feature-local decisions, constraints, and open questions
- any `shapeFeedback[]` that should flow back into the workspace
- confirmation of queue status when the feature becomes ready
