# Plan 01: Add frontmatter parser to workflow_utils.py, skill validation to workflow_validate_core.py, and clean up WORKFLOW.schema.json

## Goal
Add frontmatter parser to workflow_utils.py, skill validation to workflow_validate_core.py, and clean up WORKFLOW.schema.json

## Tasks

### Task 1: Add parse_skill_frontmatter() to workflow_utils.py
**Files:** `scripts/workflow_utils.py`
**Action:**
Add a parse_skill_frontmatter(path: Path) function that reads a .md file, extracts YAML frontmatter between --- delimiters, and returns a dict with keys: name (str|None), tags (list[str]), appliesTo (list[str]), raw (str|None for the raw frontmatter block). Use regex only (no pyyaml). Handle missing/malformed frontmatter gracefully — return empty defaults, never raise. Also add discover_skills(skills_dir: Path) that scans a directory for .md files and returns list of parsed skill dicts.

**Verify:**
```bash
python3 -c "from scripts.workflow_utils import parse_skill_frontmatter; print('import ok')"
python3 -c "from scripts.workflow_utils import discover_skills; print('import ok')"
python3 -c "from pathlib import Path; from scripts.workflow_utils import parse_skill_frontmatter; r = parse_skill_frontmatter(Path('README.md')); assert r['name'] is None; print('no-frontmatter ok')"
```

**Done when:** [Observable outcome]

### Task 2: Add _validate_skills() to workflow_validate_core.py
**Files:** `scripts/workflow_validate_core.py`
**Action:**
Add _validate_skills(root, findings, touched) that: (1) scans .claude/skills/*.md for valid frontmatter (WARN if missing name field), (2) scans .claude/commands/*.md for skill path references matching '.claude/skills/*.md' pattern and checks each resolves to an existing file (WARN if broken reference). Call _validate_skills() from validate_repo() after _validate_bootstrap_context(). Import parse_skill_frontmatter and discover_skills from workflow_utils.

**Verify:**
```bash
python3 scripts/workflow_validate.py
python3 -c "from scripts.workflow_validate_core import validate_repo; print('import ok')"
```

**Done when:** [Observable outcome]

### Task 3: Update WORKFLOW.schema.json: replace karpathyChecklist with operatingPrinciples, remove reviewPrinciples
**Files:** `docs/planning/WORKFLOW.schema.json`
**Action:**
In the enforcement object properties: (1) replace the 'karpathyChecklist' key with 'operatingPrinciples' (same type/enum), (2) remove the 'reviewPrinciples' property entirely. This aligns the schema with the validator changes from review-workflow-redesign.

**Verify:**
```bash
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.schema.json')); e=d['properties']['enforcement']['properties']; assert 'operatingPrinciples' in e; assert 'karpathyChecklist' not in e; assert 'reviewPrinciples' not in e; print('schema ok')"
```

**Done when:** [Observable outcome]

## Verification

After all tasks:
```bash
python3 scripts/workflow_validate.py
python3 -c "from scripts.workflow_utils import parse_skill_frontmatter, discover_skills; print('utils ok')"
python3 -c "import json; d=json.load(open('docs/planning/WORKFLOW.schema.json')); assert 'karpathyChecklist' not in d['properties']['enforcement']['properties']; print('schema clean')"
```

## Commit Message
```
feat(skills-usage-audit): add frontmatter parser, skill validation, and schema cleanup
```
