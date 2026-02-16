# Review: Manus Context Engineering Lessons Applied to cnogo

**Date:** 2026-02-15
**Branch:** main
**Reviewer:** Claude
**Source:** [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus)

---

## Executive Summary

cnogo already implements several Manus-recommended patterns well (stable prompts, filesystem-as-memory, error preservation). Six specific gaps offer high-impact improvements — particularly **goal recitation**, **tool masking**, and **context compression reversibility**.

---

## Lesson-by-Lesson Analysis

### 1. KV-Cache Optimization

**Manus Lesson:** Keep system prompts stable. Avoid timestamps in prompts. Maintain append-only context. Ensure deterministic serialization.

**cnogo Current State:** STRONG

| Aspect | Status | Notes |
|--------|--------|-------|
| Stable command templates | GOOD | 28 commands are static `.md` files; `$ARGUMENTS` is the only dynamic substitution |
| No timestamps in prompts | GOOD | Timestamps appear in *output* artifacts (PLAN.json, SUMMARY.json), not in command templates |
| Append-only context | PARTIAL | Memory engine events table is append-only; but commands re-read full artifacts each invocation |
| Deterministic serialization | NOT ADDRESSED | No JSON key ordering guarantees in artifact generation |

**Gap: Deterministic JSON serialization**

When commands instruct Claude to generate JSON contracts (PLAN.json, REVIEW.json, etc.), key ordering is non-deterministic. If these artifacts are later re-read as context for subsequent commands, different key orderings invalidate cached prefixes.

**Recommendation:**
- Add a note to artifact contract schemas specifying canonical key order
- In `workflow_validate.py`, warn if JSON keys are not in schema-defined order
- In `bridge.py` and `sync.py`, use `json.dumps(data, sort_keys=True)` for all serialization

**Effort:** Low | **Impact:** Medium (affects multi-step workflows where artifacts become context)

---

### 2. Mask Rather Than Remove Tools

**Manus Lesson:** Don't dynamically add/remove tools mid-iteration. Instead, use state machines to mask tool selection via logit manipulation. Design action names with consistent prefixes.

**cnogo Current State:** PARTIAL

| Aspect | Status | Notes |
|--------|--------|-------|
| Static tool sets per agent | GOOD | `implementer.md` declares fixed tools: `Read, Edit, Write, Bash, Grep, Glob` |
| Consistent naming prefixes | NOT ADDRESSED | Commands use verbs (`plan`, `implement`, `ship`) without grouping prefixes |
| State-based tool restriction | NOT ADDRESSED | No mechanism to restrict available commands based on workflow phase |

**Gap A: No workflow-phase tool gating**

An agent in the "planning" phase can invoke `/ship` or `/implement` prematurely. There's no state machine preventing out-of-sequence command execution.

**Recommendation:**
- Add a `phase` field to the memory engine (e.g., `discuss -> plan -> implement -> review -> ship`)
- Commands check current phase and warn (not block) if invoked out of sequence
- Example: `/implement` warns "No plan artifact found for this feature. Run `/plan` first?"

**Gap B: No command namespace prefixes**

Commands span planning, execution, quality, and release phases but lack prefixes for grouping.

**Recommendation (low priority):**
- Consider optional aliases with phase prefixes for discoverability: `plan:create`, `plan:discuss`, `exec:implement`, `quality:review`, `release:ship`
- This is cosmetic — the current verb-based naming is already clear

**Effort:** Medium (phase gating) / Low (prefixes) | **Impact:** Medium (prevents out-of-order execution)

---

### 3. File System as Extended Memory

**Manus Lesson:** Treat the filesystem as unlimited, persistent, agent-operable memory. Compression must be reversible — preserve URLs/file paths when dropping content.

**cnogo Current State:** STRONG

