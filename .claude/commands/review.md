# Review
<!-- effort: high -->

Comprehensive quality gates before merge. Runs automated checks and structured manual review.

## Your Task

Review all changes for quality, security, and correctness.

### Rule: Persist Review Results

Always write a review artifact:

- If memory has an active feature (query: `list_issues(issue_type='epic', status='in_progress')`), write to:
  - `docs/planning/work/features/<feature>/REVIEW.md`
  - `docs/planning/work/features/<feature>/REVIEW.json`
- Otherwise write to:
  - `docs/planning/work/review/<timestamp>-REVIEW.md`
  - `docs/planning/work/review/<timestamp>-REVIEW.json`

### Monorepo/Polyglot Note

If `docs/planning/WORKFLOW.json` indicates (or you detect) a monorepo/polyglot repo, prefer **scoped** checks per package when possible:

- `cd packages/api && npm test`
- `npm --prefix packages/web run lint`
- `pnpm -C services/orders test`
- `mvn -f services/orders/pom.xml test`

If you run repo-root checks, call that out in the report as a limitation.

### Step 1: Identify Changes

```bash
echo "=== Changed Files ==="
git diff --name-only HEAD~1..HEAD 2>/dev/null || git diff --name-only

echo ""
echo "=== Uncommitted Changes ==="
git status --porcelain

echo ""
echo "=== Commits to Push ==="
git log origin/main..HEAD --oneline 2>/dev/null || echo "No remote tracking"
```

### Step 2: Run Automated Checks

#### 2.1 Linting

```bash
echo "🔍 Running linter..."

if [ -f pom.xml ]; then
    mvn spotless:check -q && echo "✅ Spotless passed" || echo "❌ Spotless failed"
    mvn checkstyle:check -q 2>/dev/null && echo "✅ Checkstyle passed" || echo "⚠️ Checkstyle skipped"
fi

if [ -f package.json ]; then
    npm run lint --silent 2>/dev/null && echo "✅ ESLint passed" || echo "❌ ESLint failed"
fi

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    ruff check . 2>/dev/null && echo "✅ Ruff passed" || python -m flake8 . 2>/dev/null && echo "✅ Flake8 passed" || echo "⚠️ No Python linter"
fi

if [ -f go.mod ]; then
    go vet ./... 2>/dev/null && echo "✅ go vet passed" || echo "❌ go vet failed"
    golangci-lint run 2>/dev/null && echo "✅ golangci-lint passed" || echo "⚠️ golangci-lint not installed"
fi
```

#### 2.2 Tests

```bash
echo ""
echo "🧪 Running tests..."

if [ -f pom.xml ]; then
    mvn test -q -DskipITs && echo "✅ Tests passed" || echo "❌ Tests failed"
fi

if [ -f package.json ]; then
    npm test --silent 2>/dev/null && echo "✅ Tests passed" || echo "❌ Tests failed"
fi

if [ -f pyproject.toml ] || [ -f setup.py ]; then
    pytest -q --tb=short 2>/dev/null && echo "✅ Tests passed" || echo "❌ Tests failed"
fi

if [ -f go.mod ]; then
    go test ./... -short && echo "✅ Tests passed" || echo "❌ Tests failed"
fi
```

#### 2.3 Security Scanning

```bash
echo ""
echo "🔒 Security scanning..."

# Secret detection — delegates to the shared hook script (single source of truth)
echo "Scanning for secrets..."
bash scripts/hook-pre-commit-secrets.sh || SECRETS_FOUND=1

# Dependency vulnerabilities
echo ""
echo "Scanning dependencies..."

if [ -f package.json ]; then
    npm audit --audit-level=high 2>/dev/null && echo "✅ npm audit passed" || echo "⚠️ npm vulnerabilities found"
fi

if [ -f pom.xml ] && command -v mvn &>/dev/null; then
    # OWASP dependency check (if plugin configured)
    mvn org.owasp:dependency-check-maven:check -q 2>/dev/null && echo "✅ OWASP check passed" || echo "⚠️ OWASP check skipped"
fi

if [ -f requirements.txt ] || [ -f pyproject.toml ]; then
    pip-audit 2>/dev/null && echo "✅ pip-audit passed" || echo "⚠️ pip-audit not installed"
fi

if [ -f go.mod ]; then
    govulncheck ./... 2>/dev/null && echo "✅ govulncheck passed" || echo "⚠️ govulncheck not installed"
fi

# SAST (if available)
echo ""
echo "Running SAST..."

if command -v semgrep &>/dev/null; then
    semgrep --config=auto --quiet . && echo "✅ Semgrep passed" || echo "⚠️ Semgrep findings"
else
    echo "⚠️ Semgrep not installed (recommended: pip install semgrep)"
fi
```

#### 2.4 Production Check (if MCP configured)

```bash
echo ""
echo "🔍 Checking production errors..."
if claude mcp list 2>/dev/null | grep -q "sentry"; then
    echo "Checking Sentry for related issues..."
    claude mcp use sentry query "issue.handled:no is:unresolved" 2>/dev/null && echo "ℹ️  Sentry check complete" || echo "⚠️ Sentry check failed"
fi
```

#### 2.5 Type Checking

```bash
echo ""
echo "📝 Type checking..."

if [ -f tsconfig.json ]; then
    npx tsc --noEmit && echo "✅ TypeScript check passed" || echo "❌ TypeScript errors"
fi

if [ -f pyproject.toml ] && grep -q "mypy" pyproject.toml 2>/dev/null; then
    mypy . 2>/dev/null && echo "✅ mypy passed" || echo "⚠️ mypy issues"
fi
```

