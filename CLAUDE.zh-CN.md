[English](CLAUDE.md) | **简体中文**

# CLAUDE.md — 项目操作指南（Claude Code 打开本项目时自动加载）

> 若需英文版 Agent 指南，请使用 [CLAUDE.md](CLAUDE.md) 或将本文件内容复制为 `CLAUDE.md`。

本项目是 **北斗星**（代码库名 `career-compass`）：职业生涯决策引擎。当用户谈到职业规划 / 职业方向 / 求职决策 / 行业趋势 / 投递反馈时，运行北斗星工作流。

## 北极星

自动分析**用户画像 × 产业结构 × 行业趋势 × 市场竞争**，给出**精准、个性化、可执行**的求职定位与执行闭环。系统给排序后的选项和依据，**不替用户拍板**。

## 它是什么

用户关注的四块：**个人画像 · 行业趋势 · 职位收藏 · 机会矩阵**（App 与 CLI 同构）。

- `src/career_compass/` —— Python CLI + macOS App（`career-compass-app`）
- `playbooks/` —— 分析逻辑（Agent 驱动部分）
- `data/` —— 用户唯一事实源（gitignore）
- `data/examples/` —— 脱敏示例

## 工作流

1. **intake** — 引导式画像 → profile / narrative / constraints
2. **scan** — scan-plan → new-signal
3. **analyze** — brief → match --write-draft → 审阅 opportunities.yaml → render-opportunities（★核心交付★）
4. **execute（可选）** — render-execution → track 投递 → funnel → replan
5. **plan / stress-test** — 可选，用户选定方向后

**编排**: `status` / `run --stage`

## 命令速查

| 命令 | 作用 |
|---|---|
| `status` / `run [--stage]` | 阶段检测与预检 |
| `validate` / `brief` / `scan-plan` / `new-signal` / `scan-projects` | intake + scan |
| `match [--write-draft]` / `render-opportunities` / `render-pack` | analyze + 定位包 |
| `render-execution` | 求职执行包（pitch/简历/投递策略） |
| `track add/list/update/funnel` | 投递追踪 |
| `job add/list/show/analyze/remove` | 感兴趣岗位库（收藏 JD）→ `saved_jobs.yaml` |
| `jd-analyze <file>` | JD vs 画像缺口 |

## 铁律

- 优势挂证据；信号带来源+日期
- 机会矩阵给几个方向，不自动收敛一个
- constraints 是墙
- 不手改渲染出来的 .md

## 当前状态

**v0.3 · Phase 1–3**。Industry Graph、Role Taxonomy、match、render-pack、render-execution、track、replan、jd-analyze 已可用。

文档: `docs/schema-v2.md`, `docs/matching-engine.md`, `docs/phase-3.md`, [SKILL.zh-CN.md](SKILL.zh-CN.md)
