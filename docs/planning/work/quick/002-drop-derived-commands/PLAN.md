# Quick: Stop persisting commands.claim/report_done/context in TaskDesc V2 — derive them on-demand from task_id in consumers (generate_implement_prompt and implement.md)

## Goal
Stop persisting commands.claim/report_done/context in TaskDesc V2 — derive them on-demand from task_id in consumers (generate_implement_prompt and implement.md)

## Files
- `scripts/memory/bridge.py`
- `.claude/commands/implement.md`
- `tests/test_bridge.py`

## Approach
[Brief description]

## Verify
```bash
python3 -m py_compile scripts/memory/bridge.py
python3 -c "from scripts.memory.bridge import plan_to_task_descriptions, generate_implement_prompt; print('imports OK')"
python3 -c "from scripts.memory.bridge import TASK_DESC_SCHEMA_VERSION; assert TASK_DESC_SCHEMA_VERSION == 2"
python3 -m pytest tests/test_bridge.py -v
python3 scripts/workflow_validate.py
```
