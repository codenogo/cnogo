# Plan 01: Extract Templates + Update install.sh

## Goal
Move the 3 dual-purpose files to `docs/templates/` as `*-TEMPLATE` files and update `install.sh` to copy from there.

## Prerequisites
- [x] `/discuss template-self-separation` complete

## Tasks

### Task 1: Create template files in docs/templates/
**Files:** `docs/templates/PROJECT-TEMPLATE.md`, `docs/templates/ROADMAP-TEMPLATE.md`, `docs/templates/WORKFLOW-TEMPLATE.json`
**Action:**
Copy the current content of each file verbatim:
- `docs/planning/PROJECT.md` → `docs/templates/PROJECT-TEMPLATE.md`
- `docs/planning/ROADMAP.md` → `docs/templates/ROADMAP-TEMPLATE.md`
- `docs/planning/WORKFLOW.json` → `docs/templates/WORKFLOW-TEMPLATE.json`

Content must be byte-identical to the current files. These are the templates that `install.sh` will copy to new projects.

**Verify:**
```bash
diff docs/planning/PROJECT.md docs/templates/PROJECT-TEMPLATE.md && diff docs/planning/ROADMAP.md docs/templates/ROADMAP-TEMPLATE.md && diff docs/planning/WORKFLOW.json docs/templates/WORKFLOW-TEMPLATE.json && echo "PASS: templates match originals"
```

**Done when:** All 3 template files exist in `docs/templates/` and are identical to their sources.

### Task 2: Update install.sh copy sources
**Files:** `install.sh`
**Action:**
Change the `for file in` loop at line 177 to copy from `docs/templates/` instead of `docs/planning/`:

Current (line 177-184):
```bash
for file in PROJECT.md ROADMAP.md WORKFLOW.json; do
    if [ ! -f "$TARGET_DIR/docs/planning/$file" ]; then
        cp "$SCRIPT_DIR/docs/planning/$file" "$TARGET_DIR/docs/planning/"
```

Change to:
```bash
for file in PROJECT.md ROADMAP.md WORKFLOW.json; do
    if [ ! -f "$TARGET_DIR/docs/planning/$file" ]; then
        cp "$SCRIPT_DIR/docs/templates/${file%.*}-TEMPLATE.${file##*.}" "$TARGET_DIR/docs/planning/"
```

This maps: `PROJECT.md` → `PROJECT-TEMPLATE.md`, `ROADMAP.md` → `ROADMAP-TEMPLATE.md`, `WORKFLOW.json` → `WORKFLOW-TEMPLATE.json`.

**Verify:**
```bash
grep -n "TEMPLATE" install.sh && echo "PASS: install.sh references templates"
```

**Done when:** install.sh copies from `docs/templates/*-TEMPLATE.*` instead of `docs/planning/`.

### Task 3: Verify install.sh still works end-to-end
**Files:** `install.sh`
**Action:**
Run a dry-run install to a temporary directory and verify:
1. PROJECT.md, ROADMAP.md, WORKFLOW.json are installed correctly
2. Content matches the templates (not cnogo's filled-in docs)
3. Skip-if-exists logic still works

**Verify:**
```bash
TMPDIR=$(mktemp -d) && bash install.sh -y "$TMPDIR" && diff "$TMPDIR/docs/planning/PROJECT.md" docs/templates/PROJECT-TEMPLATE.md && diff "$TMPDIR/docs/planning/ROADMAP.md" docs/templates/ROADMAP-TEMPLATE.md && diff "$TMPDIR/docs/planning/WORKFLOW.json" docs/templates/WORKFLOW-TEMPLATE.json && echo "PASS: install produces template content" && rm -rf "$TMPDIR"
```

**Done when:** Fresh install produces template content, not cnogo's own docs.

## Verification

After all tasks:
```bash
# Templates exist and match originals
diff docs/planning/PROJECT.md docs/templates/PROJECT-TEMPLATE.md
diff docs/planning/ROADMAP.md docs/templates/ROADMAP-TEMPLATE.md
diff docs/planning/WORKFLOW.json docs/templates/WORKFLOW-TEMPLATE.json

# install.sh uses template paths
grep "TEMPLATE" install.sh

# Fresh install produces templates
TMPDIR=$(mktemp -d) && bash install.sh -y "$TMPDIR" && diff "$TMPDIR/docs/planning/PROJECT.md" docs/templates/PROJECT-TEMPLATE.md && diff "$TMPDIR/docs/planning/ROADMAP.md" docs/templates/ROADMAP-TEMPLATE.md && diff "$TMPDIR/docs/planning/WORKFLOW.json" docs/templates/WORKFLOW-TEMPLATE.json && rm -rf "$TMPDIR"

# Workflow validation
python3 scripts/workflow_validate.py
```

## Commit Message
```
feat(template-self-separation): extract install templates to docs/templates/

- Copy PROJECT.md, ROADMAP.md, WORKFLOW.json as *-TEMPLATE files
- Update install.sh to copy from docs/templates/ instead of docs/planning/
- cnogo's own docs/planning/ files are now free to contain real content
```

---
*Planned: 2026-02-14*
