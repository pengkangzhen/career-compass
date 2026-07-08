#!/usr/bin/env bash
# 将北斗星 Skill 安装到 Cursor 全局 skills 目录
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/.cursor/skills/career-compass"
DEST="${1:-$HOME/.cursor/skills/career-compass}"

if [[ ! -f "$SRC/SKILL.md" ]]; then
  echo "错误: 找不到 $SRC/SKILL.md" >&2
  exit 1
fi

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SRC" "$DEST"

echo "✅ 北斗星 Skill 已安装到: $DEST"
echo "   在 Cursor 任意项目中可通过 Agent 使用（描述含 career / 职业规划 时会触发）"
echo "   完整工作流仍需 clone career-compass 仓库并在此运行 CLI（data/ 在仓库内）"
