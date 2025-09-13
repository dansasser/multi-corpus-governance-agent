#!/usr/bin/env bash
set -Eeuo pipefail

echo "[entrypoint] Starting MCG Agent"
echo "[entrypoint] ENV: ENVIRONMENT=${ENVIRONMENT:-development} PORT=${PORT:-8000}"

# Ensure audit directory exists and writable
mkdir -p /app/audit || true

# Try to validate configuration (best effort)
python - <<'PY'
try:
    from mcg_agent.config import validate_environment
    import json
    res = validate_environment()
    print("[entrypoint] config:", json.dumps(res))
except Exception as e:
    print("[entrypoint] config validation skipped:", e)
PY

# Run DB migrations with retries (works for SQLite or Postgres if available)
attempt=0
max_attempts=${ALEMBIC_MAX_ATTEMPTS:-10}
sleep_s=${ALEMBIC_RETRY_SLEEP:-3}
until alembic upgrade head; do
  attempt=$((attempt+1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "[entrypoint] Alembic upgrade failed after $attempt attempts"
    break
  fi
  echo "[entrypoint] Alembic not ready, retrying in ${sleep_s}s... (attempt $attempt)"
  sleep "$sleep_s"
done

echo "[entrypoint] Launching API server"
exec uvicorn mcg_agent.app:app --host 0.0.0.0 --port "${PORT:-8000}"

