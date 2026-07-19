# 用户旅程 ↔ 引擎阶段 ↔ 架构层

> 不同背景用户如何被同一套引擎服务、行业扩展 ROI：见 [architecture-users.md](architecture-users.md)。

北斗星用**两套对外语言 + 一套引擎名**，一一对应，不混用：

**核心三层（北斗星主线范围）：**

| 层级 | 系统层（架构/代码） | 用户层（GUI / 对话） | 引擎阶段（CLI / Agent） |
|------|---------------------|----------------------|-------------------------|
| L0 | **构建画像** | 认识自己 | `intake` |
| L1 | **探索世界** | 探索世界 | `scan` |
| L2 | **做出决策** | 做出决策 | `analyze` |

**Legacy 投递层（仓库保留，不在主线）：**

| 层级 | 系统层 | 用户层 | 引擎阶段 | 状态 |
|------|--------|--------|----------|------|
| L3 | 开始行动 | 开始行动 | `execute` | legacy（Phase 3，不维护） |
| L4 | 持续追踪 | 持续追踪 | `track` / `replan` | legacy（Phase 3，不维护） |

- **用户层**：客户端、GUI 顶栏、对话文案（如「请先完成认识自己」）
- **系统层**：README 架构图、设计文档、代码注释
- **引擎阶段**：`pipeline.py` / `status` / playbooks 文件名（`1-intake.md` 等）

> `playbooks/3-analyze.md` 内的 **fit / match / wind / risk 四层评分**是 L2 决策层内的分析维度，与上表 L0–L4 **编号无关**。

## 主线旅程（用户看到的）

```
认识自己 → 探索世界 → 做出决策   ⛔   （投递 / 简历 / 漏斗由下游工具承接）
```

| 步骤 | 系统层 | 用户含义 | 引擎阶段 | 主要产出 |
|------|--------|----------|----------|----------|
| **① 认识自己** | L0 构建画像 | 我是谁、能做什么、不能做什么 | `intake` | `profile.yaml` · `constraints.yaml` · `narrative.md` |
| **② 探索世界** | L1 探索世界 | 行业、趋势、感兴趣 JD | `scan` | `signals/*.yaml`；`saved_jobs.yaml` 作为画像/JD 补充 |
| **③ 做出决策** | L2 做出决策 | 比较机会矩阵，自行选择 | `analyze`（+ 可选 `plan` / `stress-test`） | `opportunities.yaml` → `opportunities.md` ★核心★ |

L3「开始行动」、L4「持续追踪」保留为 legacy 阶段，不进入主线旅程条；CLI 仍可调用（见 `docs/phase-3.md`）。

## 完成判据（旅程层）

| 步骤 | 视为完成当… | 备注 |
|------|-------------|------|
| 认识自己 | `validate` 无错误 | 必选 |
| 探索世界 | 至少 1 条外部信号（`signals/`） | 可选 · 增强分析，**不阻塞**机会矩阵 |
| 做出决策 | `opportunities.md` 已渲染 | 必选 · **核心交付** |

**主线完成** = 「做出决策」完成。机会矩阵渲染后，GUI 旅程条显示 **「✓ 已完成」** 徽章；L3/L4 legacy 步骤不再高亮为「当前步骤」。

当前步骤 = 第一个尚未完成的**必选**步骤（认识自己 → 做出决策）；探索世界为可选增强。

## GUI 映射

**GUI 主导航 = 核心三步**（机会矩阵为交付终点）：

| 旅程步骤 | 子视图 | 内容 |
|----------|--------|------|
| **① 认识自己** | 对话 · 完整画像 | intake 对话 + `profile.yaml` 等 |
| **② 探索世界** | 行业信号 · 岗位收藏 | `signals/`（可选）；`saved_jobs` 辅助了解意向 |
| **③ 做出决策** | （单页） | `opportunities.md` 机会矩阵 ★核心★ |

矩阵渲染完成后，GUI 底部展示可折叠的「投递阶段（legacy · CLI）」提示，作为对 Phase 3 工具的低调入口；不再占据主导航或当前步骤高亮。

## 开发引用

```python
from career_compass.journey import build_journey_status

status = build_journey_status(data_dir)
# status.current → know_self | explore | decide | act | track
# status.engine_stage → intake | scan | analyze | ...
```

> `act` / `track` 仍在 `journey.py` 中保留以兼容旧 GUI 与代码；新叙事里它们属于 legacy，不再作为主线推进的「下一步」。

`uv run career-compass status` 同时输出用户旅程与引擎阶段。
