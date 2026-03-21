#!/bin/bash

# cnogo Installer v3
# Usage: ./install.sh [OPTIONS] /path/to/your/project
#   -y, --yes         Auto-accept merge with existing directories
#   --update          Update an existing cnogo installation (including newly added managed files)
#   --uninstall       Remove cnogo from a project (keeps seeded files)
#   --force           Uninstall + fresh install
#   --from <path>     Source cnogo repo (default: directory containing this script)
#   -h, --help        Show help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    cat <<'EOF'
Usage: ./install.sh [OPTIONS] /path/to/your/project

Options:
  -y, --yes         Auto-accept merge with existing directories
  --update          Update an existing cnogo installation (including newly added managed files)
  --uninstall       Remove cnogo from a project (keeps seeded files)
  --force           Uninstall + fresh install
  --from <path>     Source cnogo repo (default: directory containing this script)
  --skip-graph      Skip installation of graph module pip dependencies
  -h, --help        Show this help message
EOF
}

# Parse arguments
AUTO_YES=false
ACTION="install"
SOURCE_OVERRIDE=""
TARGET_DIR=""
MANAGED_PATHS=()
SKIP_GRAPH=false

track_managed_path() {
    MANAGED_PATHS+=("$1")
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        --update)
            ACTION="update"
            shift
            ;;
        --uninstall)
            ACTION="uninstall"
            shift
            ;;
        --force)
            ACTION="force"
            shift
            ;;
        --from)
            SOURCE_OVERRIDE="$2"
            shift 2
            ;;
        --skip-graph)
            SKIP_GRAPH=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            echo ""
            usage
            exit 1
            ;;
        *)
            if [ -n "$TARGET_DIR" ]; then
                echo -e "${RED}Error: Multiple target directories provided${NC}"
                echo ""
                usage
                exit 1
            fi
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

TARGET_DIR="${TARGET_DIR:-.}"
if [ -n "$SOURCE_OVERRIDE" ]; then
    SCRIPT_DIR="$(cd "$SOURCE_OVERRIDE" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
COMMAND_COUNT=0
AGENT_COUNT=0

# =============================================================================
# Lifecycle helpers (shared by install, update, uninstall)
# =============================================================================

settings_merge() {
    # Remove hook entries with _cnogo marker from settings.json
    local settings_file="$1"
    local mode="$2"  # "remove" to strip _cnogo hooks

    if [ ! -f "$settings_file" ]; then
        return
    fi

    if [ "$mode" = "remove" ]; then
        # Use python3 to safely manipulate JSON — remove hooks with _cnogo: true
        python3 -c "
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
for key in ['hooks', 'permissions']:
    if key == 'hooks' and key in data:
        for event_type in list(data['hooks']):
            hooks = data['hooks'][event_type]
            if isinstance(hooks, list):
                data['hooks'][event_type] = [h for h in hooks if not (isinstance(h, dict) and h.get('_cnogo'))]
                if not data['hooks'][event_type]:
                    del data['hooks'][event_type]
        if not data['hooks']:
            del data['hooks']
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" "$settings_file" 2>/dev/null || echo -e "   ${YELLOW}⚠️  Could not clean settings.json hooks${NC}"
    fi
}

manifest_category_for_path() {
    local path="$1"
    case "$path" in
        CLAUDE.md|CHANGELOG.md|docs/planning/PROJECT.md|docs/planning/ROADMAP.md)
            echo "seeded"
            ;;
        .claude/settings.json|.gitignore)
            echo "merged"
            ;;
        docs/planning/work/*/.gitkeep|docs/planning/archive/*/.gitkeep)
            echo "scaffold"
            ;;
        *)
            echo "managed"
            ;;
    esac
}

