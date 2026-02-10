# Plan 01: Create 10 Custom Subagent Definitions

## Goal
Create all 10 `.claude/agents/*.md` files with frontmatter (model, tools, memory, skills) and focused system prompts.

## Prerequisites
- [x] CONTEXT.md decisions finalized
- [x] Agent table with model/tools/memory/skills defined

## Tasks

### Task 1: Create haiku-tier agents (explorer, docs-writer)
**Files:** `.claude/agents/explorer.md`, `.claude/agents/docs-writer.md`
**Action:**
Create 2 agents using `model: haiku` for fast, lightweight operations:

- **explorer**: Read-only codebase scanner. Tools: Read, Grep, Glob. No memory. No skills. System prompt: fast orientation, file discovery, pattern search. Description should say "use proactively" for automatic delegation.
- **docs-writer**: Documentation generator. Tools: Read, Write, Grep, Glob. No memory (docs regenerated from current state). Preload skill: Docs Quality. System prompt: README, API docs, code comments, architecture docs.

**Verify:**
```bash
ls -la .claude/agents/explorer.md .claude/agents/docs-writer.md
grep -c "^---" .claude/agents/explorer.md  # Should be 2 (frontmatter delimiters)
grep "model: haiku" .claude/agents/explorer.md .claude/agents/docs-writer.md
```

**Done when:** Both files exist with valid YAML frontmatter and markdown system prompts.

### Task 2: Create sonnet-tier agents (code-reviewer, security-scanner, perf-analyzer, api-reviewer)
**Files:** `.claude/agents/code-reviewer.md`, `.claude/agents/security-scanner.md`, `.claude/agents/perf-analyzer.md`, `.claude/agents/api-reviewer.md`
**Action:**
Create 4 agents using `model: sonnet` for analytical work:

- **code-reviewer**: Read-only code analysis. Tools: Read, Grep, Glob, Bash. Memory: project. Skills: Security Review, Refactor Safety. System prompt: quality, patterns, naming, error handling, test coverage. Mark "use proactively after code changes" in description.
- **security-scanner**: Vulnerability auditing. Tools: Read, Grep, Glob, Bash. Memory: project. Skills: Security Review, Auth/AuthZ Review. System prompt: OWASP Top 10, secrets, injection, auth flaws, dependency risk.
- **perf-analyzer**: Performance analysis. Tools: Read, Grep, Glob, Bash. Memory: project. Skills: Performance Profiling. System prompt: hotspots, O(n^2), N+1 queries, caching, memory, IO patterns.
- **api-reviewer**: API design review. Tools: Read, Grep, Glob, Bash. Memory: project. Skills: API Design. System prompt: contracts, naming, errors, pagination, versioning, idempotency.

**Verify:**
```bash
ls -la .claude/agents/code-reviewer.md .claude/agents/security-scanner.md .claude/agents/perf-analyzer.md .claude/agents/api-reviewer.md
grep "model: sonnet" .claude/agents/code-reviewer.md .claude/agents/security-scanner.md .claude/agents/perf-analyzer.md .claude/agents/api-reviewer.md
grep "memory: project" .claude/agents/code-reviewer.md .claude/agents/security-scanner.md .claude/agents/perf-analyzer.md .claude/agents/api-reviewer.md
```

**Done when:** All 4 files exist with sonnet model, project memory, and correct skill preloading.

### Task 3: Create inherit-tier agents (test-writer, debugger, refactorer, migrate)
**Files:** `.claude/agents/test-writer.md`, `.claude/agents/debugger.md`, `.claude/agents/refactorer.md`, `.claude/agents/migrate.md`
**Action:**
Create 4 agents using `model: inherit` (uses parent's model, typically opus) for implementation work:

- **test-writer**: Test generation and fixing. Tools: Read, Edit, Write, Bash, Grep, Glob. Memory: project. Skills: Test Strategy, Integration Testing. System prompt: unit/integration/regression tests, edge cases, error paths, mock patterns.
- **debugger**: Root cause analysis and fixing. Tools: Read, Edit, Bash, Grep, Glob. Memory: project. Skills: Debug Investigation, RCA. System prompt: reproduce, hypothesize, isolate, fix, verify. Mark "use proactively when encountering errors" in description.
- **refactorer**: Code quality improvement. Tools: Read, Edit, Write, Bash, Grep, Glob. Memory: project. Skills: Refactor Safety. System prompt: dead code, duplication, patterns, complexity reduction, behavior preservation.
- **migrate**: Framework/dependency upgrades. Tools: Read, Edit, Write, Bash, Grep, Glob. Memory: project. Skills: Data & Migrations. System prompt: backward compatibility, rollout plans, dependency updates, breaking changes.

**Verify:**
```bash
ls -la .claude/agents/test-writer.md .claude/agents/debugger.md .claude/agents/refactorer.md .claude/agents/migrate.md
grep "model: inherit" .claude/agents/test-writer.md .claude/agents/debugger.md .claude/agents/refactorer.md .claude/agents/migrate.md
grep "memory: project" .claude/agents/test-writer.md .claude/agents/debugger.md .claude/agents/refactorer.md .claude/agents/migrate.md
```

**Done when:** All 4 files exist with inherit model, project memory, and correct skill preloading.

## Verification

After all tasks:
```bash
ls .claude/agents/*.md | wc -l  # Should be 10
for f in .claude/agents/*.md; do echo "=== $f ==="; head -1 "$f"; done  # All start with ---
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(opus-46-agents-workflow-improvements): add 10 custom subagent definitions

- haiku: explorer, docs-writer (fast read-only)
- sonnet: code-reviewer, security-scanner, perf-analyzer, api-reviewer (analysis)
- inherit: test-writer, debugger, refactorer, migrate (implementation)
- persistent memory (project scope) for 8 of 10 agents
- skill preloading from docs/skills.md
```

---
*Planned: 2026-02-10*
