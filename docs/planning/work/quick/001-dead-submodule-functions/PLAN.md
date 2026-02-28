# Quick: Delete scripts/memory/bridge.py and scripts/memory/ledger.py — both are entirely dead after __init__.py wrapper removal in workflow-dead-code-cleanup

## Goal
Delete scripts/memory/bridge.py and scripts/memory/ledger.py — both are entirely dead after __init__.py wrapper removal in workflow-dead-code-cleanup

## Files
- `.cnogo/scripts/memory/bridge.py`
- `.cnogo/scripts/memory/ledger.py`

## Approach
[Brief description]

## Verify
```bash
python3 -c "from scripts.memory import *; print('wildcard import OK')"
python3 -c "from scripts.memory import init, create, ready, claim, close, prime; print('core API OK')"
python3 .cnogo/scripts/workflow_validate.py
test ! -f scripts/memory/bridge.py
test ! -f scripts/memory/ledger.py
```
