#!/usr/bin/env bash
# 一键启动北斗星本地 Web 桌面版（需先 uv sync --group gui）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ ! -d "$ROOT/src/career_compass/gui/static/dist" ]]; then
  echo "首次运行：构建现代化前端…"
  "$ROOT/scripts/build-frontend.sh"
fi

DESKTOP=""
NO_BROWSER=""
PORT=""
for arg in "$@"; do
  case "$arg" in
    --desktop) DESKTOP="--desktop" ;;
    --no-browser) NO_BROWSER="--no-browser" ;;
    --legacy) LEGACY="--legacy" ;;
  esac
done

if [[ -n "${PORT:-}" ]]; then
  exec uv run career-compass-app $DESKTOP $NO_BROWSER ${LEGACY:-} --port "$PORT"
fi

exec uv run career-compass-app $DESKTOP $NO_BROWSER ${LEGACY:-}
