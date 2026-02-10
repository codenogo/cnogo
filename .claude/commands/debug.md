# Debug: $ARGUMENTS
<!-- effort: max -->

Systematic debugging with persistent state tracking.

## Your Task

Debug the issue: "$ARGUMENTS"

### Step 1: Create Debug Session

Create `docs/planning/work/debug/[timestamp]-[slug]/SESSION.md`:

```markdown
# Debug Session: $ARGUMENTS

**Started:** [timestamp]
**Status:** 🔄 In Progress

## Problem Statement

[Restate the issue clearly]

## Symptoms

- [Observable symptom 1]
- [Observable symptom 2]

## Reproduction Steps

1. [Step to reproduce]
2. [Step to reproduce]
3. [Expected vs actual]
```

### Step 2: Gather Evidence

```bash
# Find related code
rg -n "[error message or keyword]" --type-add 'code:*.{java,ts,js,py,go}' -t code

# Check recent changes to likely files
git log -p --since="1 week ago" -- [suspected files]

# Check for similar issues
rg -n "TODO|FIXME|HACK|BUG" --type-add 'code:*.{java,ts,js,py,go}' -t code | head -20
```

Add findings to SESSION.md:

```markdown
## Evidence Gathered

### Related Code
| File | Line | Relevance |
|------|------|-----------|
| `path/file.ts` | 42 | [why relevant] |

### Recent Changes
| Commit | File | Change |
|--------|------|--------|
| abc123 | `file.ts` | [what changed] |

### Logs/Errors
```
[Any error output]
```
```

### Step 3: Form Hypotheses

Based on evidence, list possible causes:

```markdown
## Hypotheses

| # | Hypothesis | Likelihood | Test |
|---|------------|------------|------|
| 1 | [Possible cause] | High/Med/Low | [How to test] |
| 2 | [Possible cause] | High/Med/Low | [How to test] |
| 3 | [Possible cause] | High/Med/Low | [How to test] |
```

### Step 4: Test Hypotheses

For each hypothesis (highest likelihood first):

1. **Announce:** "Testing hypothesis N: [description]"
2. **Test:** Run the test described
3. **Record:** Result in SESSION.md

```markdown
## Investigation Log

### Hypothesis 1: [Description]
**Test:** [What was done]
**Result:** ✅ Confirmed | ❌ Ruled out | ⚠️ Inconclusive
**Notes:** [Observations]

### Hypothesis 2: [Description]
...
```

### Step 5: Identify Root Cause

Once confirmed:

```markdown
## Root Cause

**Confirmed hypothesis:** #N
**Explanation:** [Why this is happening]
**Location:** `path/to/file.ts:42`

## Impact Analysis

- [What else might be affected]
- [Related code that depends on this]
```

### Step 6: Propose Fix

```markdown
## Proposed Fix

### Option A: [Approach]
**Pros:** [Benefits]
**Cons:** [Drawbacks]
**Effort:** Low/Med/High

### Option B: [Approach]
**Pros:** [Benefits]
**Cons:** [Drawbacks]
**Effort:** Low/Med/High

### Recommendation
[Which option and why]
```

### Step 7: Implement Fix (with approval)

Ask user: "Implement fix Option [N]? (y/n)"

If yes:
1. Make the fix
2. Run tests
3. Verify the original issue is resolved
4. Update SESSION.md

```markdown
## Resolution

**Fix applied:** [Description]
**Commit:** `abc123f`
**Verified:** ✅ Issue no longer reproduces

## Prevention

[How to prevent this in future]
- [ ] Add test for this case
- [ ] Add validation
- [ ] Update documentation
```

### Step 8: Close Session

```markdown
**Status:** ✅ Resolved
**Duration:** [time spent]
**Resolved:** [timestamp]
```

## Output

- Root cause identified
- Fix applied (if approved)
- Prevention recommendations
