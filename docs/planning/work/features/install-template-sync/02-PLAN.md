# Plan 02: Fix install.sh + Stack Templates

## Goal
Sync install.sh with the new file structure and clean up stack templates.

## Prerequisites
- [ ] Plan 01 complete (CLAUDE-generic.md and .claude/CLAUDE.md must exist)

## Tasks

### Task 1: Replace stale `docs/skills.md` block with `.claude/skills/` loop
**Files:** `install.sh`
**Action:**
Remove lines 236-247 (the `docs/skills.md` copy block):

```bash
# docs/skills.md
# ...
echo "📄 Skills library"
mkdir -p "$TARGET_DIR/docs"
if [ ! -f "$TARGET_DIR/docs/skills.md" ]; then
    cp "$SCRIPT_DIR/docs/skills.md" "$TARGET_DIR/docs/"
    echo "   └── docs/skills.md"
else
    echo -e "   └── docs/skills.md ${YELLOW}(skipped - exists)${NC}"
fi
```

Replace with a `.claude/skills/` copy loop (always overwrite — cnogo's files):

```bash
# =============================================================================
# .claude/skills directory
# =============================================================================
echo ""
echo "📁 .claude/skills/"
mkdir -p "$TARGET_DIR/.claude/skills"
for skill in "$SCRIPT_DIR/.claude/skills/"*.md; do
    if [ -f "$skill" ]; then
        cp "$skill" "$TARGET_DIR/.claude/skills/"
        echo "   ├── $(basename "$skill")"
    fi
done
```

**Verify:**
```bash
grep -q ".claude/skills/" install.sh && echo "has skills loop" || echo "FAIL"
! grep -q "docs/skills.md" install.sh && echo "no stale ref" || echo "FAIL"
```

**Done when:** install.sh copies `.claude/skills/*.md` instead of `docs/skills.md`.

### Task 2: Fix CLAUDE.md copy source + add `.claude/CLAUDE.md` + fix agent count
**Files:** `install.sh`
**Action:**
Three changes in install.sh:

**2a.** Change CLAUDE.md copy source (lines 222-227). Replace:
```bash
if [ ! -f "$TARGET_DIR/CLAUDE.md" ]; then
    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/"
```
With:
```bash
if [ ! -f "$TARGET_DIR/CLAUDE.md" ]; then
    cp "$SCRIPT_DIR/docs/templates/CLAUDE-generic.md" "$TARGET_DIR/CLAUDE.md"
```

**2b.** Add `.claude/CLAUDE.md` always-overwrite copy. Insert after the CLAUDE.md block (after line 227):
```bash
# Workflow docs (always overwrite — cnogo's file)
cp "$SCRIPT_DIR/.claude/CLAUDE.md" "$TARGET_DIR/.claude/CLAUDE.md"
echo "   ├── .claude/CLAUDE.md (workflow docs)"
```

**2c.** Fix agent count on line 274. Change:
```
echo "  Agents:   /spawn  /team  /background  (10 agent definitions)"
```
To:
```
echo "  Agents:   /spawn  /team  /background  (2 agent definitions)"
```

**Verify:**
```bash
grep -q "CLAUDE-generic.md" install.sh && echo "generic source: OK" || echo "FAIL"
grep -q '.claude/CLAUDE.md' install.sh && echo "workflow copy: OK" || echo "FAIL"
grep -q "2 agent definitions" install.sh && echo "agent count: OK" || echo "FAIL"
! grep -q "10 agent definitions" install.sh && echo "no stale count" || echo "FAIL"
```

**Done when:** install.sh copies from CLAUDE-generic.md, always writes .claude/CLAUDE.md, says "2 agent definitions".

### Task 3: Remove Planning Docs section from all 5 stack templates
**Files:** `docs/templates/CLAUDE-python.md`, `docs/templates/CLAUDE-java.md`, `docs/templates/CLAUDE-typescript.md`, `docs/templates/CLAUDE-go.md`, `docs/templates/CLAUDE-rust.md`
**Action:**
Remove the trailing Planning Docs section from each template. Each has an identical block at the end:

```markdown
---

## Planning Docs

- Project vision: `docs/planning/PROJECT.md`
- Current state: `docs/planning/STATE.md`
- Roadmap: `docs/planning/ROADMAP.md`
- Feature work: `docs/planning/work/features/`
- Quick tasks: `docs/planning/work/quick/`
```

Line ranges:
- CLAUDE-python.md: lines 139-148
- CLAUDE-java.md: lines 127-136
- CLAUDE-typescript.md: lines 135-144
- CLAUDE-go.md: lines 155-164
- CLAUDE-rust.md: lines 172-181

Per CONTEXT.md decision: "All workflow references live in `.claude/CLAUDE.md` — single source of truth."

**Verify:**
```bash
for f in docs/templates/CLAUDE-*.md; do
    if grep -q "Planning Docs" "$f"; then
        echo "FAIL: $f still has Planning Docs"
    else
        echo "OK: $f"
    fi
done
```

**Done when:** No stack template contains a "Planning Docs" section.

## Verification

After all tasks:
```bash
grep -q ".claude/skills/" install.sh && echo "skills loop: OK"
grep -q "CLAUDE-generic.md" install.sh && echo "generic source: OK"
grep -q "2 agent definitions" install.sh && echo "agent count: OK"
! grep -q "docs/skills.md" install.sh && echo "no stale skills ref: OK"
for f in docs/templates/CLAUDE-*.md; do ! grep -q "Planning Docs" "$f" && echo "OK: $f"; done
bash -n install.sh && echo "syntax: OK"
```

## Commit Message
```
fix(install-template-sync): sync install.sh with redesigned architecture

- Replace stale docs/skills.md copy with .claude/skills/ loop
- Source CLAUDE.md from CLAUDE-generic.md template
- Always install .claude/CLAUDE.md workflow docs
- Fix agent count 10 → 2
- Remove Planning Docs from stack templates (now in .claude/CLAUDE.md)
```

---
*Planned: 2026-02-14*
