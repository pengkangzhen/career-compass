#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/.env" ]]; then
  if [[ -f "$ROOT/.env.example" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo "Copied .env.example -> .env (edit SECRET_KEY before running again)."
  fi
fi

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

docker compose up -d postgres redis
sleep 3

uv sync --extra web
uv run alembic upgrade head

echo "✅ Dev env ready. Run: scripts/dev-web.sh"
