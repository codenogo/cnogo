# Spawn: $ARGUMENTS
<!-- effort: medium -->

Launch a specialized subagent for focused work with isolated context.

## Arguments

`/spawn <specialization> <task>`

## Available Specializations

| Specialization | Focus Area | Agent Definition | Best For |
|----------------|------------|------------------|----------|
| `security` | Security analysis | `.claude/agents/security-scanner.md` | Vulnerability audits, auth review, secrets scanning |
| `tests` | Test generation | `.claude/agents/test-writer.md` | Unit tests, integration tests, coverage gaps |
| `docs` | Documentation | `.claude/agents/docs-writer.md` | README, API docs, code comments, wikis |
| `perf` | Performance | `.claude/agents/perf-analyzer.md` | Profiling, optimization, benchmarks |
| `api` | API design | `.claude/agents/api-reviewer.md` | Endpoint review, schema validation, contracts |
| `refactor` | Code quality | `.claude/agents/refactorer.md` | Dead code, duplication, patterns |
| `migrate` | Migrations | `.claude/agents/migrate.md` | Framework updates, dependency upgrades |
| `review` | Code review | `.claude/agents/code-reviewer.md` | PR review, best practices, style |

## Agent Definitions

Each specialization maps to a persistent agent definition in `.claude/agents/`. These agents have:

- **Tiered model routing**: haiku (fast scanning), sonnet (analysis), inherit/opus (implementation)
- **Persistent memory**: Agents accumulate project knowledge across sessions (`.claude/agent-memory/`)
- **Tool restrictions**: Read-only agents can't modify code; implementation agents get full access
- **Focused system prompts**: Each agent has domain expertise from `docs/skills.md`

### Specialization → Agent Mapping

| /spawn shorthand | Agent name | Model | Memory |
|------------------|-----------|-------|--------|
| `security` | `security-scanner` | sonnet | project |
| `tests` | `test-writer` | inherit | project |
| `docs` | `docs-writer` | haiku | none |
| `perf` | `perf-analyzer` | sonnet | project |
| `api` | `api-reviewer` | sonnet | project |
| `refactor` | `refactorer` | inherit | project |
| `migrate` | `migrate` | inherit | project |
| `review` | `code-reviewer` | sonnet | project |

### Direct Invocation

Users can also invoke agents directly without /spawn:

```
Use the code-reviewer agent to review my changes
Have the security-scanner agent audit the auth module
Ask the debugger agent to investigate this error
```

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

### Step 2: Resolve Agent Definition

Look up the specialization in the mapping table above and find the corresponding `.claude/agents/<name>.md` file.

- If the agent definition file exists: delegate to that agent (preferred — it has model routing, memory, and focused prompts)
- If the agent definition file does NOT exist: fall back to the inline profiles below

### Step 3: Launch Subagent

**Primary path (agent definitions exist):**

Delegate to the matching `.claude/agents/<name>.md` agent. The Task tool will use the agent's configured model, tools, memory, and system prompt automatically.

**Fallback path (inline profiles — for projects without .claude/agents/):**

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

### Step 4: Report Launch

```markdown
## Subagent Spawned

**Type:** [specialization]
**Agent:** [agent-name from .claude/agents/ or "inline fallback"]
**Task:** [task description]
**Model:** [haiku/sonnet/inherit]
**Status:** Running

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

# Code review
/spawn review Check the latest changes for quality issues
```

## Output

- Confirmation of subagent launch
- Which agent definition was used (or fallback)
- Expected output location
- Instructions to check status
