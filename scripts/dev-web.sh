#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

docker compose up -d postgres redis
sleep 2

uv run alembic upgrade head
exec uv run uvicorn career_compass.web.main:app --reload --port 8000
