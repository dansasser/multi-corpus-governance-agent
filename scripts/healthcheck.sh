#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"
URL="http://127.0.0.1:${PORT}/health"

if command -v curl >/dev/null 2>&1; then
  curl -fsS "$URL" >/dev/null
else
  python - <<PY
import sys, json, urllib.request
try:
    with urllib.request.urlopen("$URL", timeout=3) as r:
        if r.status != 200:
            sys.exit(1)
except Exception:
    sys.exit(1)
PY
fi

exit 0