| Aspect | Status | Notes |
|--------|--------|-------|
| Filesystem as memory | EXCELLENT | Dual persistence: SQLite (`.cnogo/memory.db`) + JSONL (`.cnogo/issues.jsonl`) + planning artifacts on disk |
| Persistent by nature | GOOD | WAL mode, atomic writes, crash-safe session checkpointing |
| Agent-operable | GOOD | Agents claim/close via Python one-liners in task descriptions |
| Reversible compression | NOT ADDRESSED | `prime()` drops content irreversibly — no way to restore from summary |

**Gap: Irreversible context compression in `prime()`**

`context.py:prime()` truncates handoff notes to 120 chars and omits issue descriptions entirely. There's no breadcrumb to restore the full content. The Manus insight: compress by replacing content with *references* (IDs, file paths), not by deleting it.

**Recommendation:**
- `prime()` already emits issue IDs (`cn-a3f8`) which can be resolved via `show(id)` — this is good
- Add a `prime(verbose=True)` mode that includes file paths for each issue's metadata (e.g., `files: storage.py, graph.py`)
- Add a "restore hint" line at the bottom: `Details: python3 scripts/workflow_memory.py show <id>`
- This preserves the path back to full context without bloating the summary

**Effort:** Low | **Impact:** High (agents can self-recover detailed context)

---

### 4. Recitation for Attention Management

**Manus Lesson:** Combat "lost-in-the-middle" by having agents rewrite task summaries (like todo.md) into the end of context. Repeatedly recite objectives.

**cnogo Current State:** WEAK

| Aspect | Status | Notes |
|--------|--------|-------|
| Goal recitation | NOT IMPLEMENTED | No command instructs agents to restate objectives mid-execution |
| Todo recitation | NOT IMPLEMENTED | No todo.md or checkpoint mechanism during long workflows |
| `prime()` as recitation | PARTIAL | `prime()` is called at command start but not mid-execution |

**Gap: No mid-execution goal recitation**

This is the biggest gap relative to Manus. During `/implement` (which can span 7+ steps across multiple files), or during team implementations (50+ tool calls), agents lose focus on the original objective. Manus specifically found this critical for long-running tasks.

**Recommendation:**
- **Add a recitation step to `/implement`:** After Step 2 (every task completion), inject: "Restate: What is the plan objective? What tasks remain? What is the current task's success criterion?"
- **Add recitation to `implementer.md`:** Before the Verify step, the agent should re-read its task description to confirm alignment
- **Add a `checkpoint()` function to the memory engine:** Returns a 1-2 line summary: "Feature X: 2/3 tasks done. Current: Task 3 — add retry logic to storage.py. Verify: `python3 -m pytest tests/`"
- **Integrate checkpoint into team `/status`:** When team lead checks status, each agent's checkpoint is included

