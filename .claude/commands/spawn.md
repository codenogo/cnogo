# Spawn: $ARGUMENTS
<!-- effort: medium -->

Launch a focused subagent with specialization-specific guidance.

## Arguments

`/spawn <specialization> <task>`

Specializations:
- `security`
- `tests`
- `perf`
- `api`
- `review`
- `refactor`
- `debug`

## Your Task

1. Parse specialization and task text from `$ARGUMENTS`.
2. Resolve execution mode:
- `debug` -> debugger subagent type
- others -> `general-purpose` with matching skill file context
3. Load only the matching skill/agent instructions.
4. Spawn Task with prompt containing:
- role/specialization contract
- user task
- expected output format (findings, diffs, tests, risks)
5. Report launch status and track completion.

## Output

- Subagent type + loaded skill path
- Task summary
- Completion handoff with concrete results
