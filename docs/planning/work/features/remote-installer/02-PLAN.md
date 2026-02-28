# Plan 02: Create remote-install.sh bootstrap script that installs cnogo from git with a one-liner

## Goal
Create remote-install.sh bootstrap script that installs cnogo from git with a one-liner

## Tasks

### Task 1: Create remote-install.sh at repo root
**Files:** `remote-install.sh`
**Action:**
Create remote-install.sh at repo root. The script: parses CLI args (target dir positional, --ref <tag/branch>, --update, --uninstall, --force), clones repo to mktemp -d (try SSH first via git@github.com:codenogo/workflowy.git, fall back to HTTPS), runs install.sh from the clone passing through lifecycle flags, and cleans up via trap EXIT. Must work on macOS and Linux. Handle clone failure gracefully with clear error message.

**Micro-steps:**
- Write the script header with usage/help text
- Implement CLI arg parsing: positional target dir, --ref, --update, --uninstall, --force
- Implement clone strategy: try git clone (SSH) first, fall back to HTTPS
- Implement install delegation: run install.sh from temp clone with passthrough args
- Implement trap EXIT cleanup to always remove temp dir
- Run bash -n syntax check

**TDD:**
- required: `false`
- reason: Bash bootstrap script — integration tested via dry-run verification, not unit-testable

**Verify:**
```bash
bash -n remote-install.sh
head -5 remote-install.sh | grep -q '#!/bin/bash'
grep -q 'trap' remote-install.sh
grep -q 'mktemp' remote-install.sh
grep -q 'install.sh' remote-install.sh
```

**Done when:** [Observable outcome]

### Task 2: Write integration test for remote-install.sh
**Files:** `tests/test_remote_install.py`
**Action:**
Write Python tests in tests/test_remote_install.py that verify: (1) bash -n passes, (2) --help/-h outputs usage text, (3) script is executable and has correct shebang. Use subprocess.run to invoke the script.

**Micro-steps:**
- Write test that verifies bash -n (syntax valid)
- Write test that verifies --help output contains usage info
- Write test that verifies script handles missing target dir gracefully
- Run tests to confirm all pass

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_remote_install.py -x -q --tb=short`
- passingVerify:
  - `python3 -m pytest tests/test_remote_install.py -x -q --tb=short`

**Verify:**
```bash
python3 -m pytest tests/test_remote_install.py -x -q --tb=short
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
bash -n remote-install.sh
python3 -m pytest tests/test_remote_install.py -x -q --tb=short
```

## Commit Message
```
feat(remote-installer): add remote-install.sh bootstrap script with tests
```
