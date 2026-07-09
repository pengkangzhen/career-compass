#!/usr/bin/env bash
# Build Vite SPA → src/career_compass/gui/static/dist
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "错误: 需要 Node.js + npm。参见 https://nodejs.org/" >&2
  exit 1
fi

npm install
npm run build
echo "✅ 前端已构建 → src/career_compass/gui/static/dist"
