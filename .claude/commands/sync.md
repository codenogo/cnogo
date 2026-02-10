# Sync
<!-- effort: medium -->

Coordinate work across parallel sessions/checkouts.

## The Problem

With Boris Cherny's workflow, you have 5+ sessions running in parallel. Each has its own STATE.md. How do you know what's happening in your other checkouts without constantly switching terminals?

## Step 0: Detect Mode

Before choosing a sync mode, detect the coordination environment:

1. **Check for Agent Teams**: Is `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set and are there active teammates?
   - If **Agent Teams active**: Use Modes 5-6 (shared task list + mailbox)
   - If **no Agent Teams**: Fall back to Modes 1-4 (manual sync file)

2. **Auto-detection logic**:
   - Read team config at `~/.claude/teams/*/config.json` to check for active teams
   - If a team exists with active members, prefer Agent Teams modes
   - Otherwise, use the manual sync file approach

## Choosing a Mode

| Scenario | Recommended Mode |
|----------|-----------------|
| Multiple local checkouts, no Agent Teams | Mode 1-4 (manual sync file) |
| Agent Teams active with teammates | Mode 5-6 (shared task list) |
| Quick status check | Mode 1 (view) or Mode 5 (team view) |
| Claiming files to prevent conflicts | Mode 3 (claim) |
| Messaging a specific teammate | Mode 6 (Agent Teams message) |
| Full team orchestration | Use `/team` instead |

## Solution A: Manual Sync File (Modes 1-4)

Use a sync file in a shared location (e.g., Dropbox, iCloud, or a dedicated repo).

### Step 1: Configure Sync Location

Set the sync file path. Options:

```bash
# Option A: Environment variable
export WORKFLOW_SYNC_FILE=~/Dropbox/workflow-sync.md

# Option B: Git repo (push/pull to share)
export WORKFLOW_SYNC_FILE=~/projects/workflow-sync/status.md

# Option C: Local file (single machine only)
export WORKFLOW_SYNC_FILE=~/.workflow-sync.md
```

Add to your shell profile (`.zshrc` or `.bashrc`).

### Step 2: Register This Session

```bash
# Get checkout identifier
CHECKOUT_NAME=$(basename $(pwd))
BRANCH=$(git branch --show-current)
FEATURE=$(grep -A1 "Current Focus" docs/planning/STATE.md 2>/dev/null | grep "Feature:" | cut -d: -f2 | xargs)

# Append to sync file
cat >> "$WORKFLOW_SYNC_FILE" << EOF

## $CHECKOUT_NAME
- **Branch:** $BRANCH
- **Feature:** $FEATURE
- **Status:** Active
- **Updated:** $(date -Iseconds)
EOF
```

### Step 3: Update Sync on Key Actions

After `/plan`, `/implement`, `/pause`:

```bash
CHECKOUT_NAME=$(basename $(pwd))
TIMESTAMP=$(date -Iseconds)
STATUS=$(grep -A5 "Current Focus" docs/planning/STATE.md 2>/dev/null)

# Update this checkout's entry in sync file
# (In practice, this would be a more sophisticated update)
echo "[$TIMESTAMP] $CHECKOUT_NAME: $STATUS" >> "$WORKFLOW_SYNC_FILE.log"
```

### Step 4: View All Sessions

Read the sync file:

```bash
cat "$WORKFLOW_SYNC_FILE"
```

## Solution B: Agent Teams (Modes 5-6)

When Agent Teams is active, coordination happens through the shared task list and mailbox system built into Claude Code.

## Your Task

When user runs `/sync`:

### Mode 1: `/sync` (View — Manual)

Show status of all known sessions:

```markdown
## Session Sync

### Active Sessions

| Checkout | Branch | Feature | Status | Last Update |
|----------|--------|---------|--------|-------------|
| commhub-main | main | - | Idle | 2 hours ago |
| commhub-feature | feat/websocket | websocket-notifications | Implementing Plan 02 | 5 min ago |
| commhub-bugfix | fix/token | - | PR open | 1 hour ago |
| commhub-tests | main | - | Writing tests | 30 min ago |

### Remote Sessions (claude.ai/code)

| Task | Status | Started |
|------|--------|---------|
| Implement retry logic | Running | 45 min ago |
| Add pagination | Complete | 1 hour ago |

### Conflicts

Both `commhub-feature` and `commhub-refactor` are touching `src/services/notification.ts`
```

### Mode 2: `/sync update` (Push — Manual)

Update this session's status to the sync file:

1. Read current STATE.md
2. Extract key info (feature, status, branch)
3. Update sync file with this checkout's entry

### Mode 3: `/sync claim <file>` (Coordinate — Manual)

Claim a file to avoid conflicts:

```bash
echo "$(basename $(pwd)): $1 - $(date)" >> "$WORKFLOW_SYNC_FILE.locks"
```

### Mode 4: `/sync release <file>` (Release — Manual)

Release a claimed file.

### Mode 5: `/sync` (View — Agent Teams)

When Agent Teams is detected, show the shared task list instead:

```markdown
## Agent Teams Sync

### Team: [team-name]

### Teammates

| Name | Agent | Status | Current Task |
|------|-------|--------|-------------|
| reviewer-1 | code-reviewer | Active | Reviewing auth module |
| security-1 | security-scanner | Idle | (waiting for assignment) |
| tester-1 | test-writer | Active | Writing integration tests |

### Task List

| ID | Task | Owner | Status | Blocked By |
|----|------|-------|--------|------------|
| 1 | Review auth module | reviewer-1 | in_progress | — |
| 2 | Security audit | security-1 | pending | — |
| 3 | Integration tests | tester-1 | in_progress | — |
| 4 | Merge and ship | — | pending | 1, 2, 3 |

### File Boundaries

| Teammate | Owns |
|----------|------|
| reviewer-1 | src/auth/ |
| tester-1 | tests/ |
```

Use TaskList to read the current task state. Read the team config at `~/.claude/teams/*/config.json` for teammate details.

### Mode 6: `/sync message <teammate> <msg>` (Message — Agent Teams)

Route a message to a teammate via the Agent Teams mailbox:

1. Parse teammate name and message from arguments
2. Use SendMessage to deliver
3. Confirm delivery

## Output

### Manual View Mode

Formatted table of all sessions with:
- Conflict warnings
- Stale session warnings (>4 hours no update)
- Suggested actions

### Manual Update Mode

```
Sync updated for [checkout-name]
```

### Agent Teams View Mode

Formatted table of teammates, task list, and file boundaries.

### Agent Teams Message Mode

```
Message delivered to [teammate-name]
```

## Notes

This is a lightweight coordination mechanism. For heavier coordination:
- Use `/team` for full Agent Teams orchestration (create, assign, dismiss)
- Use GitHub issues/projects for cross-repo coordination
- Use a proper task board for team-wide visibility

The goal is just visibility, not enforcement. `/sync` shows status; `/team` manages the team.
