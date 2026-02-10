#!/bin/bash
set -e

# Sensitive file reader blocker for PreToolUse (Read)
# Warns when attempting to read files that may contain secrets.
# Uses printf instead of echo to avoid shell injection via $CLAUDE_TOOL_INPUT.

if [ -z "$CLAUDE_TOOL_INPUT" ]; then
  exit 0
fi

if printf '%s' "$CLAUDE_TOOL_INPUT" | grep -qE '(\.env$|\.env\.|credentials|secrets\.ya?ml|-prod\.ya?ml|\.pem$|\.key$|id_rsa|id_ed25519)'; then
  echo '⚠️ Attempting to read sensitive file - requires approval'
  exit 1
fi

exit 0
