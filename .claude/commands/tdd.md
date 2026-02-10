# TDD: $ARGUMENTS
<!-- effort: high -->

Test-driven development flow. Tests first, then implementation.

## Your Task

Implement "$ARGUMENTS" using TDD.

### Step 1: Understand Requirements

1. Read `docs/planning/PROJECT.md` for testing patterns
2. If feature has CONTEXT.md, read it for decisions
3. Identify expected inputs and outputs

### Step 2: Write Tests FIRST

Create comprehensive tests based on expected behaviour:

**Unit tests for:**
- Happy path (expected inputs → expected outputs)
- Edge cases (empty, null, boundary values)
- Error cases (invalid inputs → proper errors)

**Integration tests for:**
- API endpoints (request → response)
- Database operations (if applicable)
- External service calls (mocked)

### Step 3: Run Tests - Confirm They FAIL

```bash
# Stack-specific test commands
if [ -f pom.xml ]; then mvn test -Dtest=[TestClass]; fi
if [ -f package.json ]; then npm test -- --grep "[test name]"; fi
if [ -f pyproject.toml ]; then pytest -k "[test name]"; fi
```

**CRITICAL:** Tests MUST fail at this point. If they pass, either:
- Tests are wrong (not testing new functionality)
- Implementation already exists

Show the failing test output and STOP.

### Step 4: Wait for Approval

Present:
```
Tests written and failing as expected:

✗ should return user by ID
✗ should throw NotFound for missing user
✗ should validate email format

Proceed with implementation? (y/n)
```

**DO NOT write implementation until user approves.**

### Step 5: Implement (After Approval)

Write the minimum code to make tests pass:

1. Implement one test at a time
2. Run that test after each change
3. Refactor only after test passes
4. Move to next test

### Step 6: Verify All Tests Pass

```bash
# Run full test suite for affected code
```

### Step 7: Create Summary

Document what was built:

```markdown
# TDD Summary: $ARGUMENTS

## Tests Created

| Test | Purpose | Status |
|------|---------|--------|
| `should X` | [what it tests] | ✅ |

## Implementation

| File | Purpose |
|------|---------|
| `path/to/file` | [what it does] |

## Test Coverage

[Coverage report if available]

---
*Completed: [date]*
```

### Step 8: Commit

Two options:

**Option A: Single commit**
```bash
git add -A
git commit -m "feat([scope]): $ARGUMENTS

- Add tests for [feature]
- Implement [feature]"
```

**Option B: Separate commits (preferred for larger changes)**
```bash
git add tests/
git commit -m "test([scope]): add tests for $ARGUMENTS"

git add src/
git commit -m "feat([scope]): implement $ARGUMENTS"
```

## Output

- List of tests and their status
- Implementation summary
- Ready for `/review`