**Effort:** Medium | **Impact:** High (prevents drift in long-running agent sessions — Manus's top finding)

---

### 5. Preserve Errors as Learning Evidence

**Manus Lesson:** Keep wrong turns in context so models update internal beliefs. Don't sanitize failures.

**cnogo Current State:** STRONG

| Aspect | Status | Notes |
|--------|--------|-------|
| Error preservation in memory | GOOD | Events table stores all state changes with full data payloads |
| Error context in commands | GOOD | `/implement` says "If verification fails: diagnose, fix, re-verify" — doesn't discard |
| Stack traces preserved | GOOD | No sanitization of error messages in memory engine |
| Error recovery instructions | GOOD | "After 2 failures, message the team lead" — escalation path |

**Gap: No structured error-learning feedback loop**

While errors are preserved in the events table, there's no mechanism for agents to *read back* prior failures before retrying. An agent that fails Task 2 and retries doesn't explicitly review what went wrong on attempt 1.

**Recommendation:**
- Add to `implementer.md` cycle: "Before retry, read your previous error: `python3 -c \"from scripts.memory import show; print(show('<id>'))\"`"
- In `bridge.py:generate_implement_prompt()`, add: "**On retry:** Review previous attempt's error before trying again."
- Consider a `history(issue_id)` function that returns the events log for an issue — agents can inspect their own trail

**Effort:** Low | **Impact:** Medium (improves retry success rate)

---

### 6. Increase Pattern Diversity

**Manus Lesson:** Few-shot examples can backfire. Introduce structured variation in actions and observations to prevent brittle pattern-matching.

**cnogo Current State:** WEAK

| Aspect | Status | Notes |
|--------|--------|-------|
| Template variation | NOT ADDRESSED | All JSON contract examples use identical structure (`"timestamp": "2026-01-24T00:00:00Z"`) |
| Observation formatting | NOT ADDRESSED | `prime()` output is always the same markdown format |
| Action phrasing | NOT ADDRESSED | Commands use identical phrasing patterns |

**Gap: Identical example values across 22 command files**

Every JSON contract example uses `"timestamp": "2026-01-24T00:00:00Z"` and similar hardcoded values. This is a minor risk — Claude may over-anchor on these specific values rather than generating contextually appropriate ones.

**Recommendation:**
- Low priority: Vary example timestamps, feature slugs, and field values across command templates
- More important: In `prime()`, consider occasionally varying the section order or using different markdown formatting (tables vs. lists) — though this conflicts with cacheability, so evaluate carefully
- **Best approach:** Keep templates stable (for caching) but add a note: "Generate contextually appropriate values — examples are illustrative only, not templates to copy"

**Effort:** Low | **Impact:** Low (minor quality improvement)

---

## Summary: Improvement Priority Matrix

| # | Improvement | Effort | Impact | Manus Lesson |
|---|------------|--------|--------|-------------|
| 1 | **Goal recitation / checkpoint()** | Medium | HIGH | Lesson 4: Recitation |
| 2 | **Reversible compression in prime()** | Low | HIGH | Lesson 3: Filesystem memory |
| 3 | **Error-learning feedback in retries** | Low | Medium | Lesson 5: Preserve errors |
| 4 | **Deterministic JSON serialization** | Low | Medium | Lesson 1: KV-cache |
| 5 | **Workflow phase gating** | Medium | Medium | Lesson 2: Tool masking |
| 6 | **Example value diversity** | Low | Low | Lesson 6: Pattern diversity |

---

## Automated Checks

| Check | Result |
|-------|--------|
| Linting | N/A (Python stdlib, no linter configured) |
| Tests | N/A (no test suite — tracked as v2.0) |
| Security Scan | PASS (no secrets detected) |
| Type Check | N/A (no mypy configured) |
| Dependency Audit | N/A (zero external deps) |
| Workflow Validation | PASS |
| Memory Engine | PASS (smoke test OK) |
| Syntax Compilation | PASS (workflow_validate.py, workflow_memory.py) |

---

## Karpathy Checklist

| Principle | Status | Notes |
|----------|--------|-------|
| Think Before Coding | PASS | Each improvement maps directly to a Manus lesson with clear rationale |
| Simplicity First | PASS | Recommendations are incremental — no architectural rewrites proposed |
| Surgical Changes | PASS | Each improvement is scoped to specific files with explicit impact boundaries |
| Goal-Driven Execution | PASS | Priority matrix provides clear ordering; each item has effort/impact assessment |

---

## Verdict

**PASS** — cnogo's architecture already aligns well with 4 of 6 Manus principles (KV-cache stability, filesystem-as-memory, error preservation, static tool sets). The two weakest areas — **goal recitation** and **reversible compression** — represent the highest-impact improvements and should be prioritized for the next development cycle.

### Recommended Next Steps

1. `/plan context-recitation` — Add `checkpoint()` to memory engine + recitation steps to implement/implementer
2. `/quick prime-restore-hints` — Add verbose mode and restore hints to `prime()`
3. `/quick deterministic-json` — Add `sort_keys=True` to serialization paths
