#!/bin/bash
set -e

# Sensitive file reader blocker for PreToolUse (Read)
# Warns when attempting to read files that may contain secrets.
# Uses printf instead of echo to avoid shell injection via $CLAUDE_TOOL_INPUT.

if [ -z "${CLAUDE_TOOL_INPUT:-}" ]; then
  exit 0
fi

extract_paths() {
  python3 - "$CLAUDE_TOOL_INPUT" <<'PY'
import json
import sys

raw = sys.argv[1].strip()
if not raw:
    raise SystemExit(0)

PATH_KEYS = {"path", "paths", "file_path", "target_file", "file", "filename"}
out: list[str] = []

def add(value):
    if isinstance(value, str):
        v = value.strip()
        if v:
            out.append(v)
    elif isinstance(value, list):
        for item in value:
            add(item)

def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in PATH_KEYS:
                add(v)
            if isinstance(v, (dict, list)):
                walk(v)
    elif isinstance(node, list):
        for item in node:
            walk(item)

try:
    payload = json.loads(raw)
except Exception:
    # If tool input isn't JSON, use raw string as best effort.
    out.append(raw)
else:
    if isinstance(payload, str):
        out.append(payload)
    else:
        walk(payload)

for value in out:
    print(value)
PY
}

while IFS= read -r path; do
  [ -z "$path" ] && continue
  lower="$(printf '%s' "$path" | tr '[:upper:]' '[:lower:]')"
  if printf '%s' "$lower" | grep -qE '((^|/)\.env($|\.|/)|credentials|secrets\.ya?ml$|-prod\.(ya?ml|properties|json)$|\.pem$|\.key$|id_rsa$|id_ed25519$|\.aws/credentials$|\.kube/config$)'; then
    echo "⚠️ Attempting to read sensitive file: $path"
    exit 1
  fi
done <<EOF
$(extract_paths || true)
EOF

exit 0
