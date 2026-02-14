#!/bin/bash

# Universal Workflow Pack Installer v2
# Usage: ./install.sh [OPTIONS] /path/to/your/project
#   -y, --yes    Auto-accept merge with existing directories

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
AUTO_YES=false
TARGET_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        *)
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

TARGET_DIR="${TARGET_DIR:-.}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
    if [ "$AUTO_YES" = true ]; then
        echo "Auto-accepting merge (-y flag)"
    else
        read -p "Merge with existing? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
    fi
fi

echo -e "${GREEN}Installing...${NC}"
echo ""

# =============================================================================
# .claude directory
# =============================================================================
echo "📁 .claude/"
mkdir -p "$TARGET_DIR/.claude/commands"
if [ ! -f "$TARGET_DIR/.claude/settings.json" ]; then
    cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/"
    echo "   ├── settings.json (hooks + permissions)"
else
    echo -e "   ├── settings.json ${YELLOW}(skipped - exists)${NC}"
fi

for cmd in "$SCRIPT_DIR/.claude/commands/"*.md; do
    cp "$cmd" "$TARGET_DIR/.claude/commands/"
    echo "   ├── commands/$(basename "$cmd")"
done

# Agent definitions
mkdir -p "$TARGET_DIR/.claude/agents"
for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
    cp "$agent" "$TARGET_DIR/.claude/agents/"
    # Extract model tier from frontmatter
    MODEL=$(grep '^model:' "$agent" 2>/dev/null | head -1 | awk '{print $2}' || echo "inherit")
    echo "   ├── agents/$(basename "$agent") ($MODEL)"
done

# Agent memory scaffolding (project scope, checked in)
mkdir -p "$TARGET_DIR/.claude/agent-memory"
touch "$TARGET_DIR/.claude/agent-memory/.gitkeep"
echo "   └── agent-memory/ (project scope)"

# =============================================================================
# scripts directory
# =============================================================================
echo ""
echo "📁 scripts/"
mkdir -p "$TARGET_DIR/scripts"

for script in "$SCRIPT_DIR/scripts/"*.py; do
    if [ -f "$script" ]; then
        cp "$script" "$TARGET_DIR/scripts/"
        echo "   ├── $(basename "$script")"
    fi
done

for hook in "$SCRIPT_DIR/scripts/hook-"*.sh; do
    if [ -f "$hook" ]; then
        cp "$hook" "$TARGET_DIR/scripts/"
        chmod +x "$TARGET_DIR/scripts/$(basename "$hook")"
        echo "   ├── $(basename "$hook")"
    fi
done

if [ -f "$SCRIPT_DIR/scripts/install-githooks.sh" ]; then
    cp "$SCRIPT_DIR/scripts/install-githooks.sh" "$TARGET_DIR/scripts/"
    chmod +x "$TARGET_DIR/scripts/install-githooks.sh"
    echo "   ├── install-githooks.sh"
fi

# Memory engine package
mkdir -p "$TARGET_DIR/scripts/memory"
for mem in "$SCRIPT_DIR/scripts/memory/"*.py; do
    if [ -f "$mem" ]; then
        cp "$mem" "$TARGET_DIR/scripts/memory/"
        echo "   ├── memory/$(basename "$mem")"
    fi
done
echo "   └── memory/ (memory engine package)"

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

for file in PROJECT.md ROADMAP.md WORKFLOW.json; do
    if [ ! -f "$TARGET_DIR/docs/planning/$file" ]; then
        cp "$SCRIPT_DIR/docs/planning/$file" "$TARGET_DIR/docs/planning/"
        echo "   ├── $file"
    else
        echo -e "   ├── $file ${YELLOW}(skipped - exists)${NC}"
    fi
done

# Migration: remove STATE.md if it exists (replaced by memory engine)
if [ -f "$TARGET_DIR/docs/planning/STATE.md" ]; then
    rm "$TARGET_DIR/docs/planning/STATE.md"
    echo -e "   ├── STATE.md ${YELLOW}(deleted — replaced by memory engine)${NC}"
fi

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

for template in CLAUDE-generic.md CLAUDE-java.md CLAUDE-typescript.md CLAUDE-python.md CLAUDE-go.md CLAUDE-rust.md; do
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
    cp "$SCRIPT_DIR/docs/templates/CLAUDE-generic.md" "$TARGET_DIR/CLAUDE.md"
    echo "   ├── CLAUDE.md (from generic template)"
else
    echo -e "   ├── CLAUDE.md ${YELLOW}(skipped - exists)${NC}"
fi

# Workflow docs (always overwrite — cnogo's file)
cp "$SCRIPT_DIR/.claude/CLAUDE.md" "$TARGET_DIR/.claude/CLAUDE.md"
echo "   ├── .claude/CLAUDE.md (workflow docs)"

if [ ! -f "$TARGET_DIR/CHANGELOG.md" ]; then
    cp "$SCRIPT_DIR/CHANGELOG.md" "$TARGET_DIR/"
    echo "   └── CHANGELOG.md"
else
    echo -e "   └── CHANGELOG.md ${YELLOW}(skipped - exists)${NC}"
fi

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

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Installation complete                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
# Initialize memory engine
echo ""
echo "🧠 Initializing memory engine..."
if command -v python3 &>/dev/null; then
    (cd "$TARGET_DIR" && python3 -c "
import sys; sys.path.insert(0, '.')
from scripts.memory import is_initialized, init
from pathlib import Path
root = Path('.')
if not is_initialized(root):
    init(root=root)
    print('   ✅ Memory engine initialized (.cnogo/memory.db)')
else:
    print('   ✅ Memory engine already initialized')
" 2>/dev/null) || echo -e "   ${YELLOW}⚠️  Memory init skipped (run manually: python3 scripts/workflow_memory.py init)${NC}"
else
    echo -e "   ${YELLOW}⚠️  python3 not found — run manually: python3 scripts/workflow_memory.py init${NC}"
fi

echo ""
echo "Next steps:"
echo "  1. Run '/init' to auto-detect your stack and populate CLAUDE.md"
echo "  2. Edit docs/planning/PROJECT.md with your project details"
echo "  3. Edit .github/CODEOWNERS with your team structure"
echo "  4. Run 'claude' and verify with /status"
echo "  5. Run '/spawn' to view available subagents"
echo ""
echo "Commands installed (28):"
echo ""
echo "  Core:     /discuss  /plan  /implement  /verify  /review  /ship"
echo "  Fast:     /quick  /tdd"
echo "  Session:  /status  /pause  /resume  /sync  /context"
echo "  Debug:    /debug  /bug  /rollback"
echo "  Release:  /changelog  /release  /close"
echo "  Research: /research  /brainstorm"
echo "  Setup:    /init  /validate"
echo "  MCP:      /mcp"
echo "  Agents:   /spawn  /team  /background  (2 agent definitions)"
echo ""
echo "Hooks installed:"
echo "  • PreToolUse:    Security validation (blocks dangerous commands)"
echo "  • SubagentStop:  Teammate completion logging"
echo "  • PostToolUse:   Auto-format on edit (stack-detected)"
echo "  • PreCommit:     Secret scanning"
echo "  • PostCommit:    Commit confirmation"
echo ""
