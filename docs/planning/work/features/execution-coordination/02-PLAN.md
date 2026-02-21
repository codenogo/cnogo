# Plan 02: Update team.md and implement.md commands to use bridge + V2 contract, and clean up V1 artifacts

## Goal
Update team.md and implement.md commands to use bridge + V2 contract, and clean up V1 artifacts

## Tasks

### Task 1: Update team.md for V2 bridge integration
**Files:** `.claude/commands/team.md`
**Action:**
Rewrite the 'Action: implement' section of team.md:

1. Remove all ledger imports (line 37: from scripts.memory.ledger import create_ledger, generate_run_id, update_ledger). Replace with bridge imports.

2. Step 4: generate_run_id from bridge (not ledger):
   python3 -c "from scripts.memory.bridge import generate_run_id; print(generate_run_id('<feature>'))"

3. Step 5: Remove 'Create run ledger' — no ledger. Store run_id in worktree-session.json instead.

4. Step 6: Generate task descriptions via bridge, persist as V2 wrapper:
   python3 -c "import json; from scripts.memory.bridge import plan_to_task_descriptions; ..."
   Wrapper shape: {schema_version: 2, feature, plan_number, generated_at, tasks: TaskDescV2[]}
   Persist to .cnogo/task-descriptions-<feature>-<plan>.json

5. Step 8: create_session reads from V2 task descriptions.

6. Step 11: At spawn-time, call generate_implement_prompt(taskdesc) to render the markdown prompt for each implementer agent.

7. Remove all ledger phase updates (steps 9, 13, 18, 20). Phase tracking uses memory engine only (phase-get/phase-set).

8. Keep the try/finally structure but remove ledger references from the finally block.

**Verify:**
```bash
grep -c 'ledger' .claude/commands/team.md | grep -q '^0$'
grep -q 'generate_run_id' .claude/commands/team.md
grep -q 'schema_version' .claude/commands/team.md
grep -q 'generate_implement_prompt' .claude/commands/team.md
```

**Done when:** [Observable outcome]

### Task 2: Update implement.md for V2 bridge integration
**Files:** `.claude/commands/implement.md`
**Action:**
Update implement.md Step 3 (Execute Tasks) to use bridge:

1. Add a new Step 2d after Step 2c (Team Mode Routing): 'Bridge Validation'
   Call plan_to_task_descriptions() to validate and bootstrap:
   python3 -c "from scripts.memory.bridge import plan_to_task_descriptions; from pathlib import Path; tasks = plan_to_task_descriptions(Path('docs/planning/work/features/<feature>/<NN>-PLAN.json'), Path('.')); print(f'{len(tasks)} tasks loaded')"

2. Update Step 3 to iterate TaskDescV2 results instead of raw plan JSON:
   - Use task['action'] for the action text
   - Use task['file_scope']['paths'] for file constraints
   - Use task['commands']['verify'] for verification
   - Use task['commands']['claim'] for claiming memory ID
   - Use task['commands']['report_done'] for reporting done
   - Use task['task_id'] as the memory ID
   - Skip tasks where task['skipped'] is true

3. Update the TASK_DONE footer instruction to reference task['completion_footer'] directly.

4. Keep all other steps (0, 1, 2, 4-7) unchanged.

**Verify:**
```bash
grep -q 'plan_to_task_descriptions' .claude/commands/implement.md
grep -q 'file_scope' .claude/commands/implement.md
grep -q 'TaskDescV2\|task_id\|task.action\|completion_footer' .claude/commands/implement.md
```

**Done when:** [Observable outcome]

### Task 3: Delete V1 task-description artifacts
**Files:** `.cnogo/task-descriptions-compaction-resilience-01.json`, `.cnogo/task-descriptions-compaction-resilience-02.json`, `.cnogo/task-descriptions-compaction-resilience-03.json`, `.cnogo/task-descriptions-overstory-workflow-patterns-03.json`
**Action:**
Delete all old V1 task-descriptions-*.json files from .cnogo/. These use the V1 shape with the markdown description field and are no longer compatible with the V2 contract. Files to delete:
- .cnogo/task-descriptions-compaction-resilience-01.json
- .cnogo/task-descriptions-compaction-resilience-02.json
- .cnogo/task-descriptions-compaction-resilience-03.json
- .cnogo/task-descriptions-overstory-workflow-patterns-03.json

**Verify:**
```bash
test $(find .cnogo/ -name 'task-descriptions-*.json' 2>/dev/null | wc -l) -eq 0
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
grep -c 'ledger' .claude/commands/team.md | grep -q '^0$'
grep -q 'plan_to_task_descriptions' .claude/commands/implement.md
test $(find .cnogo/ -name 'task-descriptions-*.json' 2>/dev/null | wc -l) -eq 0
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(execution-coordination): update commands for V2 bridge contract, remove ledger, delete V1 artifacts
```