emit_manifest_paths_for_tree() {
    local base="$1"

    [ -f "$base/.claude/settings.json" ] && echo ".claude/settings.json"
    for f in "$base/.claude/commands/"*.md; do
        [ -f "$f" ] && echo ".claude/commands/$(basename "$f")"
    done
    for f in "$base/.claude/agents/"*.md; do
        [ -f "$f" ] && echo ".claude/agents/$(basename "$f")"
    done
    [ -f "$base/.claude/agent-memory/.gitkeep" ] && echo ".claude/agent-memory/.gitkeep"

    for f in "$base/.cnogo/scripts/"*.py; do
        [ -f "$f" ] && echo ".cnogo/scripts/$(basename "$f")"
    done
    for f in "$base/.cnogo/scripts/memory/"*.py; do
        [ -f "$f" ] && echo ".cnogo/scripts/memory/$(basename "$f")"
    done
    for f in "$base/.cnogo/scripts/context/"*.py; do
        [ -f "$f" ] && echo ".cnogo/scripts/context/$(basename "$f")"
    done
    if [ -d "$base/.cnogo/scripts/context/phases" ]; then
        for f in "$base/.cnogo/scripts/context/phases/"*.py; do
            [ -f "$f" ] && echo ".cnogo/scripts/context/phases/$(basename "$f")"
        done
    fi
    if [ -d "$base/.cnogo/scripts/workflow" ]; then
        while IFS= read -r f; do
            rel="${f#$base/}"
            echo "$rel"
        done < <(find "$base/.cnogo/scripts/workflow" -type f -name '*.py' | sort)
    fi
    [ -f "$base/.cnogo/requirements-graph.txt" ] && echo ".cnogo/requirements-graph.txt"

    [ -f "$base/.cnogo/hooks/_bootstrap.py" ] && echo ".cnogo/hooks/_bootstrap.py"
    for f in "$base/.cnogo/hooks/"hook-*.sh "$base/.cnogo/hooks/"hook-*.py; do
        [ -f "$f" ] && echo ".cnogo/hooks/$(basename "$f")"
    done
    [ -f "$base/.cnogo/hooks/install-githooks.sh" ] && echo ".cnogo/hooks/install-githooks.sh"

    for f in "$base/.cnogo/templates/"*.md "$base/.cnogo/templates/"*.json; do
        [ -f "$f" ] && echo ".cnogo/templates/$(basename "$f")"
    done

    [ -f "$base/.github/CODEOWNERS" ] && echo ".github/CODEOWNERS"
    [ -f "$base/.github/PULL_REQUEST_TEMPLATE.md" ] && echo ".github/PULL_REQUEST_TEMPLATE.md"

    for f in PROJECT.md ROADMAP.md WORKFLOW.json WORKFLOW.schema.json; do
        [ -f "$base/docs/planning/$f" ] && echo "docs/planning/$f"
    done
    [ -f "$base/docs/planning/adr/ADR-TEMPLATE.md" ] && echo "docs/planning/adr/ADR-TEMPLATE.md"
    [ -f "$base/docs/planning/work/features/CONTEXT-TEMPLATE.md" ] && echo "docs/planning/work/features/CONTEXT-TEMPLATE.md"
    for dir in work/quick work/features work/debug work/background work/review work/research work/ideas archive/features; do
        [ -f "$base/docs/planning/$dir/.gitkeep" ] && echo "docs/planning/$dir/.gitkeep"
    done

    [ -f "$base/CLAUDE.md" ] && echo "CLAUDE.md"
    [ -f "$base/.claude/CLAUDE.md" ] && echo ".claude/CLAUDE.md"
    [ -f "$base/CHANGELOG.md" ] && echo "CHANGELOG.md"

    for f in "$base/.claude/skills/"*.md; do
        [ -f "$f" ] && echo ".claude/skills/$(basename "$f")"
    done
    for skill_dir in "$base/.claude/skills/"*; do
        [ -d "$skill_dir" ] || continue
        [ -f "$skill_dir/SKILL.md" ] || continue
        while IFS= read -r skill_file; do
            echo "${skill_file#$base/}"
        done < <(find "$skill_dir" -type f | sort)
    done

    [ -f "$base/.gitignore" ] && echo ".gitignore"
}

CNOGO_BLOCK="# >>> cnogo
# Memory engine runtime (SQLite binary — not diffable)
.cnogo/memory.db
.cnogo/memory.db-wal
.cnogo/memory.db-shm
.cnogo/tee/
.cnogo/command-usage.jsonl

# Worktree session state (transient, contains absolute paths)
.cnogo/worktree-session.json

# Compaction checkpoint (runtime snapshot, not source)
.cnogo/compaction-checkpoint.json

# Validation baselines (per-branch runtime snapshots)
.cnogo/validate-baseline.json
.cnogo/validate-latest.json

# Context graph (rebuild from source)
.cnogo/graph.db

# Graph venv (auto-managed, rebuild via install.sh)
.cnogo/.venv/

# Task description cache (generated, not source)
.cnogo/task-descriptions-*.json
.cnogo/prompt-*.md
# <<< cnogo"

gitignore_merge() {
    local target_gitignore="$1"
    local block_content="$2"

    if [ ! -f "$target_gitignore" ]; then
        echo "$block_content" > "$target_gitignore"
        echo "   ✅ Created .gitignore with cnogo block"
        return
    fi

    if grep -q '# >>> cnogo' "$target_gitignore"; then
        sed -i '' '/^# >>> cnogo$/,/^# <<< cnogo$/d' "$target_gitignore" 2>/dev/null || \
        sed -i '/^# >>> cnogo$/,/^# <<< cnogo$/d' "$target_gitignore"
        sed -i '' -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$target_gitignore" 2>/dev/null || true
    fi

    echo "" >> "$target_gitignore"
    echo "$block_content" >> "$target_gitignore"
    echo "   ✅ Updated .gitignore cnogo block"
}

generate_manifest() {
    local target="$1"
    local manifest_file="$target/.cnogo/manifest.json"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    echo '{'                                          > "$manifest_file"
    echo '  "schemaVersion": 1,'                     >> "$manifest_file"
    echo "  \"generatedAt\": \"$timestamp\","        >> "$manifest_file"
    echo '  "files": ['                              >> "$manifest_file"

    local first=true
    for p in "${MANAGED_PATHS[@]}"; do
        local full_path="$target/$p"
        if [ ! -f "$full_path" ]; then
            continue
        fi

        local category
        category=$(manifest_category_for_path "$p")

        local sha
        sha=$(shasum -a 256 "$full_path" | awk '{print $1}')

        if [ "$first" = true ]; then
            first=false
        else
            echo ','                                 >> "$manifest_file"
        fi
        printf '    {"path": "%s", "category": "%s", "sha256": "%s"}' "$p" "$category" "$sha" >> "$manifest_file"
    done

    echo ''                                          >> "$manifest_file"
    echo '  ]'                                       >> "$manifest_file"
    echo '}'                                         >> "$manifest_file"

    echo "   ✅ Generated .cnogo/manifest.json (${#MANAGED_PATHS[@]} files tracked)"
}

generate_version() {
    local target="$1"
    local source="$2"
    local version_file="$target/.cnogo/version.json"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local version="dev"
    if command -v git &>/dev/null && [ -d "$source/.git" ]; then
        version=$(git -C "$source" describe --tags --abbrev=0 2>/dev/null || echo "dev")
    fi

    local source_commit="unknown"
    if command -v git &>/dev/null && [ -d "$source/.git" ]; then
        source_commit=$(git -C "$source" rev-parse HEAD 2>/dev/null || echo "unknown")
    fi

    local source_url="local"
    if command -v git &>/dev/null && [ -d "$source/.git" ]; then
        source_url=$(git -C "$source" remote get-url origin 2>/dev/null || echo "local")
    fi

    cat > "$version_file" <<VEOF
{
  "schemaVersion": 1,
  "version": "$version",
  "sourceCommit": "$source_commit",
  "source": "$source_url",
  "installedAt": "$timestamp"
}
VEOF

    echo "   ✅ Generated .cnogo/version.json (version: $version)"
}

