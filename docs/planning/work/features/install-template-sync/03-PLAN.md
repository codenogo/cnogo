# Plan 03: Fix init.md

## Goal
Make `/init` safe for existing projects and fix the unknown stack fallback.

## Prerequisites
- [ ] Plan 01 complete (CLAUDE-generic.md must exist for comparison and fallback)

## Tasks

### Task 1: Add safety check before replacing root CLAUDE.md
**Files:** `.claude/commands/init.md`
**Action:**
In Step 3 (lines 126-161), the current logic unconditionally copies the stack template over CLAUDE.md:

```bash
if [ -f "$TEMPLATE" ]; then
    echo "Using template: $TEMPLATE"
    cp "$TEMPLATE" CLAUDE.md
    echo "✅ CLAUDE.md populated with $STACK defaults"
```

Replace with a safety check that compares against the generic template. If the current CLAUDE.md has custom content (differs from the generic template), ask before overwriting:

```bash
if [ -f "$TEMPLATE" ]; then
    echo "Using template: $TEMPLATE"
    if [ -f "CLAUDE.md" ]; then
        # Check if CLAUDE.md has custom content (differs from generic template)
        GENERIC="docs/templates/CLAUDE-generic.md"
        if [ -f "$GENERIC" ] && ! diff -q "CLAUDE.md" "$GENERIC" > /dev/null 2>&1; then
            echo ""
            echo -e "${YELLOW}Your CLAUDE.md has custom content.${NC}"
            echo "The stack template ($STACK) would replace it."
            echo ""
            read -p "Replace CLAUDE.md with $STACK template? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "⏭️  Kept existing CLAUDE.md"
            else
                cp "$TEMPLATE" CLAUDE.md
                echo "✅ CLAUDE.md replaced with $STACK defaults"
            fi
        else
            cp "$TEMPLATE" CLAUDE.md
            echo "✅ CLAUDE.md populated with $STACK defaults"
        fi
    else
        cp "$TEMPLATE" CLAUDE.md
        echo "✅ CLAUDE.md populated with $STACK defaults"
    fi
```

Per CONTEXT.md decision: "If CLAUDE.md has custom content, user should decide whether to replace with stack template."

**Verify:**
```bash
grep -q "custom content" .claude/commands/init.md && echo "has safety check" || echo "FAIL"
grep -q "Replace CLAUDE.md" .claude/commands/init.md && echo "has prompt" || echo "FAIL"
grep -q "Kept existing" .claude/commands/init.md && echo "has skip path" || echo "FAIL"
```

**Done when:** init.md asks before replacing a CLAUDE.md that has custom content.

### Task 2: Fix unknown stack fallback
**Files:** `.claude/commands/init.md`
**Action:**
Change the unknown stack fallback (line 149-150) from:

```bash
    *)
        TEMPLATE="CLAUDE.md"  # Use generic template
```

To:

```bash
    *)
        TEMPLATE="docs/templates/CLAUDE-generic.md"  # Use generic template
```

Per CONTEXT.md decision: "init.md currently falls back to root CLAUDE.md which has cnogo-specific content."

**Verify:**
```bash
grep -q 'TEMPLATE="docs/templates/CLAUDE-generic.md"' .claude/commands/init.md && echo "generic fallback: OK" || echo "FAIL"
! grep 'TEMPLATE="CLAUDE.md"' .claude/commands/init.md && echo "no root fallback: OK" || echo "FAIL"
```

**Done when:** Unknown stack uses `docs/templates/CLAUDE-generic.md` instead of root CLAUDE.md.

## Verification

After all tasks:
```bash
grep -q "custom content" .claude/commands/init.md && echo "safety check: OK"
grep -q 'docs/templates/CLAUDE-generic.md' .claude/commands/init.md && echo "generic fallback: OK"
! grep 'TEMPLATE="CLAUDE.md"' .claude/commands/init.md && echo "no root fallback: OK"
```

## Commit Message
```
fix(install-template-sync): make /init safe for existing projects

- Add safety check: ask before replacing CLAUDE.md with custom content
- Fix unknown stack fallback to use CLAUDE-generic.md template
```

---
*Planned: 2026-02-14*
