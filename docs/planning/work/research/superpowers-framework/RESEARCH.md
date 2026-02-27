# Research: obra/superpowers Framework

## CONTEXT

**Topic:** Analysis of the superpowers agentic skills framework for adoption patterns applicable to cnogo.
**Date:** 2026-02-25
**Mode:** auto (repo + web)
**Repo:** https://github.com/obra/superpowers (61,683 stars as of 2026-02-25, MIT, plugin manifest v4.3.1; latest GitHub Release: v4.1.1)

## Key Findings

### 1. Architecture: Skill-Based Agent Behavior

Superpowers decomposes all agent workflow into **14 composable skills**, each a `SKILL.md` with YAML frontmatter (`name`, `description`) and structured markdown body. In JS plugin runtimes, skill discovery is implemented by `lib/skills-core.js` which recursively finds `SKILL.md` files, extracts frontmatter, and supports shadowing (personal skills override plugin skills unless `superpowers:` is prefixed). In Codex, discovery is native via `~/.agents/skills` symlink setup.

**Trigger model:** Skills are intended to be mandatory, not optional. On Claude plugin runtimes, the `using-superpowers` meta-skill is injected at session start via a synchronous `SessionStart` hook so instructions are present from the first turn. On Codex, the same behavior is achieved through native skill discovery plus trigger descriptions (no SessionStart hook path).

**cnogo parallel:** `.claude/skills/` serves the same purpose but skills are invoked by slash commands, not auto-triggered. cnogo could adopt auto-trigger via session hooks.

### 2. Enforced TDD as Iron Law

The `test-driven-development` skill is the most opinionated piece. Key design choices:

- **Delete-and-restart mandate:** Code written before a failing test must be deleted entirely. No "keep as reference."
- **Verification is mandatory:** Must watch test fail (RED), watch it pass (GREEN), then refactor. Skipping any step is treated as a rule violation.
- **Rationalization table:** 12 common excuses are pre-addressed with rebuttals, preventing the model from reasoning its way out of TDD.
- **Anti-patterns reference:** Separate `testing-anti-patterns.md` covers mock abuse, test-only methods on production classes.

**cnogo gap:** cnogo has a `/tdd` command, but does not enforce TDD globally as a hard gate with "iron law" semantics. Tightening this into an explicit hard gate (or policy toggle) would improve consistency.

### 3. Two-Stage Subagent Review

The `subagent-driven-development` skill is the core execution engine. Each plan task follows:

1. **Dispatch implementer subagent** with full task text (never make subagent read files)
2. Implementer can **ask questions before starting** (not after)
3. Implementer does work + self-review + commit
4. **Spec compliance reviewer** verifies what was built matches what was requested (explicitly told "do not trust the implementer's report")
5. **Code quality reviewer** runs only after spec passes
6. Fix loops until both reviewers approve

**Key insight:** The spec reviewer prompt contains adversarial framing: "The implementer finished suspiciously quickly. Their report may be incomplete, inaccurate, or optimistic." This prevents rubber-stamping.

**cnogo parallel:** cnogo's `/review` skill and `agentTeams` config support multi-agent review but lack the two-stage (spec then quality) separation and adversarial reviewer framing.

### 4. Task Granularity: 2-5 Minute Chunks

Plans decompose into steps where each step is a single action:
- Write the failing test (step)
- Run it to verify failure (step)
- Implement minimal code (step)
- Run tests to verify pass (step)
- Commit (step)

This is finer-grained than cnogo's "max 3 tasks per plan" rule. Superpowers tasks are closer to individual git commits than feature slices.

**Trade-off:** Finer granularity means more subagent dispatches (higher cost) but better isolation and easier rollback.

### 5. Verification Before Completion

A standalone skill that blocks any success claim without fresh evidence. Key patterns:

- Gate function: IDENTIFY command -> RUN it -> READ output -> VERIFY -> THEN claim
- Bans words like "should", "probably", "seems to" before verification
- Bans satisfaction expressions ("Great!", "Done!") before running commands
- Applies to agent delegation too: "Agent said success" requires independent verification

**cnogo gap:** cnogo's workflow_validate.py checks contracts and freshness but doesn't enforce runtime verification claims within agent conversations.

### 6. Git Worktree Integration

Structured skill for worktree management:
- Priority-based directory selection (.worktrees > worktrees > CLAUDE.md > ask user)
- Safety verification (must be gitignored before creation)
- Auto-detect project setup (package.json, Cargo.toml, requirements.txt)
- Baseline test verification before work begins

