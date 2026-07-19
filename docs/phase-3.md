# Phase 3 — 可选延伸（L3 战术 · L4 追踪）

> ⚠️ **Legacy 文档**：自 v0.4 起，北斗星主线收敛到 L0–L2（机会矩阵即终点）。本文档化的工具（`render-execution` / `track` / `replan` / `jd-analyze` / `render-pack`）保留为 legacy CLI，**不再作为产品卖点或维护重点**。下游「求职加速器」工具（简历优化、投递追踪、面试辅导）通常做得更深，建议优先采用。
>
> 只有在你确实需要维护或调用这些 CLI 时才阅读本文档。

> **核心交付仍是机会矩阵**（L2 / `opportunities.md`）。本章在矩阵生成之后的**可选**阶段使用。

Phase 3 补齐**怎么投、投得怎样、偏了怎么改**——历史上曾计划作为战术加速器延伸，现已归档；下面内容供历史参考。

## 模块

| 模块 | 命令 | 产出 |
|------|------|------|
| 行动手册（L3） | `render-execution` | `execution_pack.md` — pitch、证据故事、简历建议、投递策略 |
| 投递追踪（L4） | `track add/list/update/funnel` | `applications.yaml` |
| 反馈 replan（L4） | `replan [--write]` | 建议 + 可选 `opportunities.revised.yaml` |
| JD 分析 | `jd-analyze <file>` | stdout 技能词频与缺口 |
| 汇总视图 | `render-pack` | `job_pack.md`（与矩阵重叠，一般不必） |

## 典型流程（可选）

```bash
# 1. 核心交付完成后，准备投递时
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
- **JD 关联矩阵方向**：`data/jd_link_rules.yaml` pattern → capability_id；有 `opportunities.yaml` 时合成「能力（雇主）」展示名
- replan 不调用 LLM，修订需人工审阅后再 `mv` 为 opportunities.yaml
- tracker 无 Web UI，纯 YAML + CLI

## Phase 4 方向

定期 rescan、多 profile 版本、可 fork 行业知识包、可选浏览器插件抓 JD。
