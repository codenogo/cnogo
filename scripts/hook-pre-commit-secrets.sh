#!/bin/bash
set -e

# Pre-commit secret scanner for PreToolUse (Bash)
# Scans staged files for secret patterns before git commit.
# Uses a single combined grep per file instead of separate calls.
# Uses printf instead of echo to avoid shell injection via $CLAUDE_TOOL_INPUT.

if [ -z "$CLAUDE_TOOL_INPUT" ]; then
  exit 0
fi

# Only run on git commit commands
if ! printf '%s' "$CLAUDE_TOOL_INPUT" | grep -q '^git commit'; then
  exit 0
fi

echo '🔍 Scanning for secrets...'
SECRET_FOUND=0
STAGED=$(git diff --cached --name-only 2>/dev/null || true)

if [ -z "$STAGED" ]; then
  echo '✅ No staged files to scan'
  exit 0
fi

# Combined pattern for all secret types:
#   AWS keys, Anthropic keys, OpenAI keys, GitHub tokens, Slack tokens,
#   Private keys, Azure storage keys, GCP service accounts,
#   Stripe keys, Twilio SIDs, SendGrid keys, Firebase keys,
#   Database connection strings
SECRET_PATTERN='AKIA[0-9A-Z]{16}|sk-ant-[a-zA-Z0-9-]{20,}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|xox[baprs]-[0-9a-zA-Z-]{10,}|BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY|AccountKey=[a-zA-Z0-9+/=]{40,}|"type":\s*"service_account"|sk_live_[a-zA-Z0-9]{20,}|pk_live_[a-zA-Z0-9]{20,}|SK[a-fA-F0-9]{32}|SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}|AIza[0-9A-Za-z_-]{35}|postgres://[^:]+:[^@]+@|mongodb(\+srv)?://[^:]+:[^@]+@'

for file in $STAGED; do
  if [ -f "$file" ]; then
    MATCHES=$(grep -nE "$SECRET_PATTERN" "$file" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
      echo "❌ Secret pattern found in $file:"
      echo "$MATCHES" | head -5
      SECRET_FOUND=1
    fi
  fi
done

if [ $SECRET_FOUND -eq 1 ]; then
  exit 1
fi

echo '✅ No secrets detected'
exit 0