### Step 2b: Package-Aware Execution (Recommended)

If `docs/planning/WORKFLOW.json` has `packages[]` with `commands`, run:

```bash
python3 scripts/workflow_checks.py review
```

This executes `lint/typecheck/test` per package and writes the review artifacts automatically.

### Step 3: Code Review Checklist

For each changed file, evaluate:

#### Security

| Check | Status |
|-------|--------|
| No hardcoded credentials | ⬜ |
| Input validation present | ⬜ |
| Output encoding (XSS prevention) | ⬜ |
| SQL injection prevention | ⬜ |
| Auth/authz correctly applied | ⬜ |
| Sensitive data not logged | ⬜ |
| HTTPS/TLS for external calls | ⬜ |

#### Code Quality

| Check | Status |
|-------|--------|
| Functions ≤50 lines | ⬜ |
| Clear, descriptive naming | ⬜ |
| No magic numbers/strings | ⬜ |
| Error handling present | ⬜ |
| Logging appropriate | ⬜ |
| No TODO without ticket | ⬜ |
| Consistent with patterns | ⬜ |

#### Testing

| Check | Status |
|-------|--------|
| Unit tests for new logic | ⬜ |
| Edge cases covered | ⬜ |
| Error cases tested | ⬜ |
| Integration tests (if API) | ⬜ |
| No flaky test patterns | ⬜ |

#### Cross-Cutting (if applicable)

| Check | Status |
|-------|--------|
| API contracts preserved | ⬜ |
| Database migrations reversible | ⬜ |
| Backward compatible | ⬜ |
| Feature flag for risky changes | ⬜ |
| Documentation updated | ⬜ |

#### Karpathy Checklist (Enforced)

Complete this section in the review report:

| Principle | Check |
|----------|-------|
| Think Before Coding | Assumptions clarified / tradeoffs surfaced |
| Simplicity First | No unnecessary abstractions / minimal solution |
| Surgical Changes | No drive-by refactors / diff matches intent |
| Goal-Driven Execution | Verifiable success criteria met (tests/commands) |

### Step 4: Generate Review Report

```markdown
## Review Report

**Date:** [timestamp]
**Branch:** [branch]
**Reviewer:** Claude

### Automated Checks

| Check | Result |
|-------|--------|
| Linting | ✅ Passed / ❌ Failed |
| Tests | ✅ Passed / ❌ Failed |
| Security Scan | ✅ Passed / ⚠️ Warnings |
| Type Check | ✅ Passed / ❌ Failed |
| Dependency Audit | ✅ Passed / ⚠️ Vulnerabilities |

### Issues Found

#### ❌ Blockers (must fix)

| File | Line | Issue | Severity |
|------|------|-------|----------|
| `path/file.ts` | 42 | [Issue description] | Critical |

#### ⚠️ Warnings (should fix)

| File | Line | Issue | Severity |
|------|------|-------|----------|
| `path/file.ts` | 15 | [Issue description] | Medium |

#### 💡 Suggestions (optional)

| File | Line | Suggestion |
|------|------|------------|
| `path/file.ts` | 28 | [Improvement idea] |

### Manual Review Notes

[Notes from code review checklist]

### Karpathy Checklist

| Principle | Status | Notes |
|----------|--------|------|
| Think Before Coding | ⬜ | |
| Simplicity First | ⬜ | |
| Surgical Changes | ⬜ | |
| Goal-Driven Execution | ⬜ | |

### Verdict

- ❌ **Not Ready** — Blockers must be addressed
- ⚠️ **Conditional** — Warnings should be reviewed
- ✅ **Ready to Ship** — All checks passed
```

Also create a machine-checkable contract (`REVIEW.json`) (minimal):

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per review: `REVIEW.md` + `REVIEW.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `timestamp`.
- **Verdict required**: `verdict` MUST be `pass|warn|fail`.
- **Validation**: run `python3 scripts/workflow_validate.py` after writing the review artifacts.

```json
{
  "schemaVersion": 1,
  "timestamp": "2026-01-24T00:00:00Z",
  "feature": "websocket-notifications (optional)",
  "branch": "feature/xyz",
  "automated": [
    { "name": "lint", "result": "pass|fail|skipped" },
    { "name": "tests", "result": "pass|fail|skipped" },
    { "name": "security", "result": "pass|warn|fail" },
    { "name": "types", "result": "pass|fail|skipped" },
    { "name": "deps", "result": "pass|warn|fail|skipped" }
  ],
  "verdict": "pass|warn|fail",
  "blockers": [{ "file": "path/file.ts", "line": 42, "issue": "...", "severity": "critical" }],
  "warnings": [{ "file": "path/file.ts", "line": 15, "issue": "...", "severity": "medium" }]
}
```

### Step 5: Decision

Based on findings:

**If blockers found:**
```
❌ Review Failed

Blockers found that must be addressed:
1. [Issue 1]
2. [Issue 2]

Run `/review` again after fixing.
```

**If warnings only:**
```
⚠️ Review Passed with Warnings

The following warnings were found:
1. [Warning 1]
2. [Warning 2]

Proceed to `/ship` anyway? (y/n)
```

**If clean:**
```
✅ Review Passed

All automated checks passed.
Manual review checklist completed.

Ready for `/ship`
```

## Output

- Automated check results
- Detailed findings with file/line references
- Clear verdict (block/warn/pass)
- Next action recommendation

Finally, run:

```bash
python3 scripts/workflow_validate.py
```
