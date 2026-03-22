# Research: Honcho Memory Patterns vs cnogo

**Topic**: What can cnogo steal from Honcho's agent memory architecture?
**Date**: 2026-03-21
**Mode**: auto (repo + web)

---

## 1. Decision to Resolve

Honcho (plastic-labs/honcho) reimagines agent memory as a reasoning-driven system rather than simple retrieval. cnogo's memory engine is a deterministic task coordination layer (SQLite + JSONL). The question: which Honcho patterns are worth adopting to improve cnogo's workflow intelligence, without violating stdlib-only and offline-first constraints?

---

## 2. Evidence Summary

### What Honcho Does Differently

| Concept | Honcho | cnogo |
|---------|--------|-------|
| **Memory model** | Derived observations from conversations (explicit, deductive, inductive, contradiction) | Explicit task CRUD only |
| **Retrieval** | Agentic tool-based search (dialectic) with contradiction detection | Flat SQL queries (ready, blockers, by-feature) |
| **Background processing** | Continuous deriver pipeline extracts insights async | None — state changes only on explicit API calls |
| **Multi-perspective** | Peer cards track what each observer knows about each entity | Single-perspective flat task state |
| **Semantic search** | Vector embeddings (pgvector/LanceDB/Turbopuffer) | None |
| **Reconciliation** | Continuous vector sync with rolling time budgets | Manual session reconciliation |
| **Contradiction handling** | Explicit level; refuses to silently resolve conflicts | No conflict detection |
| **Deferred reasoning** | "Dreamer" module discovers patterns, anomalies asynchronously | Scheduler exists but no insight derivation |

### What cnogo Does Well That Honcho Doesn't

| Strength | Detail |
|----------|--------|
| **Offline-first** | No network, no external services, no API keys |
| **Stdlib-only** | Zero dependencies beyond Python 3 |
| **Deterministic coordination** | Forward-only phases, DAG dependencies, blocked cache |
| **Audit trail** | Immutable events table with actor tracking |
| **Git-portable** | JSONL sync enables version-controlled state |
| **Policy enforcement** | TDD mode, task ownership, completion evidence |

**Source**: Honcho repo (GitHub plastic-labs/honcho, commit history, src/, SDK docs). cnogo repo (`.cnogo/scripts/memory/`, 20+ modules, ~6600 lines).

---

## 3. Options: What to Steal

### Option A: Observation Extraction (High Value, Medium Effort)

**Concept**: After conversations (or at session boundaries), derive structured observations from what happened — decisions made, blockers discovered, patterns found, context learned.

**Honcho parallel**: Their deriver pipeline continuously extracts "explicit atomic facts" from messages and stores them as documents with observation levels.

**cnogo adaptation**:
- Add an `observations` table: `issue_id | observation | level (explicit|inferred) | source (conversation|commit|review) | created_at`
- Hook into session checkpoints (already exist via `workflow_memory.py checkpoint`)
- Extract observations from events metadata — e.g., when a task is closed, capture *why* it was closed, what was learned
- `prime()` can then include recent observations, not just task states
- **Stays stdlib-only**: No LLM calls needed; observations are structured text extracted at known lifecycle points

**Tradeoff**: Adds schema complexity. Observations may become stale. Need a decay/archival strategy.

### Option B: Contradiction Detection (High Value, Low Effort)

**Concept**: When new information conflicts with existing state, surface it explicitly rather than silently overwriting.

**Honcho parallel**: Their dialectic agent refuses to resolve contradictions arbitrarily — presents both sides.

**cnogo adaptation**:
- On `update()` or `report_done()`, check if the new state contradicts existing metadata (e.g., task marked done but blocker still open; plan says X files but implementation touched Y files)
- Store contradictions as events with `event_type: contradiction`
- `prime()` includes active contradictions in context summary
- Policy enforcement can warn or error on unresolved contradictions

**Tradeoff**: Minimal — this is mostly validation logic on existing operations.

### Option C: Multi-Perspective Task Notes (Medium Value, Low Effort)

**Concept**: Different agents (implementer, reviewer, debugger) see the same task differently. Let each record their perspective.

**Honcho parallel**: Peer cards — observer-specific views of entities.

**cnogo adaptation**:
- Extend events or metadata with `actor_perspective` field
- When implementer claims a task, they record implementation notes
- When reviewer reviews, they record review findings
- When debugger investigates, they record debug context
- `prime()` can filter by current actor role to show relevant perspectives

**Tradeoff**: Small schema change. Risk of perspective noise without curation.

