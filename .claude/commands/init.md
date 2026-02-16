# Init
<!-- effort: medium -->

Bootstrap workflow config and templates for this repo.

## Arguments

`/init` or `/init force`

## Your Task

1. Detect packages and write workflow metadata:
```bash
python3 scripts/workflow_detect.py --write-workflow
```
If this fails, fall back to manifest scan (`package.json`, `pyproject.toml`, `pom.xml`, `go.mod`, `Cargo.toml`) and continue.

2. Determine stack template:
- Java: `docs/templates/CLAUDE-java.md`
- TypeScript/JavaScript: `docs/templates/CLAUDE-typescript.md`
- Python: `docs/templates/CLAUDE-python.md`
- Go: `docs/templates/CLAUDE-go.md`
- Rust: `docs/templates/CLAUDE-rust.md`
- Fallback: `docs/templates/CLAUDE-generic.md`

3. Populate `CLAUDE.md` from template.
- If `CLAUDE.md` exists and differs from `docs/templates/CLAUDE-generic.md`, ask before overwrite.
- If argument is `force`, overwrite without prompt.

4. Gather/confirm project metadata (name, one-line description, owner) and update the top project section in `CLAUDE.md`.

5. If `docs/planning/WORKFLOW.json` has multiple `packages[]`, add a concise monorepo quick-reference block to `CLAUDE.md`:
- package path
- language/kind
- build/test/lint/run commands

6. Validate and report:
```bash
python3 scripts/workflow_validate.py --json
```
Treat `ERROR` as blocking. Surface `WARN` with exact file paths.

## Output

- Detected stack and repo shape (single package vs monorepo/polyglot)
- Files changed (`CLAUDE.md`, `docs/planning/WORKFLOW.json`)
- Any validation warnings/errors and next fix
