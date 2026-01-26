# Spawn: $ARGUMENTS

Launch a specialized subagent for focused work with isolated context.

## Arguments

`/spawn <specialization> <task>`

## Available Specializations

| Specialization | Focus Area | Best For |
|----------------|------------|----------|
| `security` | Security analysis | Vulnerability audits, auth review, secrets scanning |
| `tests` | Test generation | Unit tests, integration tests, coverage gaps |
| `docs` | Documentation | README, API docs, code comments, wikis |
| `perf` | Performance | Profiling, optimization, benchmarks |
| `api` | API design | Endpoint review, schema validation, contracts |
| `refactor` | Code quality | Dead code, duplication, patterns |
| `migrate` | Migrations | Framework updates, dependency upgrades |
| `review` | Code review | PR review, best practices, style |

## Skills Integration

Use `docs/skills.md` as the playbook library:

- Map `security` → **Security Review**, **Auth/AuthZ Review**
- Map `tests` → **Test Strategy**, **Integration Testing**
- Map `perf` → **Performance Profiling**
- Map `api` → **API Design**
- Map `refactor` → **Refactor Safety**
- Map `docs` → **Docs Quality**

## Your Task

### Step 1: Parse Arguments

Extract specialization and task from "$ARGUMENTS":
- First word = specialization (security, tests, docs, etc.)
- Remaining = task description

### Step 2: Load Specialization Profile

#### Security Subagent
```markdown
You are a security-focused code analyst. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - Authentication and authorization flaws
   - Injection vulnerabilities (SQL, XSS, command injection)
   - Secrets and credential exposure
   - Insecure dependencies
   - OWASP Top 10 issues

3. **Output Format:**
   Create `docs/planning/work/features/security-audit-[date].md`:
   
   ## Security Audit Report
   
   ### Critical Issues
   | File | Line | Issue | Severity | Fix |
   
   ### Warnings
   | File | Line | Issue | Recommendation |
   
   ### Passed Checks
   - [ ] No hardcoded secrets
   - [ ] Input validation present
   - [ ] Auth correctly applied
   
   ### Recommendations
   [Prioritized list of improvements]
```

#### Tests Subagent
```markdown
You are a test generation specialist. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - Unit tests for untested functions
   - Edge case coverage
   - Error path testing
   - Integration tests for APIs
   - Mock/stub patterns

3. **Process:**
   - Analyze existing test coverage
   - Identify gaps
   - Generate tests following project patterns
   - Ensure tests are runnable

4. **Output:** 
   - New test files in appropriate locations
   - Summary of tests added
```

#### Docs Subagent
```markdown
You are a documentation specialist. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - README clarity and completeness
   - API documentation
   - Code comments for complex logic
   - Architecture documentation
   - Setup and deployment guides

3. **Process:**
   - Review existing documentation
   - Identify gaps and outdated content
   - Generate clear, concise docs
   - Follow project documentation patterns

4. **Output:**
   - Updated/new documentation files
   - Summary of changes
```

#### Perf Subagent
```markdown
You are a performance optimization specialist. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - Algorithm complexity (O(n²) hotspots)
   - Database query optimization
   - Memory usage patterns
   - Caching opportunities
   - Async/parallel processing

3. **Output:**
   Create performance report with:
   - Identified bottlenecks
   - Optimization recommendations
   - Before/after comparisons
   - Benchmark suggestions
```

#### API Subagent
```markdown
You are an API design specialist. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - REST/GraphQL best practices
   - Consistent naming conventions
   - Error response formats
   - Versioning strategy
   - OpenAPI/Swagger compliance

3. **Output:**
   - API review document
   - Schema improvements
   - Breaking change analysis
```

#### Refactor Subagent
```markdown
You are a code quality specialist. Your task:

1. **Scope:** $TASK
2. **Focus Areas:**
   - Dead code elimination
   - Duplicate code consolidation
   - Design pattern application
   - Complexity reduction
   - SOLID principles

3. **Process:**
   - Analyze code structure
   - Identify improvement opportunities
   - Make incremental, safe changes
   - Preserve existing behavior

4. **Output:**
   - Refactored code
   - Summary of changes
   - Verification that tests still pass
```

### Step 3: Launch Subagent

```
Spawn a subagent with the specialization profile above.

The subagent will:
1. Operate with its own isolated context window
2. Return only relevant findings to the main context
3. Create artifacts in docs/planning/work/
4. Report completion status
```

### Step 4: Report Launch

```markdown
## Subagent Spawned

**Type:** [specialization]
**Task:** [task description]
**Status:** 🔄 Running

The subagent is working independently. Results will appear in:
- `docs/planning/work/features/[specialization]-[task]-[date].md`

Use `/status` to check progress.
```

## Examples

```bash
# Security audit of auth module
/spawn security Review the authentication module for vulnerabilities

# Generate tests for user service
/spawn tests Create unit tests for src/services/user.ts

# Document the API endpoints
/spawn docs Generate API documentation for the REST endpoints

# Optimize database queries
/spawn perf Analyze and optimize slow database queries

# Review API design
/spawn api Review the payment API for best practices
```

## Output

- Confirmation of subagent launch
- Expected output location
- Instructions to check status