### Option D: Semantic Task Search (Medium Value, High Effort)

**Concept**: Find related tasks by meaning, not just by feature_slug or label.

**Honcho parallel**: Vector embeddings on all documents, semantic similarity search.

**cnogo adaptation**:
- **Lightweight version**: TF-IDF on task titles+descriptions using stdlib `collections.Counter` + cosine similarity. No external deps.
- Store term vectors in a `task_vectors` table or precompute at export time
- Enable `memory.py search "auth timeout"` to find semantically related tasks
- Could also power "duplicate detection" on create

**Tradeoff**: TF-IDF is a pale shadow of vector embeddings. But it's stdlib-only and better than nothing. Full vector search would need the graph venv.

### Option E: Background Insight Derivation (High Value, Medium Effort)

**Concept**: Periodically analyze accumulated events to derive higher-level patterns — "this feature has had 3 tasks reopened", "implementer-1 consistently takes longer on auth tasks", "review findings cluster around error handling".

**Honcho parallel**: Dreamer module + deriver pipeline.

**cnogo adaptation**:
- Add a `derive` command to the scheduler (already has 15-min patrol)
- Analyze events table for patterns: reopened tasks, stalled features, recurring blockers
- Store derived insights as observations (see Option A)
- Surface in `prime()` as "attention items"

**Tradeoff**: Requires Option A first. Pattern detection logic must be maintained.

### Option F: Conversation Context Capture (High Value, Medium Effort)

**Concept**: Capture key decisions and context from Claude Code conversations, not just task state changes.

**Honcho parallel**: All messages stored and processed; metamessages for out-of-band context.

**cnogo adaptation**:
- Add a `context_notes` field to events or a separate `notes` table
- Slash commands like `/discuss` and `/implement` already create events — enrich them with conversation summaries
- Hook-based: post-conversation hook extracts key decisions and stores as observations
- Enables "why did we decide X?" queries later

**Tradeoff**: Conversation capture is inherently lossy. Need to be selective about what's stored.

---

## 4. Recommendation

**Adopt in order of priority**:

| Priority | Option | Why |
|----------|--------|-----|
| **P0** | B: Contradiction Detection | Lowest effort, highest immediate value. Catches real bugs in task coordination. Pure validation logic. |
| **P1** | A: Observation Extraction | Foundational for C, E, F. Gives memory system the ability to store *learned context*, not just task state. |
| **P1** | C: Multi-Perspective Notes | Small schema change, big improvement for multi-agent coordination. Natural extension of existing events. |
| **P2** | F: Conversation Context Capture | Requires A. Bridges the gap between "what happened" (events) and "why it happened" (context). |
| **P2** | E: Background Insight Derivation | Requires A. Leverages existing scheduler. Turns accumulated data into actionable attention items. |
| **P3** | D: Semantic Task Search | Nice-to-have. TF-IDF version is feasible but limited. Full vector search breaks stdlib constraint. |

**Do NOT adopt**:
- Honcho's full vector store abstraction (pgvector/LanceDB/Turbopuffer) — violates stdlib-only constraint
- Their managed service model — cnogo is offline-first by design
- Their LLM-in-the-loop deriver — adds API dependency to memory operations
- Their REST API surface — cnogo uses direct Python API, which is faster and simpler

**Key insight**: Honcho's best idea is that **memory should be derived, not just stored**. cnogo currently only stores what's explicitly created. Adding even basic observation extraction would be a paradigm shift that enables multiple downstream improvements.

---

## 5. Open Questions

1. **Observation storage format**: Should observations live in the existing events table (as a new event_type) or in a dedicated table? Events table is simpler but mixes concerns.
2. **Decay strategy**: How long should observations persist? Honcho re-derives continuously. cnogo would need explicit archival (e.g., observations older than `freshness.contextMaxAgeDays` get pruned from `prime()` output).
3. **Actor role taxonomy**: For multi-perspective notes, do we use existing actor strings or formalize roles (implementer, reviewer, debugger, leader)?
4. **Contradiction severity**: Should contradictions block operations (like `enforcement.tddMode: error`) or just warn?
5. **Graph DB integration**: The existing graph.db could power semantic search without stdlib violations — worth investigating whether symbol embeddings could double as task similarity.

---

## 6. Next Command

This research spans multiple features and affects memory architecture. Route to:

**`/shape memory-intelligence`** — The observation extraction, contradiction detection, and multi-perspective patterns represent an initiative-level change to how cnogo's memory engine works. This needs shaping before individual features branch into `/discuss`.
