# Sync

Coordinate work across parallel sessions/checkouts.

## The Problem

With Boris Cherny's workflow, you have 5+ sessions running in parallel. Each has its own STATE.md. How do you know what's happening in your other checkouts without constantly switching terminals?

## Solution: Shared Sync File

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

## Your Task

When user runs `/sync`:

### Mode 1: `/sync` (View)

Show status of all known sessions:

```markdown
## 🔄 Session Sync

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

⚠️ Both `commhub-feature` and `commhub-refactor` are touching `src/services/notification.ts`
```

### Mode 2: `/sync update` (Push)

Update this session's status to the sync file:

1. Read current STATE.md
2. Extract key info (feature, status, branch)
3. Update sync file with this checkout's entry

### Mode 3: `/sync claim <file>` (Coordinate)

Claim a file to avoid conflicts:

```bash
echo "$(basename $(pwd)): $1 - $(date)" >> "$WORKFLOW_SYNC_FILE.locks"
```

### Mode 4: `/sync release <file>` (Release)

Release a claimed file.

## Output

### View Mode

Formatted table of all sessions with:
- Conflict warnings
- Stale session warnings (>4 hours no update)
- Suggested actions

### Update Mode

```
✅ Sync updated for [checkout-name]
```

## Notes

This is a lightweight coordination mechanism. For heavier coordination:
- Use GitHub issues/projects
- Use a proper task board
- Use git worktree tracking

The goal is just visibility, not enforcement.
