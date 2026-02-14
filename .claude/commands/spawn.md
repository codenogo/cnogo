# Spawn: $ARGUMENTS
<!-- effort: medium -->

Launch a specialized subagent for focused work with isolated context.

## Arguments

`/spawn <specialization> <task>`

## Available Specializations

| Specialization | Skill Loaded | Best For |
|----------------|-------------|----------|
| `security` | `.claude/skills/security-scan.md` | Vulnerability audits, auth review |
| `tests` | `.claude/skills/test-writing.md` | Unit tests, integration tests |
| `perf` | `.claude/skills/perf-analysis.md` | Profiling, optimization |
| `api` | `.claude/skills/api-review.md` | API design review, contracts |
| `review` | `.claude/skills/code-review.md` | Code quality review |
| `refactor` | `.claude/skills/refactor-safety.md` | Safe refactoring, cleanup |
| `debug` | `.claude/agents/debugger.md` | Root cause analysis (full agent) |

## Your Task

### Step 1: Parse Arguments

Extract specialization and task from "$ARGUMENTS":
- First word = specialization (security, tests, perf, api, review, refactor, debug)
- Remaining = task description

### Step 2: Resolve Specialization

- If `debug` → use the `debugger` agent via Task tool with `subagent_type`
- All others → spawn a `general-purpose` subagent with the matching `.claude/skills/` file

### Step 3: Launch Subagent

Read the matching skill file, then spawn a Task with:
- `subagent_type`: `"general-purpose"` (or `"debugger"` for debug)
- `prompt`: Include the skill content as context + the user's task description

Example prompt structure:
```
Apply the following skill checklist to this task:

[skill file contents]

Task: [user's task description]
```

### Step 4: Report

```markdown
## Subagent Spawned

**Type:** [specialization]
**Skill:** [skill file path]
**Task:** [task description]
**Status:** Running

Results will appear when the subagent completes.
```

## Examples

```bash
/spawn security Review the auth module for vulnerabilities
/spawn tests Create unit tests for the memory engine
/spawn perf Analyze query performance in storage.py
/spawn review Check the latest changes for quality issues
/spawn debug Investigate why claims fail on closed tasks
```

## Output

- Confirmation of subagent launch
- Which skill was loaded
- Results when subagent completes
