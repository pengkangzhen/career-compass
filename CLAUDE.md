# CLAUDE.md — 项目操作指南（Claude Code 打开本项目时自动加载）

本项目是 **Career-Compass**：一个"投简历之前"的职业规划工具。当用户谈到职业规划 / 职业方向 / 求职决策 / 行业趋势时，运行 Career-Compass 工作流。

## 它是什么

一个**数据驱动的工作流**，由你（Claude）来驱动：
- `src/career_compass/` —— Python CLI（用 uv 跑）。机械活：校验数据、渲染产物。命令以 `uv run career-compass <cmd>` 运行。
- `playbooks/` —— 分析逻辑（每个阶段开始前读对应文件）。
- `data/` —— 用户的唯一事实源（profile / constraints / narrative / signals / sectors / opportunities）。**改数据，不改代码**。

## 工作流（5 阶段）

1. **intake**（`playbooks/1-intake.md`）—— **引导式**：和用户聊，边聊边把信息提炼写入 `data/profile.yaml`、`narrative.md`、`constraints.yaml`（用户**不用预填**），针对 `validate` 报的缺口追问，直到 ✅。
2. **scan**（`playbooks/2-scan.md`）—— `uv run career-compass scan-plan` → 联网检索 → `uv run career-compass new-signal ...` 逐条入库（**带来源+日期**）。
3. **analyze**（`playbooks/3-analyze.md`）—— `uv run career-compass brief` → 套四层框架 → 写 `data/opportunities.yaml` → `uv run career-compass render-opportunities`。★**核心交付物**。
4. **plan**（`playbooks/4-plan.md`）—— **可选**，用户**自己选定**一个方向后才进。`uv run career-compass render-strategy` → 填 `strategy.md`。
5. **stress-test**（`playbooks/5-stress-test.md`）—— **可选**。pre-mortem + 设 tripwire。

## 铁律

- 每条优势必须有证据；每条信号必须有来源+日期。
- **机会矩阵是交付物**：给出**几个**可比较方向，**不要自动收敛到一个**。
- **不替用户选方向**。4-plan 只在用户明确选定后才进。
- **constraints 是墙**，不是建议；违反约束的方向直接剔除。
- 改事实改 `data/`，改逻辑改 `playbooks/`。永远不要手改渲染出来的 `.md`（那是产物）。

## 命令速查

| 命令 | 作用 |
|---|---|
| `uv run career-compass validate` | 校验画像完整性 |
| `uv run career-compass brief` | 聚合所有数据为分析用 brief |
| `uv run career-compass scan-plan` | 基于画像派生检索查询 |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | 追加一条外部信号 |
| `uv run career-compass render-opportunities` | 渲染机会矩阵（核心交付物） |
| `uv run career-compass render-strategy` | 渲染 strategy.md 骨架 |

**首次使用**：`cp templates/profile.example.yaml data/profile.yaml`（constraints 同理），填好后 `uv run career-compass validate`。

## 当前状态

`data/sectors.yaml` 是预置的 9 个热门行业参考池（非个人数据，已入库）。用户的个人数据文件（profile/narrative/constraints/opportunities/signals）被 gitignore，不入库。

完整的 skill 规范见 `SKILL.md`（用于打包成可安装 skill）。
