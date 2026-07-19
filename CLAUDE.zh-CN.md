[English](CLAUDE.md) | **简体中文**

# CLAUDE.md — 项目操作指南（Claude Code 打开本项目时自动加载）

> 若需英文版 Agent 指南，请使用 [CLAUDE.md](CLAUDE.md) 或将本文件内容复制为 `CLAUDE.md`。

本项目是 **北斗星**（代码库名 `career-compass`）：职业生涯决策引擎。当用户谈到职业规划 / 职业方向 / 求职决策 / 行业趋势 / 投递反馈时，运行北斗星工作流。

## 北极星

在**用户画像 × 产业结构**两维基础信息上，叠加**趋势信号**与**竞争强度**作为评价指标，给出**排序后的方向选项和依据**。北斗星止步于机会矩阵（L2 做出决策）；简历优化、投递策略、面试辅导不在范围。系统**不替用户拍板**。

## 它是什么

用户关注的三块（App 与 CLI 同构）：**个人画像 · 行业探索 · 机会矩阵**。

- `src/career_compass/` —— Python CLI + macOS App（`career-compass-app`）
- `playbooks/` —— 分析逻辑（Agent 驱动部分）
- `data/` —— 用户唯一事实源（gitignore）
- `data/examples/` —— 脱敏示例

## 工作流

**主流程（L0–L2）：**

1. **intake** — 引导式画像 → profile / narrative / constraints
2. **scan** — scan-plan → new-signal；`job add` 收藏感兴趣 JD
3. **analyze** — brief → match --write-draft → 审阅 opportunities.yaml → render-opportunities ★核心交付★

**可选深化（仍属 L2 决策层）：**

4. **plan / stress-test** — 用户从矩阵里**自行选定**一个方向后才进入

**范围外（仓库保留 legacy CLI，不在主线维护）：** `render-execution` / `track` / `replan` / `jd-analyze` —— 简历优化、投递策略、面试辅导、漏斗追踪交给下游加速器工具。

**编排**: `status` / `run --stage`

## 命令速查

**主流程：**

| 命令 | 作用 |
|---|---|
| `status` / `run [--stage]` | 阶段检测与预检 |
| `validate` / `brief` / `scan-plan` / `new-signal` / `scan-projects` | intake + scan |
| `match [--write-draft]` / `render-opportunities` / `render-pack` | analyze + 定位包 |
| `job add/list/show/analyze/remove` | 感兴趣岗位库（收藏 JD）→ `saved_jobs.yaml`（属 L1 探索世界） |

**Legacy（投递侧，非主线）：**

| 命令 | 作用 |
|---|---|
| `render-execution` | 求职执行包（pitch/简历/投递策略） |
| `track add/list/update/funnel` | 投递追踪 |
| `replan [--write]` | 反馈闭环 |
| `jd-analyze <file>` | JD vs 画像缺口 |

## 铁律

- 优势挂证据；信号带来源+日期
- 机会矩阵给几个方向，不自动收敛一个
- constraints 是墙
- 不手改渲染出来的 .md
- **范围克制**：止步于机会矩阵；不要把北斗星拖进简历/投递/面试地盘

## 当前状态

**v0.4 · 主线收敛到 L0–L2** —— 主流程止步于机会矩阵。Phase 3 的投递侧工具（`render-execution` / `track` / `replan` / `jd-analyze`）保留为 legacy CLI，不再是叙事与维护重点。

文档: `docs/schema-v2.md`, `docs/matching-engine.md`, [SKILL.zh-CN.md](SKILL.zh-CN.md)。（`docs/phase-3.md` 文档化 legacy 投递侧工具——只有必须维护那些 CLI 时才读。）
