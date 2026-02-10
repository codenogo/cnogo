#!/bin/bash
set -e

# Dangerous command blocker for PreToolUse (Bash)
# Blocks destructive patterns that could damage the system.
# Uses printf instead of echo to avoid shell injection via $CLAUDE_TOOL_INPUT.

if [ -z "$CLAUDE_TOOL_INPUT" ]; then
  exit 0
fi

# Match dangerous patterns — covers flag variants, absolute paths, and command wrappers
if printf '%s' "$CLAUDE_TOOL_INPUT" | grep -qE '(rm\s+(-[a-zA-Z]*r[a-zA-Z]*\s+-[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*\s+-[a-zA-Z]*r|-rf|-fr)\s+[/~]|/bin/rm\s|command\s+rm\s|sudo\s+rm\s|chmod\s+777|>\s*/dev/sd|mkfs\.|dd\s+if=)'; then
  echo '❌ Blocked: Dangerous command pattern detected'
  exit 1
fi

exit 0
