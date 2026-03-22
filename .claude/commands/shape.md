# Shape: $ARGUMENTS
<!-- effort: high -->

Run a persistent initiative workspace.

## Arguments

`/shape <initiative>`

## Your Task

Treat `/shape` as the only upstream workspace for broad or multi-feature work. Keep cross-feature truth here. Shape owns feature definition, prioritization, readiness, dependencies, research, and feedback intake.

1. Load only the essentials:
- `docs/planning/PROJECT.md`
- `docs/planning/WORKFLOW.json`
- existing `docs/planning/work/ideas/<initiative-slug>/SHAPE.json` when re-entering an initiative
- only the needed shaping skills and scouts

2. Run an iterative shaping conversation:
- clarify users, jobs-to-be-done, success criteria, scope boundaries, constraints, sequencing, and major risks
- revise direction when feasibility, architecture, or sequencing changes
- accept natural-language follow-ups such as split, merge, compare, resequence, promote, park, or reopen
- use `/research "$ARGUMENTS"` only for targeted uncertainty reduction
- do not branch or create feature memory issues here
- end a pass after persisting workspace state, queue state, and next shaping moves

3. Persist the initiative source of truth:
- `docs/planning/work/ideas/<initiative-slug>/SHAPE.md`
- `docs/planning/work/ideas/<initiative-slug>/SHAPE.json`
- if only legacy `BRAINSTORM.*` exists, read it and migrate forward into `SHAPE.*`

`SHAPE.json` minimum fields:
- `schemaVersion`, `initiative`, `slug`, `problem`, `constraints[]`, `globalDecisions[]`, `researchRefs[]`, `openQuestions[]`, `candidateFeatures[]`, `recommendedSequence[]`, `feedbackInbox[]`, `timestamp`
- each `candidateFeatures[]` entry needs `slug`, `displayName`, `userOutcome`, `scopeSummary`, `dependencies[]`, `risks[]`, `priority`, `status`, `readinessReason`, `handoffSummary`
- valid `status`: `draft`, `ready`, `blocked`, `parked`
- optional: `decisionLog[]`, `shapeThreads[]`, `nextShapeMoves[]`

4. Materialize ready-for-line features immediately:
- for each `ready` candidate, create `docs/planning/work/features/<feature-slug>/FEATURE.md`
- create matching `FEATURE.json` with `parentShape` linkage plus inherited outcome, scope, dependencies, risks, priority, readiness, and handoff fields
- create `docs/planning/work/features/<feature-slug>/CONTEXT.md`
- create matching `CONTEXT.json` so planning can start from a stable dossier immediately
- queue the feature into the assembly line by running `python3 .cnogo/scripts/workflow_memory.py work-sync <feature-slug>`
- do not use `/discuss`; shape already owns the readiness conversation

5. Optional scouts:
- never use `/team` inside `/shape`
- stay single-agent
- use `shape-scout`, `architecture-scout`, and `risk-challenger` only as read-only scouts
- spawn at most 3 read-only scouts total:
  - `/spawn shape-scout <question>` for fit
  - `/spawn architecture-scout <question>` for option comparison
  - `/spawn risk-challenger <question>` to pressure-test the favored direction
- scouts must not edit artifacts, branch, commit, or touch memory state
- require a concise answer plus final `SCOUT_REPORT: {...}` with `kind`, `question`, `confidence`, `summary`, `implication`, and `sources[]`
- fold back only useful evidence into `SHAPE.*`

6. Validate:
```bash
python3 .cnogo/scripts/workflow_validate.py --json
```

## Output

- initiative workspace summary
- stable cross-feature decisions and active shaping threads
- feature queue snapshot with any `ready` features that were materialized
- stay-in-shape continuation moves first
- assembly-line visibility second: queued or leased features, priority, and any new feedback for shape