**cnogo parallel:** cnogo's `agentTeams.worktreeMode: "always"` enables worktrees but lacks the structured directory selection and safety verification.

### 7. Brainstorming as Hard Gate

The brainstorming skill uses `<HARD-GATE>` tags to prevent any implementation before design approval. It intercepts even `EnterPlanMode` calls, routing through brainstorming first. The checklist is enforced as tasks, not suggestions.

**Design pattern:** "Anti-Pattern" callouts address the exact rationalizations models use to skip process steps. This is a recurring pattern across all skills.

### 8. Plugin Architecture

Multi-platform delivery:
- `.claude-plugin/` with `plugin.json` manifest (name, version, keywords)
- `.cursor-plugin/` for Cursor support
- `.codex/` with INSTALL.md for Codex
- `.opencode/` for OpenCode
- `hooks/hooks.json` defines SessionStart hook
- `hooks/session-start` (extensionless for Windows compat) bootstraps context

## Options for cnogo

### Option A: Adopt Superpowers Directly

Install superpowers as a plugin alongside cnogo's existing workflow.

- **Pro:** Immediate access to 14 battle-tested skills, large community (61,683 stars as of 2026-02-25)
- **Con:** Conflicts with cnogo's planning contracts, memory engine, and slash commands. Two competing workflow systems.
- **Fit:** Poor. Superpowers is opinionated about its own workflow and would clash with cnogo's WORKFLOW.json-driven approach.

### Option B: Port Key Patterns Into cnogo Skills

Selectively adopt the highest-value patterns as cnogo-native skills.

Priority patterns to port:
1. **TDD enforcement** - Strengthen existing `/tdd` workflow with hard gates and rationalization tables (optionally as a dedicated skill + policy toggle)
2. **Two-stage review** - Extend `/review` to separate spec compliance from code quality
3. **Verification-before-completion** - Add as a skill or hook that blocks success claims
4. **Adversarial reviewer framing** - Update code-reviewer agent prompt
5. **Brainstorming hard gate** - Add `<HARD-GATE>` pattern to `/brainstorm`

- **Pro:** Best patterns without workflow conflicts. Builds on cnogo's existing infrastructure.
- **Con:** Porting effort. Must adapt patterns to Python/stdlib-only constraint.
- **Fit:** Strong. Extends cnogo without replacing it.

### Option C: Study and Adapt Philosophy Only

Don't port code or skill files. Instead, internalize the design principles:
- Mandatory skills (not optional suggestions)
- Rationalization prevention tables
- Adversarial reviewer framing
- Verification gates before claims

- **Pro:** Zero integration effort. Improves agent behavior through CLAUDE.md updates.
- **Con:** Loses the structured enforcement that makes superpowers effective.
- **Fit:** Moderate. Good as a first step, insufficient long-term.

## Recommendation

**Option B: Port Key Patterns.** Start with these three, in order:

1. **Verification-before-completion skill** - Highest ROI, prevents false completion claims. Small skill file, no infrastructure changes.
2. **Two-stage review separation** - Extend existing review workflow with spec-compliance pass before code-quality pass. Adversarial framing in reviewer prompts.
3. **TDD enforcement skill** - Most ambitious but highest long-term quality impact. Hard gates, rationalization tables, delete-and-restart mandate.

Each can be shipped independently as a `.claude/skills/` file with no changes to cnogo's core scripts.

## Risks

| Risk | Mitigation |
|------|------------|
| Over-enforcement slows iteration | Make skills warn-mode initially, escalate to block after validation |
| Rationalization tables become stale | Review quarterly against actual model evasion patterns |
| Two-stage review doubles cost | Use haiku for spec compliance reviewer (cheaper, focused task) |
| TDD mandate rejected by users | Gate behind WORKFLOW.json toggle (`tdd.mode: "enforce" / "warn" / "off"`) |

## Open Questions

1. Should verification-before-completion be a skill or a PreToolUse hook that intercepts commit/push?
2. Should adversarial framing be the default for all reviewer agents, or only spec compliance?
3. Can cnogo's memory engine track TDD compliance (test-first vs test-after) as a quality metric?

## SUMMARY

Superpowers is a mature skills framework (plugin manifest v4.3.1; 61,683 stars as of 2026-02-25) that enforces structured agent development workflows through hard-gated skills and rationalization prevention. Its strongest patterns are strict TDD enforcement, two-stage adversarial review, and verification-before-completion. cnogo should import these patterns by hardening existing workflows (especially `/tdd` and `/review`) and adding verification-before-completion enforcement for highest immediate ROI.
