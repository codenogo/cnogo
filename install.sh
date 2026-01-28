#!/bin/bash

# Universal Workflow Pack Installer v2
# Usage: ./install.sh /path/to/your/project

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-.}"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Universal Workflow Pack Installer v2.0    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Target: $TARGET_DIR"
echo ""

# Check if target exists
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}Error: Target directory does not exist: $TARGET_DIR${NC}"
    exit 1
fi

# Check for existing directories
EXISTING=""
[ -d "$TARGET_DIR/.claude" ] && EXISTING="${EXISTING}.claude "
[ -d "$TARGET_DIR/.github" ] && EXISTING="${EXISTING}.github "
[ -d "$TARGET_DIR/docs/planning" ] && EXISTING="${EXISTING}docs/planning "

if [ -n "$EXISTING" ]; then
    echo -e "${YELLOW}Warning: The following already exist: ${EXISTING}${NC}"
    read -p "Merge with existing? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo -e "${GREEN}Installing...${NC}"
echo ""

# =============================================================================
# .claude directory
# =============================================================================
echo "📁 .claude/"
mkdir -p "$TARGET_DIR/.claude/commands"
cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/"
echo "   ├── settings.json (hooks + permissions)"

for cmd in "$SCRIPT_DIR/.claude/commands/"*.md; do
    cp "$cmd" "$TARGET_DIR/.claude/commands/"
    echo "   ├── commands/$(basename $cmd)"
done

# =============================================================================
# .github directory
# =============================================================================
echo ""
echo "📁 .github/"
mkdir -p "$TARGET_DIR/.github"

if [ ! -f "$TARGET_DIR/.github/CODEOWNERS" ]; then
    cp "$SCRIPT_DIR/.github/CODEOWNERS" "$TARGET_DIR/.github/"
    echo "   ├── CODEOWNERS"
else
    echo -e "   ├── CODEOWNERS ${YELLOW}(skipped - exists)${NC}"
fi

if [ ! -f "$TARGET_DIR/.github/PULL_REQUEST_TEMPLATE.md" ]; then
    cp "$SCRIPT_DIR/.github/PULL_REQUEST_TEMPLATE.md" "$TARGET_DIR/.github/"
    echo "   └── PULL_REQUEST_TEMPLATE.md"
else
    echo -e "   └── PULL_REQUEST_TEMPLATE.md ${YELLOW}(skipped - exists)${NC}"
fi

# =============================================================================
# docs/planning directory
# =============================================================================
echo ""
echo "📁 docs/planning/"
mkdir -p "$TARGET_DIR/docs/planning/work/quick"
mkdir -p "$TARGET_DIR/docs/planning/work/features"
mkdir -p "$TARGET_DIR/docs/planning/work/debug"
mkdir -p "$TARGET_DIR/docs/planning/work/background"
mkdir -p "$TARGET_DIR/docs/planning/work/review"
mkdir -p "$TARGET_DIR/docs/planning/work/research"
mkdir -p "$TARGET_DIR/docs/planning/work/ideas"
mkdir -p "$TARGET_DIR/docs/planning/archive/features"
mkdir -p "$TARGET_DIR/docs/planning/adr"

for file in PROJECT.md STATE.md ROADMAP.md WORKFLOW.json; do
    if [ ! -f "$TARGET_DIR/docs/planning/$file" ]; then
        cp "$SCRIPT_DIR/docs/planning/$file" "$TARGET_DIR/docs/planning/"
        echo "   ├── $file"
    else
        echo -e "   ├── $file ${YELLOW}(skipped - exists)${NC}"
    fi
done

cp "$SCRIPT_DIR/docs/planning/adr/ADR-TEMPLATE.md" "$TARGET_DIR/docs/planning/adr/"
echo "   ├── adr/ADR-TEMPLATE.md"

cp "$SCRIPT_DIR/docs/planning/work/features/CONTEXT-TEMPLATE.md" "$TARGET_DIR/docs/planning/work/features/"
echo "   └── work/features/CONTEXT-TEMPLATE.md"

# .gitkeep files
touch "$TARGET_DIR/docs/planning/work/quick/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/features/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/debug/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/background/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/review/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/research/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/ideas/.gitkeep"
touch "$TARGET_DIR/docs/planning/archive/features/.gitkeep"

# =============================================================================
# docs/templates directory
# =============================================================================
echo ""
echo "📁 docs/templates/"
mkdir -p "$TARGET_DIR/docs/templates"

for template in CLAUDE-java.md CLAUDE-typescript.md CLAUDE-python.md CLAUDE-go.md CLAUDE-rust.md; do
    if [ -f "$SCRIPT_DIR/docs/templates/$template" ]; then
        cp "$SCRIPT_DIR/docs/templates/$template" "$TARGET_DIR/docs/templates/"
        echo "   ├── $template"
    fi
done

# =============================================================================
# Root files
# =============================================================================
echo ""
echo "📄 Root files"

if [ ! -f "$TARGET_DIR/CLAUDE.md" ]; then
    cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET_DIR/"
    echo "   ├── CLAUDE.md"
else
    echo -e "   ├── CLAUDE.md ${YELLOW}(skipped - exists)${NC}"
fi

if [ ! -f "$TARGET_DIR/CHANGELOG.md" ]; then
    cp "$SCRIPT_DIR/CHANGELOG.md" "$TARGET_DIR/"
    echo "   └── CHANGELOG.md"
else
    echo -e "   └── CHANGELOG.md ${YELLOW}(skipped - exists)${NC}"
fi

# =============================================================================
# docs/skills.md
# =============================================================================
echo ""
echo "📄 Skills library"
mkdir -p "$TARGET_DIR/docs"
if [ ! -f "$TARGET_DIR/docs/skills.md" ]; then
    cp "$SCRIPT_DIR/docs/skills.md" "$TARGET_DIR/docs/"
    echo "   └── docs/skills.md"
else
    echo -e "   └── docs/skills.md ${YELLOW}(skipped - exists)${NC}"
fi

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Installation complete                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Run '/init' to auto-detect your stack and populate CLAUDE.md"
echo "  2. Edit docs/planning/PROJECT.md with your project details"
echo "  3. Edit .github/CODEOWNERS with your team structure"
echo "  4. Run 'claude' and verify with /status"
echo ""
echo "Commands installed (21):"
echo ""
echo "  Core:     /discuss  /plan  /implement  /verify  /review  /ship"
echo "  Fast:     /quick  /tdd"
echo "  Session:  /status  /pause  /resume  /sync  /context"
echo "  Debug:    /debug  /rollback"
echo "  Release:  /changelog  /release"
echo "  Setup:    /init"
echo "  MCP:      /mcp"
echo "  Agents:   /background  /spawn"
echo ""
echo "Hooks installed:"
echo "  • PreToolUse:  Security validation (blocks dangerous commands)"
echo "  • PostToolUse: Auto-format on edit (stack-detected)"
echo "  • PreCommit:   Secret scanning + tests"
echo "  • PostCommit:  Commit confirmation"
echo ""
