# Verify CI: $ARGUMENTS
<!-- effort: high -->

Non-interactive verification suitable for CI, nightly runs, or pre-merge gates. This complements `/verify` (human UAT).

## Arguments

`/verify-ci <feature>`

Example: `/verify-ci websocket-notifications`

## Your Task

Verify "$ARGUMENTS" using automation-only checks and persist results.

### Step 1: Load Feature Context

```bash
cat docs/planning/work/features/$ARGUMENTS/CONTEXT.md 2>/dev/null || true
ls docs/planning/work/features/$ARGUMENTS/*-PLAN.md 2>/dev/null || true
ls docs/planning/work/features/$ARGUMENTS/*-SUMMARY.md 2>/dev/null || true
```

### Step 2: Run Automated Verification (Stack/Repo Aware)

Run what the repo supports (best-effort, do not prompt for interaction):

```bash
set -e

# Lint/format check (if present)
if [ -f pom.xml ]; then mvn -q spotless:check || true; fi
if [ -f build.gradle ] || [ -f build.gradle.kts ]; then ./gradlew -q spotlessCheck || true; fi
if [ -f package.json ]; then npm run -s lint || true; fi
if [ -f pyproject.toml ] || [ -f setup.py ]; then ruff check . 2>/dev/null || true; fi
if [ -f go.mod ]; then go vet ./... 2>/dev/null || true; fi

# Tests
if [ -f pom.xml ]; then mvn -q test -DskipITs || true; fi
if [ -f package.json ]; then npm test --silent 2>/dev/null || true; fi
if [ -f pyproject.toml ] || [ -f setup.py ]; then pytest -q --tb=short 2>/dev/null || true; fi
if [ -f go.mod ]; then go test ./... -short || true; fi
if [ -f Cargo.toml ]; then cargo test --quiet 2>/dev/null || true; fi

# Types
if [ -f tsconfig.json ]; then npx tsc --noEmit || true; fi
```

If the repo is a monorepo/polyglot (multiple manifests), prefer scoping commands:

- `cd packages/api && npm test`
- `npm --prefix packages/web test`
- `pnpm -C packages/api test`
- `mvn -f services/orders/pom.xml test`

### Step 2b: Package-Aware Execution (Recommended)

If `docs/planning/WORKFLOW.json` has `packages[]` with `commands`, run the package-aware runner:

```bash
python3 scripts/workflow_checks.py verify-ci $ARGUMENTS
```

This will execute `lint/typecheck/test` per package and write `VERIFICATION-CI.md/json` automatically.

### Step 3: Persist Verification Artifact

Create:

- `docs/planning/work/features/$ARGUMENTS/VERIFICATION-CI.md`
- `docs/planning/work/features/$ARGUMENTS/VERIFICATION-CI.json`

### Contract Rules (Apply Consistently)

- **One markdown + one JSON contract** per CI verification: `VERIFICATION-CI.md` + `VERIFICATION-CI.json`.
- **Contract required fields (minimum)**: `schemaVersion`, `feature` (slug), `timestamp`.
- **Validation**: run `python3 scripts/workflow_validate.py` after writing the artifacts.

`VERIFICATION-CI.json` contract schema (minimal):

```json
{
  "schemaVersion": 1,
  "feature": "websocket-notifications",
  "timestamp": "2026-01-24T00:00:00Z",
  "checks": [
    { "name": "tests", "result": "pass|fail|skipped" },
    { "name": "lint", "result": "pass|fail|skipped" },
    { "name": "types", "result": "pass|fail|skipped" },
    { "name": "deps", "result": "pass|warn|fail|skipped" }
  ],
  "notes": ["...optional notes..."]
}
```

### Step 4: Validate Workflow

```bash
python3 scripts/workflow_validate.py
```

## Output

- What ran and what was skipped (with reasons)
- Where the artifacts were written
- Clear next action recommendation

