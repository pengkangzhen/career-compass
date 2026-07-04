---
name: career-compass
description: 职业规划前置工具。先让 Claude 深度理解用户（个人画像 + 外部趋势 + 产业格局），核心交付物是一张【机会矩阵】——几个可比较、有依据的职业方向。在用户要"分析职业方向 / 做职业规划 / 该往哪走 / 结合行业趋势看个人发展 / 看看我有哪些路"时使用。流程：intake → scan → analyze(机会矩阵) → 可选 plan → 可选 stress-test。
---

# Career-Compass

一个"投简历之前"的职业规划工具。**核心交付物是一张机会矩阵**：几个可比较、有依据的职业方向，作为用户职业决策的输入。它**不替用户拍板**走哪条路。

## 心智模型

```
个人画像(profile.yaml + narrative.md + constraints.yaml)
        ×
外部信号(signals/*.yaml，带来源+日期)
        ↓
   四层框架分析
        ↓
【机会矩阵】opportunities.yaml → opportunities.md   ← 核心交付物
        ↓ （可选：用户自己选定一个方向后）
   展开路径 strategy.md → 压力测试
```

`data/` 是唯一事实源；`playbooks/` 是分析逻辑；`src/`（career-compass CLI）只做校验/抓取/渲染，不做判断。

## 阶段

| 阶段 | 必选 | 触发场景 | 你要做的事 |
|------|------|----------|------------|
| **1-intake** | ✅ | 首次来 / 画像不完整 | 对话采集 → 填 `profile.yaml`、`narrative.md`、`constraints.yaml` → `uv run career-compass validate` 直到无缺口 |
| **2-scan** | ✅ | 画像齐了，补外部信息 | `uv run career-compass scan-plan` → 用 web-search-prime/deep-research/WebSearch 检索 → `uv run career-compass new-signal` 逐条入库（**带来源+日期**） |
| **3-analyze** | ✅ | 画像+信号都有 | `uv run career-compass brief` → 套 `playbooks/3-analyze.md` 四层框架 → 写 `data/opportunities.yaml` → `uv run career-compass render-opportunities` |
| **4-plan** | ❌可选 | **用户从矩阵里自己选定了**一个方向 | 按 `playbooks/4-plan.md` 展开成短/中/长期路径 → 写 `strategy.md` |
| **5-stress-test** | ❌可选 | plan 完成 | 按 `playbooks/5-stress-test.md` 做 pre-mortem + 假设挑战 → 修订 `strategy.md` |

**1-3 是主流程，终点是机会矩阵。** 4-5 只有用户想深入某个方向才进入，且必须由用户自己选定方向。

## 怎么知道当前在哪一步

- 看不到 `data/profile.yaml` 或 `validate` 报缺口 → **1-intake**
- `data/signals/` 空 → **2-scan**
- 有画像+信号但没有 `data/opportunities.yaml`/`.md` → **3-analyze**
- 矩阵有了 → **交付物完成**。用户说"我想深入 X" → **4-plan**

## 铁律

1. **每条优势必须有证据**。`validate` 会拦下没有证据的"擅长"。
2. **每条外部信号必须有来源和日期**。模糊印象不算信号。
3. **机会矩阵是交付物**，不是中间步骤。给出**几个**方向，**不要自动收敛到一个**。
4. **不替用户选方向**。4-plan 只在用户明确选定后才进入。
5. **改事实改 data/，改逻辑改 playbooks/**。矩阵数据改 `opportunities.yaml`，`.md` 是渲染结果。
6. **constraints 是墙**，不是建议。违反约束的方向直接剔除。
