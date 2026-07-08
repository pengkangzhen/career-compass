---
name: career-compass
description: >-
  Beidou (北斗星) pre-application career decision engine. Guides conversational
  intake to build profile.yaml/constraints/narrative, then scan→analyze→opportunity
  matrix. Use when the user wants career planning, job direction choice, industry
  selection, profile building, or application feedback. Intake via agent dialogue
  (Claude Code/Cursor) OR GUI chat; both write data/ + CLI validate.
---

[English](../../../SKILL.md) | **简体中文**

# 北斗星 — Agent Skill

**对话建画像有两条等价主路径**（都写入同一套 `data/`，都跑 `validate`）：

| 路径 | 适合谁 |
|------|--------|
| **编码助手**（本 Skill + `playbooks/`） | Claude Code / Cursor 里开发、希望 Agent 顺带写 YAML |
| **图形界面对话**（`career-compass-app --web`） | 不想开 IDE，在浏览器里聊 |

此外还有 **CLI + 图形界面查看**（画像 / 趋势 / 矩阵 Tab），与 intake 互补。

## 用户说什么时启动

- 「帮我做职业规划」「建画像」「选行业/岗位」
- 「分析机会矩阵」「投递反馈」「replan」
- 任何涉及 career-compass / 北斗星 / 求职决策的请求

## 第一步：检测阶段

```bash
uv run career-compass status
```

按输出进入对应 playbook，**不要跳阶段**。

| 阶段 | Playbook | 目标 |
|------|----------|------|
| intake | `playbooks/1-intake.md` | `profile.yaml` + `constraints.yaml` + `narrative.md`，`validate` 通过 |
| scan | `playbooks/2-scan.md` | `signals/*.yaml`，带来源+日期 |
| analyze | `playbooks/3-analyze.md` | `opportunities.yaml` → `opportunities.md` ★核心交付★ |
| execute | `docs/phase-3.md` | track / replan / jd-analyze |
| plan | `playbooks/4-plan.md` | 用户**选定方向后**才进入 |

## Intake（对话建画像）— 最重要

**必读** `playbooks/1-intake.md`。要点：

1. **像职业顾问聊天**，宽问题开场，不要甩空表或逐项审问
2. **用户说，你结构化** — 边聊边写 `data/profile.yaml`、`data/constraints.yaml`、`data/narrative.md`
3. 首次可从 `templates/` 拷贝模板再覆盖；`data/` 是用户私人数据（gitignored）
4. 每条 `strength_evidence` 必须有可核验 `proof`
5. `constraints` 是硬墙（家庭/runway/风险偏好/雇主性质；**不含地域/签证/户口**——北斗星只定方向，不选城市）
6. 每轮或大段补充后跑 `uv run career-compass validate`，针对缺口精准追问
7. 可选：`uv run career-compass scan-projects <path>` 从代码项目采证据（用户 opt-in）

**完成判据**：`validate` 无错误 → 进入 scan。

## Scan / Analyze 命令

```bash
uv run career-compass scan-plan
uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]
uv run career-compass brief
uv run career-compass match --write-draft   # 正交矩阵（能力×雇主，默认）
uv run career-compass match --legacy --write-draft  # 旧版单轴
uv run career-compass render-opportunities
uv run career-compass render-pack
```

## 铁律

1. 每条优势有证据；每条信号有来源和日期
2. 机会矩阵为 **能力×雇主正交矩阵**（Schema 2.2），不只给单一方向列表
3. 改 YAML，重新 render；不要手改 `opportunities.md` 等渲染文件
4. constraints 违反即剔除，不是降分；**employer_preference 是墙**

## 图形界面（对话 + 查看）

**对话 intake**（与编码助手等价，需配置 LLM）：

```bash
export CC_CLOUDBASE_BASE_URL="..."   # 或 ANTHROPIC / OPENAI
export CC_CLOUDBASE_API_KEY="..."
uv run career-compass-app --web      # 浏览器 http://127.0.0.1:8765 ，「对话」Tab
```

**查看**画像 / 趋势 / 矩阵：同一 App 的其他 Tab，或编码助手里 `render-opportunities` 后打开。

## 安装本 Skill

**Cursor（项目内）**：克隆本仓库后在 Cursor 打开即可（`.cursor/skills/` 自动生效）。

**Cursor（全局）**：

```bash
./scripts/install-cursor-skill.sh
```

**Claude Code**：在本仓库目录运行 `claude`；自动加载根目录 `CLAUDE.md` + `SKILL.md`。
