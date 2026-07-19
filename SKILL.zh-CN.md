---
name: career-compass
description: 北斗星 — 职业生涯决策引擎。画像×产业结构为基础，趋势/竞争叠加为评价指标→机会矩阵。止步于决策；投递侧工具为 legacy。用户要职业规划/选行业选岗位/方向验证时使用。**Intake：编码助手对话 或 GUI 对话**，均写 data/+CLI。流程：intake→scan→analyze→可选 plan/stress-test。
---

[English](SKILL.md) | **简体中文**

# 北斗星

**对话建画像有两条等价主路径**（同一套 `data/`，同一套 `validate`）：

1. **编码助手**（Claude Code / Cursor）— 本 Skill + `playbooks/`
2. **图形界面对话** — `career-compass-app --web` 的「对话」Tab（需配置 LLM）

scan / analyze 阶段在编码助手里往往更顺手（联网检索、改 YAML）；GUI 侧重 intake 对话与结果查看。

**核心交付物是一张机会矩阵** — 几个可比较、有依据的方向；**不替用户拍板**。

## 心智模型

```
个人画像(profile.yaml + narrative.md + constraints.yaml)
        ×
外部信号(signals/*.yaml，带来源+日期) · 感兴趣 JD(saved_jobs.yaml)
        ↓
   四层框架分析
        ↓
【机会矩阵】opportunities.yaml → opportunities.md  ★核心交付★
        ⛔  （北斗星到此为止）
        ↓ （可选，仍属 L2 决策层）
   strategy.md → 压测
```

`data/` 是唯一事实源；`playbooks/` 是分析逻辑；`src/`（career-compass CLI）只做校验/抓取/渲染，不做判断。

简历优化、投递策略、面试辅导、漏斗追踪**不在范围**——交给下游加速器工具。仓库保留 legacy CLI（`render-execution` / `track` / `replan` / `jd-analyze`），但不在主叙事与维护重点内。

## 阶段

**主流程（L0–L2）：**

| 阶段 | 必选 | 触发场景 | 你要做的事 |
|------|------|----------|------------|
| **1-intake** | ✅ | 首次来 / 画像不完整 | 对话采集 → 填 `profile.yaml`、`narrative.md`、`constraints.yaml` → `uv run career-compass validate` 直到无缺口 |
| **2-scan** | ✅ | 画像齐了，补外部信息 | `uv run career-compass scan-plan` → 用 web-search-prime/deep-research/WebSearch 检索 → `uv run career-compass new-signal` 逐条入库（**带来源+日期**）；`job add` 收藏感兴趣 JD |
| **3-analyze** | ✅ | 画像+信号都有 | `brief` → 可选 `match --write-draft` → 审阅 `opportunities.yaml` → `render-opportunities` ★核心★ |

**可选深化（仍属 L2 决策层）：**

| 阶段 | 触发场景 | 你要做的事 |
|------|----------|------------|
| **4-plan** | **用户从矩阵里自己选定了**一个方向 | 按 `playbooks/4-plan.md` → `strategy.md` |
| **5-stress-test** | plan 完成 | 按 `playbooks/5-stress-test.md` 做 pre-mortem + 假设挑战 → 修订 `strategy.md` |

**Legacy（投递侧，非主线）：** `render-execution` / `track` / `replan` / `jd-analyze` —— Phase 3 遗留，不作为产品卖点。

**1-3 是主流程，终点是机会矩阵。** 4-5 只有用户想深入某个方向才进入，且必须由用户自己选定方向。

## 怎么知道当前在哪一步

运行 `uv run career-compass status`（或 `run` 不带 `--stage`）自动检测：

| 条件 | 阶段 |
|------|------|
| 无 `profile.yaml` 或 `validate` 报错误 | **1-intake** |
| 画像齐了，`signals/` 空或不足 | **2-scan** |
| 有画像+信号，无 `opportunities.yaml` / 未渲染 `.md` | **3-analyze** |
| 机会矩阵已有，`strategy.md` 存在 | **4-plan**（可选） |
| `opportunities.md` 已渲染 | **done**（主交付物完成） |

## Pipeline 命令

**主流程：**

```bash
uv run career-compass status
uv run career-compass run [--stage STAGE]
uv run career-compass match [--write-draft]
uv run career-compass render-opportunities
uv run career-compass job add "公司" "岗位" [--direction "..."]   # 感兴趣 JD 库
```

**Legacy 投递侧 CLI（非主线）：**

```bash
uv run career-compass render-pack
uv run career-compass render-execution
uv run career-compass track add "公司" "岗位" [--tier B] [--direction "..."]
uv run career-compass track funnel
uv run career-compass replan [--write]
uv run career-compass jd-analyze jd.txt
```

**Analyze 推荐**：`brief` → `match --write-draft` → playbook 3 审阅 → `render-opportunities` ★核心交付★

Legacy 投递侧流程（详见 `docs/phase-3.md`）：`render-execution` → `track` → `funnel` → `replan --write`。不再作为产品表面维护。

## 铁律

1. **每条优势必须有证据**。`validate` 会拦下没有证据的"擅长"。
2. **每条外部信号必须有来源和日期**。模糊印象不算信号。
3. **机会矩阵是交付物**，不是中间步骤。给出**几个**方向，**不要自动收敛到一个**。
4. **不替用户选方向**。4-plan 只在用户明确选定后才进入。
5. **改事实改 data/，改逻辑改 playbooks/**。矩阵数据改 `opportunities.yaml`，`.md` 是渲染结果。
6. **constraints 是墙**，不是建议。违反约束的方向直接剔除。
7. **范围克制**：止步于机会矩阵；不要把北斗星拖进简历/投递/面试地盘。
