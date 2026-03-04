# Workflow Deep-Dive V2

Second systematic audit of the cnogo workflow engine, covering scripts, commands, skills, documentation, and architecture.

## Findings Summary

- **HIGH**: 7 (data integrity, validation correctness, config accuracy)
- **MEDIUM**: 22 (state machine, phase system, command consistency, missing capabilities)
- **LOW**: 21 (DRY violations, docs staleness, cosmetic)
- **Total**: 50 unique findings after deduplication

## Proposed Phases

### Phase 1: Data Integrity & Correctness (HIGH)
- H1: SQLite-JSONL transaction isolation
- H3: Bool type checking pattern (8 locations in validate_core.py)
- H4: Silent hook telemetry failures (add stderr logging)
- H6: SQL injection in PRAGMA (add table allowlist)

### Phase 2: Memory Engine & State Machine (HIGH + MEDIUM)
- H7: Phase transition validation (enforce forward-only)
- H2: Plan validation gate before task creation
- M1: Phase/state unification or coordination
- M2: Status/state column redundancy
- M3: Session reconcile reliability

### Phase 3: Config & Validation (HIGH + MEDIUM)
- H5: WORKFLOW.json undefined agent specializations
- M4: Validation enforcement mode
- M8: Performance-review self-reference
- M9: Memory API methods verification
- M19: Ship-ready phase check

### Phase 4: Command Consistency (MEDIUM)
- M10: Step numbering standardization
- M11: Implement.md Step 2a gap
- M12: Review stage gate clarification
- M13: Phase transitions state machine docs
- M14: Error recovery paths
- M22: Quick scope boundaries

### Phase 5: Architecture Improvements (MEDIUM)
- M15: Rollback/undo capability
- M18: Memory operation hooks
- M20: Graph failure alerting
- M21: Worktree isolation docs

### Phase 6: Documentation & Polish (LOW)
- L1: DRY rationalization patterns
- L6-L10: Command formatting
- L16-L21: Docs updates
- M17: ROADMAP/PROJECT.md staleness

## Constraints

- stdlib-only Python
- Max 3 tasks per plan
- Must migrate memory DB safely
- workflow_validate.py must pass

## Open Questions

1. Should `status` column be deprecated? (migration risk)
2. Strict vs advisory phase transitions?
3. CI/CD integration scope?
4. Rollback: full feature or just phase revert?
