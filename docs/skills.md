# Claude Skills Library (Skills.md)

This file defines reusable “skills” (micro-playbooks + checklists) that Claude can apply consistently across projects and sessions.

## How to Use

- **Humans**: skim the skill names and use them to guide requests (“use the Security Review skill”).
- **Claude**: treat these as selectable playbooks. Prefer applying the smallest skill that fits.
- **Integration points**:
  - During `/discuss`: use relevant skills to surface decision points.
  - During `/implement`: use skills as execution checklists.
  - During `/review`: use Security/Testing/Perf skills.
  - With `/spawn`: map skills to subagent specializations (security/tests/docs/perf/api/refactor).

## Skill Index

- **Karpathy Principles (Claude Coding)**
- **Bug Triage**
- **Debug Investigation**
- **Root Cause Analysis (RCA)**
- **API Design**
- **Data & Migrations**
- **Security Review (OWASP)**
- **Auth/AuthZ Review**
- **Test Strategy**
- **Integration Testing**
- **Performance Profiling**
- **Refactor Safety**
- **Release Readiness**
- **Incident / Hotfix**
- **Docs Quality**

---

## Karpathy Principles (Claude Coding)

These principles are inspired by the repo [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) and are designed to reduce common LLM coding failure modes.

**Use these on every non-trivial task**, especially during `/plan`, `/implement`, and `/review`.

### 1) Think Before Coding

**Checklist**:
- State assumptions explicitly; if ambiguous, ask instead of guessing
- Surface tradeoffs and alternative interpretations before coding
- If confused, stop and clarify rather than “run with it”

### 2) Simplicity First

**Checklist**:
- Implement the minimum that solves the request
- Avoid speculative abstractions/config
- If 200 lines can be 50, simplify

### 3) Surgical Changes

**Checklist**:
- Touch only what the task requires
- Don’t refactor adjacent code “for fun”
- Clean up only the mess your change created (unused imports, etc.)

### 4) Goal-Driven Execution

**Checklist**:
- Define measurable success criteria per step
- Verify after each task (tests, commands, observable behavior)
- Loop until verified (don’t stop at “should work”)

---

## Bug Triage

**When**: user reports a bug; scope unclear.

**Checklist**:
- **Impact**: severity, affected users, prod vs dev, data loss risk
- **Repro**: steps, frequency, environment, inputs
- **Signals**: logs, metrics, Sentry/Jira context (via MCP if enabled)
- **Routing**:
  - Small + clear fix → `/quick`
  - Unclear cause or flaky → `/debug`
  - Multi-service / contract risk → `/discuss` → `/plan`

**Artifacts**: if non-trivial, use `/debug` to create a debug session doc.

---

## Debug Investigation

**When**: you need to systematically find the cause.

**Checklist**:
- Reproduce locally (or document why not)
- Identify the smallest failing scenario
- Add instrumentation (temporary logs) if needed
- Inspect recent changes (`git log -p`)
- Form hypotheses and test them in order
- Confirm root cause with evidence

**Exit criteria**: root cause identified + fix options enumerated.

---

## Root Cause Analysis (RCA)

**When**: incident or serious bug postmortem.

**Checklist**:
- Timeline (UTC), detection, mitigation, recovery
- Root cause (technical + contributing factors)
- Why it wasn’t caught (tests, monitoring, process)
- Preventative actions (tests, alerts, guardrails, docs)

---

## API Design

**When**: adding/modifying endpoints, contracts, schemas.

**Checklist**:
- Contract: request/response, errors, pagination, idempotency, versioning
- Auth: required scopes/roles
- Validation: runtime validation and error format consistency
- Compatibility: backwards compatibility plan
- Observability: request IDs, structured logs, metrics

---

## Data & Migrations

**When**: changing schema, data model, storage semantics.

**Checklist**:
- Backward compatibility + rollout plan
- Reversible migrations
- Backfill strategy (online vs offline)
- Indexing/perf impact
- Data integrity and constraints

---

## Security Review (OWASP)

**When**: any user input, auth flows, file handling, external calls.

**Checklist**:
- Input validation (types, bounds, format)
- Output encoding (XSS)
- Injection defenses (SQL/NoSQL/command)
- Secrets handling (no logs, no commits)
- Dependency risk (audit)
- Least privilege (authz)

---

## Auth/AuthZ Review

**When**: login, sessions, tokens, permissions, RBAC.

**Checklist**:
- Token storage and rotation
- AuthN vs AuthZ boundaries
- Permission checks near data access
- Audit logging for sensitive actions
- Threat model high-level

---

## Test Strategy

**When**: planning or implementing non-trivial behavior changes.

**Checklist**:
- Unit tests: pure logic, edge cases, error paths
- Integration tests: API, DB, external boundaries
- Regression test: the reported bug gets a test
- Determinism: avoid flakiness

---

## Performance Profiling

**When**: latency issues, N+1, heavy loops, large payloads.

**Checklist**:
- Identify hotspot (profile/log timings)
- Complexity check (O(n²))
- IO patterns (DB queries, network calls)
- Caching opportunities
- Backpressure/retries/timeouts

---

## Refactor Safety

**When**: cleanup, re-architecture, moving code.

**Checklist**:
- Preserve behavior (tests before/after)
- Small commits, easy rollback
- Avoid mixed concerns (refactor vs feature)
- Deprecation strategy if interfaces change

---

## Release Readiness

**When**: prepping to merge/release.

**Checklist**:
- `/review` clean (or warnings accepted)
- `/verify-ci` results recorded (where applicable)
- Docs updated
- Rollback plan noted
- Changelog impact noted

---

## Incident / Hotfix

**When**: production is broken.

**Checklist**:
- Stabilize first: rollback/feature flag
- Minimize blast radius
- Add a regression test
- Postmortem (RCA) after stabilization

---

## Docs Quality

**When**: touching developer workflow or public API.

**Checklist**:
- Update README/ADR/feature docs
- Examples are copy-pasteable
- State and next steps are clear

