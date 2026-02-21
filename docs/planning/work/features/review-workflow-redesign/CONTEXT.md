# Review Workflow Redesign

## Problem

Operating principles (previously called "Karpathy principles") are enforced as a mandatory review-time checklist. This is the wrong enforcement point — principles should guide how code is written, not be re-checked during review. Review should focus on catching real defects.

## Architecture: CLAUDE.md Layering

cnogo is a workflow system **installed into other projects**. Three CLAUDE.md layers exist:

| File | Owner | Install behavior | Role |
|------|-------|-----------------|------|
| `CLAUDE.md` (root) | Host project | Skip if exists (from template) | Project-specific instructions |
| `.claude/CLAUDE.md` | cnogo shell | **Always overwritten** | Workflow docs + Operating Principles |
| `docs/templates/CLAUDE-*.md` | cnogo | Copied as root template for new installs | Language-specific scaffolding |

**Key insight**: `.claude/CLAUDE.md` is the shell — always loaded by Claude alongside the host project's CLAUDE.md. This makes it the natural **coding-time enforcement point** for Operating Principles, since it's always-on context during every task.

## Decisions

### 1. Rename: Remove "Karpathy" Branding
All references to "Karpathy" become "Operating Principles." Remove the GitHub attribution link. The principles themselves remain unchanged.

### 2. Move Enforcement to Coding Time
Principles are enforced during implementation via:
- **`.claude/CLAUDE.md`** (always-on context — the shell, always overwritten on install)
- **`/implement` command** pre-task preamble reminding of applicable principles

### 3. Redesign Review Focus
Review restructured around three pillars:
- **Security** — auth, input validation, secrets, injection, sensitive logging
- **Performance** — N+1 queries, unbounded loops, memory leaks, timeout handling
- **Design Patterns** — alignment with codebase patterns, API consistency, proper abstractions

### 4. Principles Optional in Review
Principles may appear as optional notes when relevant (e.g., flagging over-engineering under "Simplicity First") but are not a mandatory checklist.

### 5. Config Changes
- `WORKFLOW.json`: `enforcement.karpathyChecklist` → `enforcement.operatingPrinciples`
- `WORKFLOW.json`: remove `enforcement.reviewPrinciples[]` (no longer review-scoped)
- `WORKFLOW-TEMPLATE.json`: same changes for new installs

### 6. Review Artifact Schema
**REVIEW.json** changes:
- Remove: mandatory `principles[]` array
- Add: `securityFindings[]`, `performanceFindings[]`, `patternCompliance[]`
- Add: optional `principleNotes[]` for when principles are relevant

**REVIEW.md** changes:
- Remove: `## Karpathy Checklist` section
- Add: `## Security`, `## Performance`, `## Design Patterns` sections

## Constraints

- Python stdlib only
- Backward-compatible: old REVIEW.json with `principles[]` still parses (warn, not error)
- WORKFLOW.json accepts both old and new config key during migration
- All 8 principles remain, just renamed and relocated
- `.claude/CLAUDE.md` is always overwritten on install — safe to modify freely
- Templates must be updated for new installs

## Affected Files

| File | Change |
|------|--------|
| `.claude/CLAUDE.md` | Remove "Karpathy" attribution, keep principles as-is |
| `CLAUDE.md` (root) | Already correct (says "Operating Principles") |
| `WORKFLOW.json` | Rename config keys |
| `docs/templates/WORKFLOW-TEMPLATE.json` | Rename config keys for new installs |
| `workflow_checks_core.py` | Rewrite review generation (new sections, new JSON schema) |
| `workflow_validate_core.py` | Update validation (new schema, backward compat) |
| `.claude/commands/review.md` | Remove Karpathy references, add security/perf/patterns focus |
| `.claude/commands/implement.md` | Add principle reminders to task preamble |
| `.claude/skills/code-review.md` | Align with new review structure |
| `README.md` | Remove Karpathy reference |
| `install.sh` | No changes needed (already copies .claude/CLAUDE.md) |
