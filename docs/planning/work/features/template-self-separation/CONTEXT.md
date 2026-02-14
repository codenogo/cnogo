# Template Self-Separation - Implementation Context

## Summary

Separate cnogo's own project documentation from the templates that `install.sh` copies to target projects. Currently 3 files (`PROJECT.md`, `ROADMAP.md`, `WORKFLOW.json`) serve dual duty as both templates and cnogo's own docs, preventing cnogo from eating its own dog food. After separation, templates live in `docs/templates/` and cnogo's files in `docs/planning/` contain real project content.

## Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Separation approach | Move templates to `docs/templates/` | Matches existing pattern (CLAUDE-generic.md, CONTEXT-TEMPLATE.md, ADR-TEMPLATE.md already live there) |
| Template naming | `*-TEMPLATE.md` / `*-TEMPLATE.json` | Consistent with existing `CONTEXT-TEMPLATE.md` and `ADR-TEMPLATE.md` |
| WORKFLOW.json | Same treatment as PROJECT.md/ROADMAP.md | Move template to `docs/templates/WORKFLOW-TEMPLATE.json`, fill in cnogo's own |
| Scope | Separation + fill in cnogo's own docs | The whole point is dogfooding; do both together |
| Root CLAUDE.md | Fill in unfilled sections | Already separated (installs from `docs/templates/CLAUDE-generic.md`), but own sections still have placeholders |

## Constraints

- `install.sh` must only be changed to point at new template paths — no behavioral changes
- Template content must remain identical to current files (no new placeholder text)
- cnogo's filled-in docs must accurately describe the project as it exists today
- Zero-dependency Python constraint for all scripts
- Existing installs must not be affected (install.sh skip-if-exists logic unchanged)

## Affected Files

### Templates to create (copy current files)
- `docs/templates/PROJECT-TEMPLATE.md` (from current `docs/planning/PROJECT.md`)
- `docs/templates/ROADMAP-TEMPLATE.md` (from current `docs/planning/ROADMAP.md`)
- `docs/templates/WORKFLOW-TEMPLATE.json` (from current `docs/planning/WORKFLOW.json`)

### Files to fill in with real cnogo content
- `docs/planning/PROJECT.md` — cnogo vision, constraints, architecture, tech stack
- `docs/planning/ROADMAP.md` — actual milestones and completed work
- `docs/planning/WORKFLOW.json` — populate `packages[]` for cnogo's Python scripts
- `CLAUDE.md` (root) — fill in Conventions, Architecture Rules, Testing, Troubleshooting

### Files to update
- `install.sh` — change copy sources for PROJECT.md, ROADMAP.md, WORKFLOW.json to `docs/templates/`

## Open Questions

- None — all decisions resolved during discussion.

## Related Code

- `install.sh:177-184` — current copy logic for PROJECT.md, ROADMAP.md, WORKFLOW.json
- `docs/templates/CLAUDE-generic.md` — existing template pattern (already separated)
- `docs/planning/work/features/CONTEXT-TEMPLATE.md` — existing `-TEMPLATE` naming convention

---
*Discussed: 2026-02-14*
