# Quick: Verify install.sh copies all required files and gitignore entries; fix missing .cnogo/ gitignore entries

## Goal
Verify install.sh copies all required files and gitignore entries; fix missing .cnogo/ gitignore entries

## Files
- `install.sh`

## Approach
[Brief description]

## Verify
```bash
bash install.sh --help 2>&1 || true
python3 .cnogo/scripts/workflow_validate.py
```
