#!/usr/bin/env bash
# Heads-up dev launcher that runs the FastAPI app against an in-memory sqlite DB.
# Use this ONLY when you can't run Postgres via docker-compose. State is lost on
# restart. For real local dev, prefer scripts/dev-web.sh (Postgres + Alembic).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${SECRET_KEY:-}" ]]; then
  export SECRET_KEY="dev-only-secret-please-replace-with-openssl-rand-hex-32"
fi

export DATABASE_URL="sqlite+aiosqlite:///:memory:"
export CC_CREATE_TABLES_ON_STARTUP=1

exec uv run --group web uvicorn career_compass.web.main:app --reload --port 8000 --host 127.0.0.1
