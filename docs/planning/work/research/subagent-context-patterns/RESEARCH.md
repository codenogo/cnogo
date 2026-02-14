# Research: Subagent Context Management Patterns

**Date:** 2026-02-14
**Mode:** auto (repo + web)

## Executive Summary

- **Subagents hitting "Context limit reached" is a known, recurring issue** across Claude Code versions (Issues #18240, #17591, #16209, #15191) — not a cnogo-specific bug, but cnogo's command design amplifies it
- **Root cause in cnogo**: commands were designed for interactive sessions (~200K budget) but subagents inherit compressed context windows; commands unconditionally load skills.md, CONTEXT.md, PLAN.json, and agent definitions — consuming 5-8K tokens before any code is read
- **Gas Town's key transferable insight**: separate *who agents are* (persistent roles) from *how long they stay active* (ephemeral sessions); store work state externally (git/SQLite), not in context
- **Anthropic's own guidance**: subagents should return 1-2K token summaries, not full transcripts; use JIT (just-in-time) context loading, not eager loading; treat context as a finite budget with diminishing returns
- **The Superpowers pattern** (most directly applicable): dispatch each task to a fresh subagent with only the context it needs; persist progress to disk, not memory; review between tasks
- **Context budget rule of thumb**: design subagent tasks to complete within <50% context usage; system prompt should be 2-5K tokens maximum
- **The fix for cnogo is structural**: split fat commands into subagent-aware variants, inline references instead of file reads, use the memory engine as external state rather than context payload

## Context (Project-Specific)

cnogo is a 28-command workflow pack for Claude Code with a SQLite-backed memory engine. The `/team implement` command spawns implementer subagents to execute plan tasks in parallel. These subagents consistently hit context limits because:

1. `team.md` (307 lines) loads all agent definitions + full plan JSON per task
2. `implement.md` (202 lines) says "Read ALL files listed" + loads skills.md
3. `implementer.md` agent calls `memory.prime()` adding 500-1500 tokens
4. CLAUDE.md (163 lines) is always loaded
5. Each command references `docs/skills.md` (287 lines) unconditionally

Total overhead before any code is read: ~5-8K tokens. With Sonnet subagents on complex plans, this exhausts the budget during file exploration.

## Options Considered

### Option A: Subagent-Aware Command Splitting

**What it is**: Create slim variants of commands that load minimal context when running as a subagent. The full interactive version stays for human use.

**When to use**: When commands serve dual purposes (interactive + subagent delegation)

**Pros**:
- Directly solves the problem — subagents get only what they need
- No behavior change for interactive use
- Aligns with Anthropic's guidance: "each subagent starts fresh with only the context it needs"
- The Superpowers plugin proves this works at scale (12-15 tasks per feature)

**Cons**:
- Two versions of some commands to maintain
- Need a detection mechanism (env var or prompt flag)

**Risks**:
- Subagent variant may miss context that turns out to be important
- Maintenance burden if commands diverge significantly

**Evidence**:
- Superpowers plugin dispatches each task to fresh subagent with targeted context → prevents exhaustion
- Anthropic's multi-agent research system: subagents return 1-2K summaries, not full transcripts
- Gas Town: agents have "persistent identity but ephemeral sessions" — work state lives in git, not context

### Option B: JIT Context Loading (Lazy References)

**What it is**: Replace file reads in command prompts with lightweight references. Instead of "Read docs/skills.md and apply Karpathy Principles", say "Apply Surgical Changes: touch only assigned files". Load full content only when the agent determines it's needed.

**When to use**: When commands reference large files that are only partially relevant

**Pros**:
- No command splitting needed — single version works for both modes
- Aligns with Anthropic's context engineering guidance: "maintain lightweight identifiers and dynamically load data at runtime via tools"
- Martin Fowler's article: "Claude Code exemplifies this — CLAUDE.md loads upfront; glob/grep enable runtime discovery"
- Reduces baseline token cost for all users, not just subagents

**Cons**:
- Agents may not discover context they need
- Requires careful selection of what to inline vs. defer

**Risks**:
- Agent may waste turns re-discovering information that was previously loaded eagerly
- Quality regression if important context is deferred too aggressively

**Evidence**:
- Anthropic's context engineering blog: "find the smallest possible set of high-signal tokens that maximize likelihood of desired outcome"
- zoer.ai best practices: system prompts should be 2-5K tokens; task context 20-40K; reserve 30-50K buffer
- Context budget allocation: System (2-5K) + Task (20-40K) + Working Memory (10-20K) + Reserve (30-50K)

### Option C: External State + Lightweight Handoffs (Gas Town Pattern)

**What it is**: Store all work state (plans, progress, context) in the memory engine (SQLite) or disk files. Subagents receive only a task ID and retrieve what they need at runtime. Progress is written back to disk, not held in context.

**When to use**: When coordination state is large or when agents need to survive context resets

**Pros**:
- cnogo already has the memory engine — just needs to use it more
- Aligns with Gas Town's core pattern: "persistent roles, ephemeral sessions"
- Superpowers pattern: "progress is persisted to markdown files on disk, not held in memory"
- Anthropic's multi-agent system: "subagents call tools to store work in external systems, then pass lightweight references back"
- Naturally handles crash recovery (work state survives context compaction)

**Cons**:
- Requires memory engine to be fully functional (currently 9 open issues)
- More tool calls = more turns = potentially slower
- Added complexity in read/write patterns

**Risks**:
- Memory engine bugs could block all agent work
- Disk I/O adds latency vs. in-context data

**Evidence**:
- Gas Town: Beads ledger stores work state as structured data; agents retrieve via ID
- Anthropic's research system: lead agent saves plan to Memory to persist across compaction
- Kiearan Klaassen's swarm guide: "file-based coordination" via config.json + task files

### Option D: Model + Turn Budget Controls

**What it is**: Use `maxTurns` in agent frontmatter to cap subagent execution, set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to trigger early compaction, and route subagents to models with appropriate context windows.

**When to use**: As a safety net alongside other approaches

**Pros**:
- Quick to implement — frontmatter changes only
- `maxTurns` prevents runaway subagents
- Early compaction (e.g., 50%) keeps working memory available
- Already supported by Claude Code infrastructure

**Cons**:
- Treats symptoms, not root cause
- `maxTurns` may cut off legitimate work
- Compaction loses information

**Risks**:
- Over-aggressive compaction drops critical context
- Under-aggressive limits still hit exhaustion

**Evidence**:
- Claude Code docs: "set CLAUDE_AUTOCOMPACT_PCT_OVERRIDE to a lower percentage (e.g., 50)"
- Token budget guide: "design work segments to complete within less than 50% context usage"
- Known bug: subagent return data included in parent session without cleanup (#18240)

## Recommendation

**Use Options A + B + D together. Option C as a follow-up.**

### Immediate (fixes the problem now):

1. **Add `maxTurns: 30` to implementer.md** — prevents runaway context consumption
2. **Inline skill references** — replace "Read docs/skills.md" with 1-sentence principles in commands. Example: change `Apply **Karpathy Principles** from docs/skills.md` to `Apply Surgical Changes (touch only assigned files) and Goal-Driven Execution (verify after each task)`
3. **Remove the agent definition table from team.md** — subagents don't need to know about all other agents. The team lead loads agents; teammates just execute
4. **Stop loading CONTEXT.md and PLAN.json in implementer tasks** — the task description from the bridge module already contains everything the implementer needs. Don't make it re-read source files
5. **Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60`** in settings.json env — triggers compaction earlier

### Short-term (structural fix):

6. **Split team.md**: `team.md` handles create/status/message/dismiss (light); the `implement` action's heavy lifting moves into the bridge module's task descriptions, which are already self-contained
7. **Remove spawn.md inline fallback profiles** — 800 tokens of dead weight; require `.claude/agents/*.md` to exist
8. **Make implementer agent truly self-contained** — its task description (from bridge) should be the single source of truth; no references to external docs

### Follow-up (builds on memory engine):

9. **Use memory as the coordination substrate** — subagents read task details from memory by ID instead of receiving them in prompt
10. **Write progress to memory, not messages** — reduces message payload between agents

## Open Questions

- [ ] What is the actual effective context window for Sonnet subagents? (200K nominal but practical limit may be lower with system prompt overhead)
- [ ] Does `maxTurns` interact well with the claim→verify→close cycle? Need to test that 30 turns is sufficient for typical plan tasks
- [ ] Should implementer use `memory: project` or `memory: local`? Project memory is git-tracked which adds noise; local is ephemeral
- [ ] Can we detect "running as subagent" in command prompts to conditionally load context? (env var `CLAUDE_CODE_AGENT_NAME` exists but isn't documented for this purpose)
- [ ] The known bug (#18240 / #17591) about subagent return data bloating parent context — is this fixed in current Claude Code versions?

## Sources

- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Core principles: JIT loading, altitude calibration, sub-agent architectures returning 1-2K summaries
- [Anthropic: How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system) — Orchestrator-worker pattern, memory persistence, fresh subagent spawning for context relief
- [Claude Code Docs: Create Custom Subagents](https://code.claude.com/docs/en/sub-agents) — Official subagent configuration, maxTurns, skills preloading, auto-compaction, persistent memory
- [Martin Fowler: Context Engineering for Coding Agents](https://martinfowler.com/articles/exploring-gen-ai/context-engineering-coding-agents.html) — CLAUDE.md as eager load, glob/grep as JIT, modular organization, lazy-loaded skills
- [Maggie Appleton: Gas Town's Agent Patterns](https://maggieappleton.com/gastown) — Persistent roles/ephemeral sessions, hierarchical supervision, design as bottleneck, poor upfront design compounds
- [Gas Town GitHub (Steve Yegge)](https://github.com/steveyegge/gastown) — GUPP principle, git worktree isolation, Beads ledger, convoy-based work distribution
- [Paddo.dev: GasTown and the Two Kinds of Multi-Agent](https://paddo.dev/blog/gastown-two-kinds-of-multi-agent/) — Orchestration vs. collaboration multi-agent styles
- [Kieran Klaassen: Claude Code Swarm Orchestration Skill](https://gist.github.com/kieranklaassen/4f2aba89594a4aea4ad64d753984b2ea) — File-based coordination, env injection, sequential pipelines, self-organizing swarms
- [Richard Porter: Superpowers Plugin](https://richardporter.dev/blog/superpowers-plugin-claude-code-big-features) — Fresh subagent per task, disk-persisted progress, inter-task code review, 12-15 task features
- [RichSnapp: Context Management with Subagents](https://www.richsnapp.com/article/2025/10-05-context-management-with-subagents-in-claude-code) — JIT retrieval, conversation forking, tool isolation, prompt hygiene
- [zoer.ai: Claude Code Sub-Agents Best Practices](https://zoer.ai/posts/zoer/claude-code-sub-agents-best-practices) — 2-5K system prompt budget, progressive expansion, semantic context retrieval, validator agent pattern
- [DeepWiki: Token Budget Management](https://deepwiki.com/shanraisshan/claude-code-best-practice/4.3-token-budget-management) — Always-loaded vs lazy-loaded context, design tasks for <50% context usage, manual compaction at 50%
- [GitHub Issue #18240: Subagent Return Context Exhaustion](https://github.com/anthropics/claude-code/issues/18240) — Known bug: subagent response data bloats parent context; closed as duplicate of #17591, #16209, #15191
- [Addy Osmani: Claude Code Swarms](https://addyosmani.com/blog/claude-code-agent-teams/) — Agent team patterns, coordination overhead, cost considerations (5x tokens for 5-person team)
- [alexop.dev: From Tasks to Swarms](https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/) — Wave execution, direct messaging, plan-first approach, cheaper models for teammates
