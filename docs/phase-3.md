# Phase 3 — 求职执行与反馈闭环

Phase 3 在 Phase 2「选行业 / 选岗位」之上，补齐**怎么投、投得怎样、偏了怎么改**。

## 模块

| 模块 | 命令 | 产出 |
|------|------|------|
| 求职执行包 | `render-execution` | `execution_pack.md` — pitch、证据故事、简历建议、投递策略 |
| 投递追踪 | `track add/list/update/funnel` | `applications.yaml` |
| 反馈 replan | `replan [--write]` | 建议 + 可选 `opportunities.revised.yaml` |
| JD 分析 | `jd-analyze <file>` | stdout 技能词频与缺口 |
| Geo 约束 | `match` 内置 | constraints.geo 过滤海外岗 |

## 典型流程

```bash
# 1. 规划完成后
uv run career-compass render-pack
uv run career-compass render-execution

# 2. 投递记录
uv run career-compass track add "顺丰科技" "决策AI工程师" --tier B --direction "供应链决策 AI"
uv run career-compass track update <id> phone --feedback "问 MAKO 可靠性设计"

# 3. 漏斗与修订
uv run career-compass track funnel
uv run career-compass replan --write
```

## Replan 规则（v1 heuristic）

- ≥3 ghosted → 全局 tripwire
- ≥5 投、0 面试 → 定位偏差预警
- 某 direction 全拒 → composite 降一档
- 面试 feedback 关键词 → 追加 skill_gaps
- A 档全挂 → 建议主投 B 档

## 局限

- JD 分析为关键词/heuristic，非语义 embedding
- replan 不调用 LLM，修订需人工审阅后再 `mv` 为 opportunities.yaml
- tracker 无 Web UI，纯 YAML + CLI

## Phase 4 方向

定期 rescan、多 profile 版本、可 fork 行业知识包、可选浏览器插件抓 JD。
