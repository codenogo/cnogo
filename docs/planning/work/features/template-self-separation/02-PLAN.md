# Plan 02: Fill In cnogo's Own Documentation

## Goal
Replace placeholder content in cnogo's own PROJECT.md, ROADMAP.md, WORKFLOW.json, and CLAUDE.md with real project information.

## Prerequisites
- [ ] Plan 01 complete (templates extracted, install.sh updated)

## Tasks

### Task 1: Fill in PROJECT.md
**Files:** `docs/planning/PROJECT.md`
**Action:**
Replace all placeholder text with cnogo's real content:
- **Project name:** cnogo — Universal Development Workflow Pack
- **Vision:** A zero-dependency workflow engine for Claude Code that provides 28+ slash commands, SQLite-backed memory, and Agent Teams support
- **Constraints:** Python stdlib only, no external deps; must work with any project type; install.sh is the distribution mechanism
- **Architecture:** install.sh → .claude/commands/ + scripts/ + docs/planning/ → target project
- **Tech stack:** Python 3.10+ (stdlib only), Bash (install.sh), SQLite (memory engine), Markdown (commands/docs)
- **Patterns:** Feature slugs in kebab-case, workflow contracts (JSON + MD pairs), max 3 tasks per plan
- **Non-goals:** Not a package manager, not a CI system, not a testing framework

**Verify:**
```bash
! grep -c '\[.*\]' docs/planning/PROJECT.md | grep -v '^0$' || echo "WARN: check for remaining placeholders" && python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** PROJECT.md has zero `[placeholder]` text and accurately describes cnogo.

### Task 2: Fill in ROADMAP.md
**Files:** `docs/planning/ROADMAP.md`
**Action:**
Replace all placeholder text with cnogo's actual milestones:
- **v1.0 (Complete):** Initial release — 15 commands, secret scanning, stack detection, templates
- **v1.1 (Complete):** Extended commands — 28 total, workflow contracts, memory engine, Agent Teams, skills library
- **Completed features to list:** opus-46-agents-workflow-improvements, review-findings-remediation, team-implement-integration, agent-architecture-redesign, install-template-sync, kill-state-md, template-self-separation
- **v2.0 (Future):** Ideas from parking lot — test infrastructure, pyproject.toml, CI integration, MCP tool integrations
- Update `*Last updated*` date

**Verify:**
```bash
! grep -c '\[.*\]' docs/planning/ROADMAP.md | grep -v '^0$' || echo "WARN: check for remaining placeholders" && python3 .cnogo/scripts/workflow_validate.py
```

**Done when:** ROADMAP.md reflects cnogo's actual release history and future plans.

### Task 3: Fill in WORKFLOW.json and CLAUDE.md
**Files:** `docs/planning/WORKFLOW.json`, `CLAUDE.md`
**Action:**

**WORKFLOW.json** — Populate `packages[]` with cnogo's Python scripts:
```json
"packages": [
  {
    "name": "cnogo-scripts",
    "path": "scripts",
    "kind": "python",
    "commands": {
      "lint": "python3 -m py_compile scripts/workflow_validate.py scripts/workflow_checks.py scripts/workflow_detect.py",
      "typecheck": "",
      "test": ""
    }
  }
]
```

Note: lint uses `py_compile` since cnogo has no external linter. Test/typecheck are empty since no test infrastructure exists yet.

**CLAUDE.md (root)** — Fill in unfilled sections:
- **Conventions:** Python stdlib only, no external deps; kebab-case feature slugs; workflow contracts (JSON + MD pairs)
- **Architecture Rules Do:** Follow the command template pattern, use memory API for state, verify with workflow_validate.py
- **Architecture Rules Don't:** Don't add external Python dependencies, don't hardcode file paths (use repo_root()), don't bypass workflow contracts
- **Testing:** No test suite yet (tracked as future work); verify with `python3 .cnogo/scripts/workflow_validate.py` and `python3 -c "from scripts.memory import prime; print(prime())"`
- **Troubleshooting:** Common issues (memory not initialized, workflow validation fails, install.sh target already exists)

**Verify:**
```bash
python3 .cnogo/scripts/workflow_validate.py && python3 -c "
import json
with open('docs/planning/WORKFLOW.json') as f:
    cfg = json.load(f)
pkgs = cfg.get('packages', [])
assert len(pkgs) > 0, 'packages[] is still empty'
print(f'PASS: {len(pkgs)} package(s) configured')
"
```

**Done when:** WORKFLOW.json has populated packages[], CLAUDE.md has no `[placeholder]` text in its sections.

## Verification

After all tasks:
```bash
# No placeholder text remaining
for f in docs/planning/PROJECT.md docs/planning/ROADMAP.md CLAUDE.md; do
  echo "=== $f ===" && grep -c '\[.*\]' "$f" || echo "  0 placeholders"
done

# WORKFLOW.json has packages
python3 -c "import json; cfg=json.load(open('docs/planning/WORKFLOW.json')); assert len(cfg.get('packages',[])) > 0; print('PASS: packages populated')"

# Workflow validation
python3 .cnogo/scripts/workflow_validate.py

# Memory prime still works
python3 -c "import sys; sys.path.insert(0,'.'); from scripts.memory import prime; print(prime(root=__import__('pathlib').Path('.')))"
```

## Commit Message
```
feat(template-self-separation): fill in cnogo's own project documentation

- PROJECT.md: vision, constraints, architecture, tech stack
- ROADMAP.md: v1.0, v1.1 milestones, completed features, v2.0 ideas
- WORKFLOW.json: populate packages[] with cnogo-scripts
- CLAUDE.md: fill in conventions, architecture rules, testing, troubleshooting
```

---
*Planned: 2026-02-14*
