# Background: $ARGUMENTS
<!-- effort: medium -->

Launch a fire-and-forget task that runs independently while you continue working.

## Arguments

`/background <task description>` — Start a background task
`/background status` — Check running background tasks
`/background cancel <id>` — Cancel a running task

## Your Task

### Step 1: Validate Task

Ensure the task is suitable for background execution:

**Good for background:**
- Large refactors across many files
- Test generation for entire modules
- Documentation generation
- Dependency updates and migrations
- Code analysis and audits

**Not suitable (needs interaction):**
- Tasks requiring clarification
- UI/UX decisions
- Architecture changes needing approval

### Step 2: Create Task Session

```bash
# Generate unique task ID
TASK_ID=$(date +%s | tail -c 6)
TASK_DIR="docs/planning/work/background"
mkdir -p "$TASK_DIR"

echo "🚀 Starting background task: $TASK_ID"
```

### Step 3: Create Task File

Create `docs/planning/work/background/$TASK_ID-TASK.md`:

```markdown
# Background Task: $TASK_ID

## Request
$ARGUMENTS

## Status
🔄 Running

## Started
[timestamp]

## Progress
- [ ] Analyzing request
- [ ] Planning approach
- [ ] Executing changes
- [ ] Verifying results
- [ ] Creating summary

## Log
[Execution log will be appended here]
```

### Step 4: Launch Background Agent

Using Claude's task tool for parallel execution:

```
Launch a subagent with the following task:

1. Read the task file at docs/planning/work/background/$TASK_ID-TASK.md
2. Execute the requested work: "$ARGUMENTS"
3. Update the task file with progress
4. When complete, change status to ✅ Complete
5. Create a summary of changes made

Important:
- Work independently without asking questions
- Make reasonable assumptions
- Document all decisions
- Commit changes with message: "background($TASK_ID): [description]"
```

### Step 4b: Memory Tracking (If Enabled)

If the memory engine is initialized (`.cnogo/memory.db` exists), create a tracking issue:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, create, claim
from pathlib import Path
root = Path('.')
if is_initialized(root):
    issue = create(
        '$ARGUMENTS',
        issue_type='background',
        labels=['background'],
        root=root,
    )
    claim(issue.id, actor='background-$TASK_ID', root=root)
    print(f'Memory issue: {issue.id}')
"
```

When the background task completes, close the memory issue:

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, close
from pathlib import Path
root = Path('.')
if is_initialized(root):
    close('<memoryId>', reason='completed', root=root)
"
```

### Step 5: Confirm Launch

```markdown
## Background Task Launched

**Task ID:** $TASK_ID
**Request:** $ARGUMENTS

The task is now running in the background.

### Check Status
```
/background status
```

### View Task Details
```
cat docs/planning/work/background/$TASK_ID-TASK.md
```

### Cancel Task
```
/background cancel $TASK_ID
```

You can continue working on other tasks. The background agent will update the task file with progress.
```

## If `status`:

```bash
echo "=== Background Tasks ==="
TASK_DIR="docs/planning/work/background"

if [ -d "$TASK_DIR" ]; then
    for task in "$TASK_DIR"/*-TASK.md; do
        if [ -f "$task" ]; then
            ID=$(basename "$task" | cut -d'-' -f1)
            STATUS=$(grep "^## Status" "$task" -A1 | tail -1)
            REQUEST=$(grep "^## Request" "$task" -A1 | tail -1 | head -c 60)
            echo "  [$ID] $STATUS - $REQUEST..."
        fi
    done
else
    echo "  No background tasks found"
fi
```

## If `cancel <id>`:

```bash
TASK_ID="$ARGUMENTS"
TASK_FILE="docs/planning/work/background/$TASK_ID-TASK.md"

if [ -f "$TASK_FILE" ]; then
    # Update status to cancelled
    export TASK_FILE
    python3 - << 'PY'
from pathlib import Path
import os

task_file = Path(os.environ["TASK_FILE"])
text = task_file.read_text(encoding="utf-8")
text = text.replace("🔄 Running", "❌ Cancelled")
task_file.write_text(text, encoding="utf-8")
PY
    echo "✅ Task $TASK_ID cancelled"
else
    echo "❌ Task $TASK_ID not found"
fi
```

## Output

- Task ID for tracking
- Instructions to check status
- Confirmation of launch
