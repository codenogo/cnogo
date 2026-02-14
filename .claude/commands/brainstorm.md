# Brainstorm: $ARGUMENTS
<!-- effort: high -->

Project ideation before committing to decisions in `/discuss`. This is for exploring options, asking narrowing questions, and optionally running deep research.

## Arguments

`/brainstorm <project idea>`

Example: `/brainstorm "workflow pack for Claude SDLC"`

## Your Task

Help the user explore and narrow "$ARGUMENTS" into 1–3 crisp candidate directions that are ready for `/discuss`.

### Step 0: Read Constraints + Skills

1. Read `docs/planning/PROJECT.md` (even if still skeletal) for constraints/patterns
2. Read `docs/planning/WORKFLOW.json` for research policy
3. Apply **Karpathy Principles** from CLAUDE.md (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution)
4. Load relevant `.claude/skills/` files if the topic touches security, API design, or data migrations

### Step 1: Ask Narrowing Questions (Iterative)

Ask a small batch of questions (3–7), then wait for answers, then ask more if needed.

Focus on:
- Target users and core job-to-be-done
- Success criteria (what “done” means)
- Scope boundaries (in vs out)
- Constraints (time, infra, compliance, budgets)
- Key risks (security, data sensitivity, reliability)

### Step 2: Generate Candidate Approaches

Propose 2–4 candidates with clear tradeoffs:

- Option name
- Who it’s for
- What it does / does not do
- Rough architecture
- Biggest risks and mitigations
- What to build first (MVP slice)

### Step 3: Optional Deep Research

If the user asks for research or uncertainty is high (auth/security/compliance/distributed systems), run:

```bash
/research "<topic>"
```

Then incorporate conclusions and link research artifacts.

### Step 4: Create Brainstorm Artifact

Create:

- `docs/planning/work/ideas/<slug>/BRAINSTORM.md`
- `docs/planning/work/ideas/<slug>/BRAINSTORM.json`

Slug rules: kebab-case (`claude-sdlc-workflow`).

`BRAINSTORM.md` template:

```markdown
# Brainstorm: $ARGUMENTS

**Date:** [YYYY-MM-DD]

## Problem / Opportunity
[What are we trying to achieve and why?]

## Constraints
- [...]

## Candidates

### Option A: [Name]
- **Summary**
- **In scope**
- **Out of scope**
- **Risks**
- **MVP slice**

### Option B: [Name]
...

## Recommendation
[Pick 1 primary + 1 backup]

## Next Step

Run:
`/discuss "<display name for chosen option>"`
```

`BRAINSTORM.json` contract (minimal):

```json
{
  "schemaVersion": 1,
  "topic": "workflow pack for Claude SDLC",
  "slug": "claude-sdlc-workflow",
  "timestamp": "2026-01-24T00:00:00Z",
  "questionsAsked": ["..."],
  "constraints": ["..."],
  "candidates": [
    { "name": "Option A", "summary": "...", "risks": ["..."], "mvp": ["..."] }
  ],
  "recommendation": { "primary": "Option A", "backup": "Option B" },
  "research": ["docs/planning/work/research/<slug>/RESEARCH.md (optional)"]
}
```

### Step 5: Validate

```bash
python3 scripts/workflow_validate.py
```

## Output

- 1–3 candidate directions (with tradeoffs)
- The recommended direction
- The exact `/discuss "<display name>"` to run next

