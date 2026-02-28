#!/bin/bash

# cnogo Remote Installer
# Installs cnogo into a project by cloning the repo, running install.sh, and cleaning up.
#
# Usage (public repo):
#   curl -sL https://raw.githubusercontent.com/codenogo/workflowy/main/remote-install.sh | bash -s -- /path/to/project
#
# Usage (private repo with SSH):
#   bash remote-install.sh /path/to/project
#   bash remote-install.sh --ref v1.0 /path/to/project
#
# Options:
#   --ref <tag|branch>   Pin to a specific git ref (default: main)
#   --update             Update an existing cnogo installation
#   --uninstall          Remove cnogo from a project
#   --force              Uninstall + fresh install
#   -y, --yes            Auto-accept prompts
#   -h, --help           Show this help message

set -e

REPO_SSH="git@github.com:codenogo/workflowy.git"
REPO_HTTPS="https://github.com/codenogo/workflowy.git"
REF="main"
TARGET_DIR=""
PASSTHROUGH_ARGS=()

usage() {
    cat <<'EOF'
cnogo Remote Installer

Usage: remote-install.sh [OPTIONS] /path/to/project

Options:
  --ref <tag|branch>   Pin to a specific git ref (default: main)
  --update             Update an existing cnogo installation
  --uninstall          Remove cnogo from a project
  --force              Uninstall + fresh install
  -y, --yes            Auto-accept prompts
  -h, --help           Show this help message

Examples:
  # Install into current directory
  bash remote-install.sh .

  # Install a specific version
  bash remote-install.sh --ref v1.0 /path/to/project

  # Update existing installation
  bash remote-install.sh --update /path/to/project

  # One-liner (when repo is public)
  curl -sL https://raw.githubusercontent.com/codenogo/workflowy/main/remote-install.sh | bash -s -- .
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ref)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --ref requires a value (tag or branch name)" >&2
                exit 1
            fi
            REF="$2"
            shift 2
            ;;
        --update|--uninstall|--force)
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
        -y|--yes)
            PASSTHROUGH_ARGS+=("$1")
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1" >&2
            echo "" >&2
            usage >&2
            exit 1
            ;;
        *)
            if [[ -n "$TARGET_DIR" ]]; then
                echo "Error: Multiple target directories provided" >&2
                exit 1
            fi
            TARGET_DIR="$1"
            shift
            ;;
    esac
done

if [[ -z "$TARGET_DIR" ]]; then
    echo "Error: No target directory specified" >&2
    echo "" >&2
    usage >&2
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Target directory does not exist: $TARGET_DIR" >&2
    exit 1
fi

# Create temp directory and ensure cleanup on exit
TMPDIR_CLONE="$(mktemp -d)"
cleanup() {
    rm -rf "$TMPDIR_CLONE"
}
trap cleanup EXIT

echo "cnogo remote installer"
echo "  Target: $TARGET_DIR"
echo "  Ref:    $REF"
echo ""

# Clone the repo — try SSH first, fall back to HTTPS
echo "Cloning cnogo repository..."
if git clone --quiet --depth 1 --branch "$REF" "$REPO_SSH" "$TMPDIR_CLONE" 2>/dev/null; then
    echo "  Cloned via SSH"
elif git clone --quiet --depth 1 --branch "$REF" "$REPO_HTTPS" "$TMPDIR_CLONE" 2>/dev/null; then
    echo "  Cloned via HTTPS"
else
    echo "Error: Failed to clone cnogo repository" >&2
    echo "" >&2
    echo "Tried:" >&2
    echo "  SSH:   $REPO_SSH (ref: $REF)" >&2
    echo "  HTTPS: $REPO_HTTPS (ref: $REF)" >&2
    echo "" >&2
    echo "Check that:" >&2
    echo "  - You have access to the repository" >&2
    echo "  - The ref '$REF' exists" >&2
    echo "  - git is installed and in your PATH" >&2
    exit 1
fi

# Run install.sh from the cloned repo
echo ""
echo "Running install.sh..."
echo ""
bash "$TMPDIR_CLONE/install.sh" --from "$TMPDIR_CLONE" "${PASSTHROUGH_ARGS[@]}" "$TARGET_DIR"