# =============================================================================
# do_uninstall — Remove cnogo from a project
# =============================================================================

do_uninstall() {
    local target="$1"
    local manifest_file="$target/.cnogo/manifest.json"

    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  cnogo Uninstaller                         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -f "$manifest_file" ]; then
        echo -e "${RED}Error: No manifest.json found — is cnogo installed in $target?${NC}"
        exit 1
    fi

    # Parse manifest to get file list and categories
    local removed=0
    local kept=0

    # Extract paths and categories from manifest
    while IFS= read -r line; do
        local path category
        path=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['path'])" 2>/dev/null) || continue
        category=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['category'])" 2>/dev/null) || continue

        local full_path="$target/$path"

        case "$category" in
            managed)
                if [ -f "$full_path" ]; then
                    rm -f "$full_path"
                    echo "   🗑  $path (managed — removed)"
                    removed=$((removed + 1))
                fi
                ;;
            seeded)
                echo -e "   📄 $path ${YELLOW}(seeded — kept)${NC}"
                kept=$((kept + 1))
                ;;
            merged)
                # Special handling for merged files
                if [ "$path" = ".gitignore" ]; then
                    # Remove cnogo block from .gitignore
                    local target_gitignore="$target/.gitignore"
                    if [ -f "$target_gitignore" ] && grep -q '# >>> cnogo' "$target_gitignore"; then
                        sed -i '' '/^# >>> cnogo$/,/^# <<< cnogo$/d' "$target_gitignore" 2>/dev/null || \
                        sed -i '/^# >>> cnogo$/,/^# <<< cnogo$/d' "$target_gitignore"
                        echo "   📄 .gitignore (cnogo block removed)"
                    fi
                elif [ "$path" = ".claude/settings.json" ]; then
                    settings_merge "$full_path" "remove"
                    echo "   📄 .claude/settings.json (_cnogo hooks removed)"
                fi
                ;;
            scaffold)
                if [ -f "$full_path" ]; then
                    rm -f "$full_path"
                    echo "   🗑  $path (scaffold — removed)"
                    removed=$((removed + 1))
                fi
                ;;
        esac
    done < <(python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for entry in data['files']:
    print(json.dumps(entry))
" "$manifest_file")

    # Remove .cnogo directory (runtime + managed files)
    if [ -d "$target/.cnogo" ]; then
        rm -rf "$target/.cnogo"
        echo "   🗑  .cnogo/ (directory removed)"
    fi

    # Clean up empty directories
    for dir in "$target/.claude/commands" "$target/.claude/agents" "$target/.claude/skills" "$target/.claude/agent-memory"; do
        if [ -d "$dir" ] && [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
            rmdir "$dir" 2>/dev/null || true
        fi
    done
    if [ -d "$target/.claude" ] && [ -z "$(ls -A "$target/.claude" 2>/dev/null)" ]; then
        rmdir "$target/.claude" 2>/dev/null || true
    fi

    echo ""
    echo -e "${GREEN}Uninstall complete: $removed files removed, $kept seeded files kept${NC}"
}

# =============================================================================
# do_update — Update managed files only
# =============================================================================

do_update() {
    local target="$1"
    local source="$2"
    local manifest_file="$target/.cnogo/manifest.json"

    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  cnogo Updater                             ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -f "$manifest_file" ]; then
        echo -e "${RED}Error: No manifest.json found — is cnogo installed in $target?${NC}"
        echo "Run install.sh without --update for a fresh install."
        exit 1
    fi

    local timestamp
    timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
    local backup_dir="$target/.cnogo/backup/$timestamp"
    local updated=0
    local skipped=0
    local backed_up=0
    local old_manifest_entries desired_manifest_entries
    old_manifest_entries=$(mktemp)
    desired_manifest_entries=$(mktemp)

    python3 -c "
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for entry in data['files']:
    print(f\"{entry['path']}\t{entry['category']}\t{entry['sha256']}\")
" "$manifest_file" > "$old_manifest_entries"

    while IFS= read -r path; do
        [ -n "$path" ] || continue
        printf '%s\t%s\n' "$path" "$(manifest_category_for_path "$path")" >> "$desired_manifest_entries"
    done < <(emit_manifest_paths_for_tree "$source" | sort -u)

    while IFS=$'\t' read -r path category; do
        [ -n "$path" ] || continue

        local full_target="$target/$path"
        local full_source="$source/$path"
        local old_sha
        old_sha=$(awk -F '\t' -v p="$path" '$1==p {print $3; exit}' "$old_manifest_entries")

        case "$category" in
            merged)
                continue
                ;;
            seeded|scaffold)
                if [ ! -f "$full_target" ] && [ -f "$full_source" ]; then
                    mkdir -p "$(dirname "$full_target")"
                    cp "$full_source" "$full_target"
                    echo "   ➕ $path (added)"
                    updated=$((updated + 1))
                else
                    skipped=$((skipped + 1))
                fi
                continue
                ;;
        esac

        if [ ! -f "$full_source" ]; then
            continue
        fi

        local source_sha=""
        source_sha=$(shasum -a 256 "$full_source" | awk '{print $1}')

        if [ -f "$full_target" ]; then
            local current_sha
            current_sha=$(shasum -a 256 "$full_target" | awk '{print $1}')
            if [ -n "$old_sha" ]; then
                if [ "$current_sha" != "$old_sha" ]; then
                    mkdir -p "$backup_dir/$(dirname "$path")"
                    cp "$full_target" "$backup_dir/$path"
                    echo -e "   💾 $path ${YELLOW}(user-modified — backed up)${NC}"
                    backed_up=$((backed_up + 1))
                fi
            elif [ "$current_sha" != "$source_sha" ]; then
                mkdir -p "$backup_dir/$(dirname "$path")"
                cp "$full_target" "$backup_dir/$path"
                echo -e "   💾 $path ${YELLOW}(pre-existing — backed up before cnogo takes ownership)${NC}"
                backed_up=$((backed_up + 1))
            fi
        fi

        mkdir -p "$(dirname "$full_target")"
        cp "$full_source" "$full_target"
        case "$path" in
            .cnogo/hooks/*.sh) chmod +x "$full_target" ;;
        esac
        updated=$((updated + 1))
    done < "$desired_manifest_entries"

    while IFS=$'\t' read -r path category old_sha; do
        [ -n "$path" ] || continue
        [ "$category" = "managed" ] || continue
        if awk -F '\t' -v p="$path" '$1==p {found=1; exit} END{exit !found}' "$desired_manifest_entries"; then
            continue
        fi

        local full_target="$target/$path"
        if [ -f "$full_target" ]; then
            mkdir -p "$backup_dir/$(dirname "$path")"
            cp "$full_target" "$backup_dir/$path" 2>/dev/null || true
            rm -f "$full_target"
            echo "   🗑  $path (removed in new version, backed up)"
            backed_up=$((backed_up + 1))
        fi
    done < "$old_manifest_entries"

    # Re-merge settings.json and .gitignore
    echo ""
    echo "📄 Re-merging settings.json and .gitignore..."
    # Settings: re-copy (update will overwrite — merged file is always cnogo's)
    if [ -f "$source/.claude/settings.json" ]; then
        cp "$source/.claude/settings.json" "$target/.claude/settings.json"
        echo "   ✅ settings.json updated"
    fi
    # Gitignore: re-apply block
    gitignore_merge "$target/.gitignore" "$CNOGO_BLOCK"

    # Regenerate manifest and version
    echo ""
    echo "📋 Regenerating manifest & version..."
    # Reset MANAGED_PATHS and re-collect from source
    MANAGED_PATHS=()
    while IFS= read -r path; do
        [ -n "$path" ] && MANAGED_PATHS+=("$path")
    done < <(emit_manifest_paths_for_tree "$source" | sort -u)
    generate_manifest "$target"
    generate_version "$target" "$source"

    # Refresh graph venv deps if venv exists
    local graph_venv_pip="$target/.cnogo/.venv/bin/pip"
    local graph_req="$target/.cnogo/requirements-graph.txt"
    if [ -f "$graph_venv_pip" ] && [ -f "$graph_req" ]; then
        echo ""
        echo "📦 Refreshing graph venv deps..."
        if "$graph_venv_pip" install -r "$graph_req" --quiet 2>/dev/null; then
            echo -e "   ${GREEN}Graph deps updated${NC}"
        else
            echo -e "   ${YELLOW}Graph deps update failed — run manually: $graph_venv_pip install -r $graph_req${NC}"
        fi
    fi

    echo ""
    if [ $backed_up -gt 0 ]; then
        echo -e "${YELLOW}Backups saved to: $backup_dir${NC}"
    fi
    echo -e "${GREEN}Update complete: $updated files updated, $backed_up backed up${NC}"

    rm -f "$old_manifest_entries" "$desired_manifest_entries"
}

# =============================================================================
# Route to lifecycle operation
# =============================================================================

if [ "$ACTION" = "uninstall" ]; then
    do_uninstall "$TARGET_DIR"
    exit 0
fi
if [ "$ACTION" = "update" ]; then
    do_update "$TARGET_DIR" "$SCRIPT_DIR"
    exit 0
fi
if [ "$ACTION" = "force" ]; then
    echo -e "${BLUE}Force reinstall: uninstalling first...${NC}"
    do_uninstall "$TARGET_DIR"
    echo ""
    echo -e "${BLUE}Now installing fresh...${NC}"
    echo ""
    # Fall through to install
fi

# Resolve absolute paths for self-host detection
RESOLVED_SOURCE="$(cd "$SCRIPT_DIR" && pwd -P)"
RESOLVED_TARGET="$(cd "$TARGET_DIR" 2>/dev/null && pwd -P || echo "")"
SELF_HOST=false
if [ -n "$RESOLVED_TARGET" ] && [ "$RESOLVED_SOURCE" = "$RESOLVED_TARGET" ]; then
    SELF_HOST=true
fi

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  cnogo Installer v3.0                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Source: $SCRIPT_DIR"
echo "Target: $TARGET_DIR"
if [ "$SELF_HOST" = true ]; then
    echo -e "${YELLOW}(self-host mode — skipping file copies)${NC}"
fi
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
# Self-host mode: skip copies, build managed paths from existing files
# =============================================================================
if [ "$SELF_HOST" = true ]; then
    echo "📋 Self-host: scanning existing files for manifest..."

    # .claude directory
    [ -f "$TARGET_DIR/.claude/settings.json" ] && track_managed_path ".claude/settings.json"
    for f in "$TARGET_DIR/.claude/commands/"*.md; do
        [ -f "$f" ] && track_managed_path ".claude/commands/$(basename "$f")" && COMMAND_COUNT=$((COMMAND_COUNT + 1))
    done
    for f in "$TARGET_DIR/.claude/agents/"*.md; do
        [ -f "$f" ] && track_managed_path ".claude/agents/$(basename "$f")" && AGENT_COUNT=$((AGENT_COUNT + 1))
    done
    [ -f "$TARGET_DIR/.claude/agent-memory/.gitkeep" ] && track_managed_path ".claude/agent-memory/.gitkeep"

    # .cnogo/scripts
    for f in "$TARGET_DIR/.cnogo/scripts/"*.py; do
        [ -f "$f" ] && track_managed_path ".cnogo/scripts/$(basename "$f")"
    done
    for f in "$TARGET_DIR/.cnogo/scripts/memory/"*.py; do
        [ -f "$f" ] && track_managed_path ".cnogo/scripts/memory/$(basename "$f")"
    done
    for f in "$TARGET_DIR/.cnogo/scripts/context/"*.py; do
        [ -f "$f" ] && track_managed_path ".cnogo/scripts/context/$(basename "$f")"
    done
    if [ -d "$TARGET_DIR/.cnogo/scripts/context/phases" ]; then
        for f in "$TARGET_DIR/.cnogo/scripts/context/phases/"*.py; do
            [ -f "$f" ] && track_managed_path ".cnogo/scripts/context/phases/$(basename "$f")"
        done
    fi
    if [ -d "$TARGET_DIR/.cnogo/scripts/workflow" ]; then
        while IFS= read -r f; do
            rel="${f#$TARGET_DIR/}"
            track_managed_path "$rel"
        done < <(find "$TARGET_DIR/.cnogo/scripts/workflow" -type f -name '*.py' | sort)
    fi

    # .cnogo/requirements-graph.txt
    [ -f "$TARGET_DIR/.cnogo/requirements-graph.txt" ] && track_managed_path ".cnogo/requirements-graph.txt"

    # .cnogo/hooks
    for f in "$TARGET_DIR/.cnogo/hooks/"*.py "$TARGET_DIR/.cnogo/hooks/"*.sh; do
        [ -f "$f" ] && track_managed_path ".cnogo/hooks/$(basename "$f")"
    done

    # .cnogo/templates
    for f in "$TARGET_DIR/.cnogo/templates/"*.md "$TARGET_DIR/.cnogo/templates/"*.json; do
        [ -f "$f" ] && track_managed_path ".cnogo/templates/$(basename "$f")"
    done

    # .github
    [ -f "$TARGET_DIR/.github/CODEOWNERS" ] && track_managed_path ".github/CODEOWNERS"
    [ -f "$TARGET_DIR/.github/PULL_REQUEST_TEMPLATE.md" ] && track_managed_path ".github/PULL_REQUEST_TEMPLATE.md"

    # docs/planning
    for f in PROJECT.md ROADMAP.md; do
        [ -f "$TARGET_DIR/docs/planning/$f" ] && track_managed_path "docs/planning/$f"
    done
    [ -f "$TARGET_DIR/docs/planning/WORKFLOW.json" ] && track_managed_path "docs/planning/WORKFLOW.json"
    [ -f "$TARGET_DIR/docs/planning/WORKFLOW.schema.json" ] && track_managed_path "docs/planning/WORKFLOW.schema.json"
    [ -f "$TARGET_DIR/docs/planning/adr/ADR-TEMPLATE.md" ] && track_managed_path "docs/planning/adr/ADR-TEMPLATE.md"
    [ -f "$TARGET_DIR/docs/planning/work/features/CONTEXT-TEMPLATE.md" ] && track_managed_path "docs/planning/work/features/CONTEXT-TEMPLATE.md"
    for dir in work/quick work/features work/debug work/background work/review work/research work/ideas archive/features; do
        [ -f "$TARGET_DIR/docs/planning/$dir/.gitkeep" ] && track_managed_path "docs/planning/$dir/.gitkeep"
    done

    # Root files
    [ -f "$TARGET_DIR/CLAUDE.md" ] && track_managed_path "CLAUDE.md"
    [ -f "$TARGET_DIR/.claude/CLAUDE.md" ] && track_managed_path ".claude/CLAUDE.md"
    [ -f "$TARGET_DIR/CHANGELOG.md" ] && track_managed_path "CHANGELOG.md"

    # Skills
    for f in "$TARGET_DIR/.claude/skills/"*.md; do
        [ -f "$f" ] && track_managed_path ".claude/skills/$(basename "$f")"
    done
    for skill_dir in "$TARGET_DIR/.claude/skills/"*; do
        [ -d "$skill_dir" ] || continue
        [ -f "$skill_dir/SKILL.md" ] || continue
        while IFS= read -r skill_file; do
            rel="${skill_file#$TARGET_DIR/}"
            track_managed_path "$rel"
        done < <(find "$skill_dir" -type f | sort)
    done

    track_managed_path ".gitignore"

    echo "   Found ${#MANAGED_PATHS[@]} files"
    echo ""

    # Jump to post-install: memory init, gitignore, manifest, version
    # (uses shared code below the copy sections)
fi

# =============================================================================
# .claude directory (skip in self-host mode)
# =============================================================================
if [ "$SELF_HOST" = false ]; then
echo "📁 .claude/"
mkdir -p "$TARGET_DIR/.claude/commands"
if [ ! -f "$TARGET_DIR/.claude/settings.json" ]; then
    cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET_DIR/.claude/"
    echo "   ├── settings.json (hooks + permissions)"
else
    echo -e "   ├── settings.json ${YELLOW}(skipped - exists)${NC}"
fi
track_managed_path ".claude/settings.json"

for cmd in "$SCRIPT_DIR/.claude/commands/"*.md; do
    cp "$cmd" "$TARGET_DIR/.claude/commands/"
    echo "   ├── commands/$(basename "$cmd")"
    track_managed_path ".claude/commands/$(basename "$cmd")"
    COMMAND_COUNT=$((COMMAND_COUNT + 1))
done

# Migrate legacy cnogo /init command to avoid collisions with global /init commands.
LEGACY_INIT="$TARGET_DIR/.claude/commands/init.md"
if [ -f "$LEGACY_INIT" ]; then
    if grep -q "^# Init" "$LEGACY_INIT" && grep -q "python3 .cnogo/scripts/workflow_detect.py --write-workflow" "$LEGACY_INIT"; then
        rm -f "$LEGACY_INIT"
        echo -e "   ├── commands/init.md ${YELLOW}(removed legacy cnogo command; use /cnogo-init)${NC}"
    else
        echo -e "   ├── commands/init.md ${YELLOW}(kept existing custom command; cnogo setup uses /cnogo-init)${NC}"
    fi
fi

# Agent definitions
mkdir -p "$TARGET_DIR/.claude/agents"
for agent in "$SCRIPT_DIR/.claude/agents/"*.md; do
    cp "$agent" "$TARGET_DIR/.claude/agents/"
    # Extract model tier from frontmatter
    MODEL=$(grep '^model:' "$agent" 2>/dev/null | head -1 | awk '{print $2}' || echo "inherit")
    echo "   ├── agents/$(basename "$agent") ($MODEL)"
    track_managed_path ".claude/agents/$(basename "$agent")"
    AGENT_COUNT=$((AGENT_COUNT + 1))
done

# Agent memory scaffolding (project scope, checked in)
mkdir -p "$TARGET_DIR/.claude/agent-memory"
touch "$TARGET_DIR/.claude/agent-memory/.gitkeep"
echo "   └── agent-memory/ (project scope)"
track_managed_path ".claude/agent-memory/.gitkeep"

# =============================================================================
# .cnogo/scripts directory (Python runtime)
# =============================================================================
echo ""
echo "📁 .cnogo/scripts/"
mkdir -p "$TARGET_DIR/.cnogo/scripts"

# Copy _bootstrap.py first
cp "$SCRIPT_DIR/.cnogo/scripts/_bootstrap.py" "$TARGET_DIR/.cnogo/scripts/"
echo "   ├── _bootstrap.py"
track_managed_path ".cnogo/scripts/_bootstrap.py"

# Workflow scripts
for script in "$SCRIPT_DIR/.cnogo/scripts/"*.py; do
    if [ -f "$script" ]; then
        cp "$script" "$TARGET_DIR/.cnogo/scripts/"
        echo "   ├── $(basename "$script")"
        track_managed_path ".cnogo/scripts/$(basename "$script")"
    fi
done

# Memory engine package
mkdir -p "$TARGET_DIR/.cnogo/scripts/memory"
for mem in "$SCRIPT_DIR/.cnogo/scripts/memory/"*.py; do
    if [ -f "$mem" ]; then
        cp "$mem" "$TARGET_DIR/.cnogo/scripts/memory/"
        echo "   ├── memory/$(basename "$mem")"
        track_managed_path ".cnogo/scripts/memory/$(basename "$mem")"
    fi
done
echo "   ├── memory/ (memory engine package)"

# Context graph package
mkdir -p "$TARGET_DIR/.cnogo/scripts/context"
for ctx in "$SCRIPT_DIR/.cnogo/scripts/context/"*.py; do
    if [ -f "$ctx" ]; then
        cp "$ctx" "$TARGET_DIR/.cnogo/scripts/context/"
        track_managed_path ".cnogo/scripts/context/$(basename "$ctx")"
    fi
done
# Context phases subpackage
if [ -d "$SCRIPT_DIR/.cnogo/scripts/context/phases" ]; then
    mkdir -p "$TARGET_DIR/.cnogo/scripts/context/phases"
    for phase in "$SCRIPT_DIR/.cnogo/scripts/context/phases/"*.py; do
        if [ -f "$phase" ]; then
            cp "$phase" "$TARGET_DIR/.cnogo/scripts/context/phases/"
            track_managed_path ".cnogo/scripts/context/phases/$(basename "$phase")"
        fi
    done
fi
if [ -d "$SCRIPT_DIR/.cnogo/scripts/workflow" ]; then
    while IFS= read -r workflow_file; do
        rel="${workflow_file#$SCRIPT_DIR/.cnogo/scripts/}"
        mkdir -p "$TARGET_DIR/.cnogo/scripts/$(dirname "$rel")"
        cp "$workflow_file" "$TARGET_DIR/.cnogo/scripts/$rel"
        track_managed_path ".cnogo/scripts/$rel"
    done < <(find "$SCRIPT_DIR/.cnogo/scripts/workflow" -type f -name '*.py' | sort)
fi
echo "   └── context/ (context graph package)"

# Graph requirements file
if [ -f "$SCRIPT_DIR/.cnogo/requirements-graph.txt" ]; then
    cp "$SCRIPT_DIR/.cnogo/requirements-graph.txt" "$TARGET_DIR/.cnogo/"
    echo "   └── requirements-graph.txt"
    track_managed_path ".cnogo/requirements-graph.txt"
fi

# =============================================================================
# .cnogo/hooks directory
# =============================================================================
echo ""
echo "📁 .cnogo/hooks/"
mkdir -p "$TARGET_DIR/.cnogo/hooks"

# Copy _bootstrap.py for hooks
cp "$SCRIPT_DIR/.cnogo/hooks/_bootstrap.py" "$TARGET_DIR/.cnogo/hooks/"
echo "   ├── _bootstrap.py"
track_managed_path ".cnogo/hooks/_bootstrap.py"

for hook in "$SCRIPT_DIR/.cnogo/hooks/hook-"*.sh; do
    if [ -f "$hook" ]; then
        cp "$hook" "$TARGET_DIR/.cnogo/hooks/"
        chmod +x "$TARGET_DIR/.cnogo/hooks/$(basename "$hook")"
        echo "   ├── $(basename "$hook")"
        track_managed_path ".cnogo/hooks/$(basename "$hook")"
    fi
done

for hook in "$SCRIPT_DIR/.cnogo/hooks/hook-"*.py; do
    if [ -f "$hook" ]; then
        cp "$hook" "$TARGET_DIR/.cnogo/hooks/"
        echo "   ├── $(basename "$hook")"
        track_managed_path ".cnogo/hooks/$(basename "$hook")"
    fi
done

if [ -f "$SCRIPT_DIR/.cnogo/hooks/install-githooks.sh" ]; then
    cp "$SCRIPT_DIR/.cnogo/hooks/install-githooks.sh" "$TARGET_DIR/.cnogo/hooks/"
    chmod +x "$TARGET_DIR/.cnogo/hooks/install-githooks.sh"
    echo "   └── install-githooks.sh"
    track_managed_path ".cnogo/hooks/install-githooks.sh"
fi

# =============================================================================
# .cnogo/templates directory
# =============================================================================
echo ""
echo "📁 .cnogo/templates/"
mkdir -p "$TARGET_DIR/.cnogo/templates"

for template in "$SCRIPT_DIR/.cnogo/templates/"*.md "$SCRIPT_DIR/.cnogo/templates/"*.json; do
    if [ -f "$template" ]; then
        cp "$template" "$TARGET_DIR/.cnogo/templates/"
        echo "   ├── $(basename "$template")"
        track_managed_path ".cnogo/templates/$(basename "$template")"
    fi
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
    track_managed_path ".github/CODEOWNERS"
else
    echo -e "   ├── CODEOWNERS ${YELLOW}(skipped - exists)${NC}"
fi

if [ ! -f "$TARGET_DIR/.github/PULL_REQUEST_TEMPLATE.md" ]; then
    cp "$SCRIPT_DIR/.github/PULL_REQUEST_TEMPLATE.md" "$TARGET_DIR/.github/"
    echo "   └── PULL_REQUEST_TEMPLATE.md"
    track_managed_path ".github/PULL_REQUEST_TEMPLATE.md"
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

for file in PROJECT.md ROADMAP.md; do
    if [ ! -f "$TARGET_DIR/docs/planning/$file" ]; then
        TEMPLATE_NAME="${file%.*}-TEMPLATE.${file##*.}"
        cp "$SCRIPT_DIR/.cnogo/templates/$TEMPLATE_NAME" "$TARGET_DIR/docs/planning/$file"
        echo "   ├── $file"
    else
        echo -e "   ├── $file ${YELLOW}(skipped - exists)${NC}"
    fi
    track_managed_path "docs/planning/$file"
done

# WORKFLOW.json from template
if [ ! -f "$TARGET_DIR/docs/planning/WORKFLOW.json" ]; then
    cp "$SCRIPT_DIR/.cnogo/templates/WORKFLOW-TEMPLATE.json" "$TARGET_DIR/docs/planning/WORKFLOW.json"
    echo "   ├── WORKFLOW.json"
else
    echo -e "   ├── WORKFLOW.json ${YELLOW}(skipped - exists)${NC}"
fi
track_managed_path "docs/planning/WORKFLOW.json"

if [ ! -f "$TARGET_DIR/docs/planning/WORKFLOW.schema.json" ]; then
    cp "$SCRIPT_DIR/docs/planning/WORKFLOW.schema.json" "$TARGET_DIR/docs/planning/WORKFLOW.schema.json"
    echo "   ├── WORKFLOW.schema.json"
else
    echo -e "   ├── WORKFLOW.schema.json ${YELLOW}(skipped - exists)${NC}"
fi
track_managed_path "docs/planning/WORKFLOW.schema.json"

# Migration: remove STATE.md if it exists (replaced by memory engine)
if [ -f "$TARGET_DIR/docs/planning/STATE.md" ]; then
    rm "$TARGET_DIR/docs/planning/STATE.md"
    echo -e "   ├── STATE.md ${YELLOW}(deleted — replaced by memory engine)${NC}"
fi

cp "$SCRIPT_DIR/docs/planning/adr/ADR-TEMPLATE.md" "$TARGET_DIR/docs/planning/adr/"
echo "   ├── adr/ADR-TEMPLATE.md"
track_managed_path "docs/planning/adr/ADR-TEMPLATE.md"

cp "$SCRIPT_DIR/docs/planning/work/features/CONTEXT-TEMPLATE.md" "$TARGET_DIR/docs/planning/work/features/"
echo "   └── work/features/CONTEXT-TEMPLATE.md"
track_managed_path "docs/planning/work/features/CONTEXT-TEMPLATE.md"

# .gitkeep files
touch "$TARGET_DIR/docs/planning/work/quick/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/features/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/debug/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/background/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/review/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/research/.gitkeep"
touch "$TARGET_DIR/docs/planning/work/ideas/.gitkeep"
touch "$TARGET_DIR/docs/planning/archive/features/.gitkeep"
track_managed_path "docs/planning/work/quick/.gitkeep"
track_managed_path "docs/planning/work/features/.gitkeep"
track_managed_path "docs/planning/work/debug/.gitkeep"
track_managed_path "docs/planning/work/background/.gitkeep"
track_managed_path "docs/planning/work/review/.gitkeep"
track_managed_path "docs/planning/work/research/.gitkeep"
track_managed_path "docs/planning/work/ideas/.gitkeep"
track_managed_path "docs/planning/archive/features/.gitkeep"

# =============================================================================
# Root files
# =============================================================================
echo ""
echo "📄 Root files"

if [ ! -f "$TARGET_DIR/CLAUDE.md" ]; then
    cp "$SCRIPT_DIR/.cnogo/templates/CLAUDE-generic.md" "$TARGET_DIR/CLAUDE.md"
    echo "   ├── CLAUDE.md (from generic template)"
    track_managed_path "CLAUDE.md"
else
    echo -e "   ├── CLAUDE.md ${YELLOW}(skipped - exists)${NC}"
fi

# Workflow docs (always overwrite — cnogo's file)
cp "$SCRIPT_DIR/.claude/CLAUDE.md" "$TARGET_DIR/.claude/CLAUDE.md"
echo "   ├── .claude/CLAUDE.md (workflow docs)"
track_managed_path ".claude/CLAUDE.md"

if [ ! -f "$TARGET_DIR/CHANGELOG.md" ]; then
    cp "$SCRIPT_DIR/CHANGELOG.md" "$TARGET_DIR/"
    echo "   └── CHANGELOG.md"
    track_managed_path "CHANGELOG.md"
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
        track_managed_path ".claude/skills/$(basename "$skill")"
    fi
done
for skill_dir in "$SCRIPT_DIR/.claude/skills/"*; do
    [ -d "$skill_dir" ] || continue
    [ -f "$skill_dir/SKILL.md" ] || continue
    SKILL_NAME="$(basename "$skill_dir")"
    mkdir -p "$TARGET_DIR/.claude/skills/$SKILL_NAME"
    while IFS= read -r skill_file; do
        rel="${skill_file#$skill_dir/}"
        mkdir -p "$TARGET_DIR/.claude/skills/$SKILL_NAME/$(dirname "$rel")"
        cp "$skill_file" "$TARGET_DIR/.claude/skills/$SKILL_NAME/$rel"
        echo "   ├── $SKILL_NAME/$rel"
        track_managed_path ".claude/skills/$SKILL_NAME/$rel"
    done < <(find "$skill_dir" -type f | sort)
done

fi  # end SELF_HOST=false block

# =============================================================================
# Initialize memory engine
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Files copied                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "🧠 Initializing memory engine..."
if command -v python3 &>/dev/null; then
    (cd "$TARGET_DIR" && python3 -c "
import sys; sys.path.insert(0, '.cnogo')
from scripts.memory import is_initialized, init
from pathlib import Path
root = Path('.')
if not is_initialized(root):
    init(root=root)
    print('   ✅ Memory engine initialized (.cnogo/memory.db)')
else:
    print('   ✅ Memory engine already initialized')
" 2>/dev/null) || echo -e "   ${YELLOW}⚠️  Memory init skipped (run manually: python3 .cnogo/scripts/workflow_memory.py init)${NC}"
else
    echo -e "   ${YELLOW}⚠️  python3 not found — run manually: python3 .cnogo/scripts/workflow_memory.py init${NC}"
fi

# =============================================================================
# Graph module dependencies (venv-managed)
# =============================================================================
echo ""
echo "📦 Graph module dependencies"
GRAPH_VENV="$TARGET_DIR/.cnogo/.venv"
GRAPH_REQ="$TARGET_DIR/.cnogo/requirements-graph.txt"
if [ "$SKIP_GRAPH" = true ]; then
    echo "   Skipped (--skip-graph flag set)"
elif [ -f "$GRAPH_REQ" ]; then
    if python3 -m venv "$GRAPH_VENV" 2>/dev/null; then
        echo "   Created venv at .cnogo/.venv/"
        if "$GRAPH_VENV/bin/pip" install -r "$GRAPH_REQ" --quiet 2>/dev/null; then
            echo -e "   ${GREEN}Graph deps installed in venv${NC}"
        else
            echo -e "   ${YELLOW}Graph deps install failed — run manually:${NC}"
            echo -e "   ${YELLOW}  $GRAPH_VENV/bin/pip install -r .cnogo/requirements-graph.txt${NC}"
        fi
    else
        echo -e "   ${YELLOW}Venv creation failed — run manually:${NC}"
        echo -e "   ${YELLOW}  python3 -m venv $GRAPH_VENV${NC}"
        echo -e "   ${YELLOW}  $GRAPH_VENV/bin/pip install -r .cnogo/requirements-graph.txt${NC}"
    fi
else
    echo -e "   ${YELLOW}requirements-graph.txt not found — skipping${NC}"
fi

# =============================================================================
# .gitignore entries (block markers)
# =============================================================================
echo ""
echo "📄 .gitignore entries"
GITIGNORE="$TARGET_DIR/.gitignore"

gitignore_merge "$GITIGNORE" "$CNOGO_BLOCK"
track_managed_path ".gitignore"

echo ""
echo "📋 Manifest & Version"
generate_manifest "$TARGET_DIR"
generate_version "$TARGET_DIR" "$SCRIPT_DIR"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Installation complete                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Run '/cnogo-init' to auto-detect your stack and populate CLAUDE.md"
echo "  2. Edit docs/planning/PROJECT.md with your project details"
echo "  3. Edit .github/CODEOWNERS with your team structure"
echo "  4. Run 'claude' and verify with /status"
echo "  5. Run '/spawn' to view available subagents"
echo ""
echo "Commands installed (${COMMAND_COUNT}):"
echo ""
echo "  Core:     /shape  /discuss  /plan  /implement  /verify  /verify-ci  /review  /ship"
echo "  Fast:     /quick  /tdd"
echo "  Session:  /status  /pause  /resume  /sync  /context"
echo "  Debug:    /debug  /bug  /rollback"
echo "  Release:  /changelog  /release  /close"
echo "  Research: /research  /brainstorm"
echo "  Setup:    /cnogo-init  /validate"
echo "  MCP:      /mcp"
echo "  Agents:   /spawn  /team  /background  (${AGENT_COUNT} agent definitions)"
echo ""
echo "Hooks installed:"
echo "  • PreToolUse:    Security validation (blocks dangerous commands)"
echo "  • PreToolUse:    Token optimization telemetry + suggestions"
echo "  • SubagentStop:  Teammate completion logging"
echo "  • PostToolUse:   Auto-format on edit (stack-detected)"
echo "  • PreToolUse:    Secret scanning on 'git commit'"
echo "  • PostToolUse:   Commit confirmation on 'git commit'"
echo ""
