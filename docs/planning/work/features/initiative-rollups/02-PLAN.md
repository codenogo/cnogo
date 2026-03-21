# Plan 02: Wire the initiative rollup engine into the CLI (initiative-show, initiative-list subcommands) and update /status and /resume commands to automatically surface initiative context when a feature has a parentShape link.

## Goal
Wire the initiative rollup engine into the CLI (initiative-show, initiative-list subcommands) and update /status and /resume commands to automatically surface initiative context when a feature has a parentShape link.

## Profile
`feature-delivery`

## Tasks

### Task 1: Add initiative CLI subcommands to workflow_memory.py
**Files:** `.cnogo/scripts/workflow_memory.py`
**Context links:**
- D3
**Action:**
Add cmd_initiative_show and cmd_initiative_list functions plus argparse registration. initiative-show takes a shape slug, calls build_initiative_rollup, prints a compact table (feature | status | reviewVerdict | next action) and aggregated shapeFeedback. initiative-list calls list_initiatives and prints a summary table. Both support --json output.

**Micro-steps:**
- Import build_initiative_rollup and list_initiatives from orchestration.initiative_rollup
- Add cmd_initiative_show(args) — load root, resolve shape path from slug, call build_initiative_rollup, format output as table or JSON
- Add cmd_initiative_list(args) — call list_initiatives, format as table or JSON
- Register initiative-show and initiative-list in argparse subparsers block
- Add to command dispatch dict and read-only commands list
- Error path: initiative-show with non-existent slug prints error and exits 1

**TDD:**
- required: `true`
- failingVerify:
  - `python3 -m pytest tests/test_initiative_rollup_cli.py -v`
- passingVerify:
  - `python3 -m pytest tests/test_initiative_rollup_cli.py -v`

**Verify:**
```bash
python3 .cnogo/scripts/workflow_memory.py initiative-list --json 2>&1 | head -5
python3 -m pytest tests/test_initiative_rollup_cli.py -v
```

**Done when:** [Observable outcome]

### Task 2: Update /status command for initiative section
**Files:** `.claude/commands/status.md`
**Context links:**
- D4
**Action:**
Add a new Step 2.5 (between Git Status and Artifact Status) that detects parentShape in the current feature's CONTEXT.json or FEATURE.json. If found, run initiative-show with the shape slug and include a compact initiative section in the output showing: initiative name, progress (N/M completed), per-feature status line, pending shapeFeedback count, and initiative-level next action.

**Micro-steps:**
- Add Step 2.5: Initiative Context after Git Status step
- Detect parentShape from current feature CONTEXT.json or FEATURE.json via jq/python one-liner
- If parentShape exists, run initiative-show --json with the resolved slug
- Format compact initiative section: name, progress bar, per-feature status, feedback count, next action
- If no parentShape, skip silently — backward compatible per D4

**TDD:**
- required: `false`
- reason: Markdown command file — verified by workflow_validate.py and manual inspection

**Verify:**
```bash
grep -q 'initiative' .claude/commands/status.md
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

### Task 3: Update /resume command for initiative section
**Files:** `.claude/commands/resume.md`
**Context links:**
- D4
**Action:**
Add initiative context loading after the handoff/memory step. Same detection logic as /status: check parentShape in current feature artifacts, run initiative-show if found, include in the context summary alongside where-stopped and next-command.

**Micro-steps:**
- Add Step 1.5: Initiative Context after Load Handoff step
- Detect parentShape from current feature CONTEXT.json or FEATURE.json
- If parentShape exists, run initiative-show --json with the resolved slug
- Include initiative progress in the Step 5 Next summary: blocked features, pending feedback, initiative-level recommended action
- If no parentShape, skip silently

**TDD:**
- required: `false`
- reason: Markdown command file — verified by workflow_validate.py and manual inspection

**Verify:**
```bash
grep -q 'initiative' .claude/commands/resume.md
python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 -m pytest tests/test_initiative_rollup_cli.py -v
python3 .cnogo/scripts/workflow_validate.py
python3 .cnogo/scripts/workflow_memory.py initiative-list --json 2>&1 | head -5
```

## Commit Message
```
feat(workflow): add initiative rollup CLI and command integration

Wire initiative-show and initiative-list subcommands into the CLI.
Update /status and /resume commands to auto-surface initiative
context when a feature has a parentShape link.
```
