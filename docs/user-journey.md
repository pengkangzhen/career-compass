# 用户旅程 ↔ 引擎阶段 ↔ 架构层

北斗星用**两套对外语言 + 一套引擎名**，一一对应，不混用：

| 层级 | 系统层（架构/代码） | 用户层（GUI / 对话） | 引擎阶段（CLI / Agent） |
|------|---------------------|----------------------|-------------------------|
| L0 | **构建画像** | 认识自己 | `intake` |
| L1 | **探索世界** | 探索世界 | `scan` |
| L2 | **做出决策** | 做出决策 | `analyze` |
| L3 | **开始行动** | 开始行动 | `execute` |
| L4 | **持续追踪** | 持续追踪 | `track` / `replan` |

- **用户层**：客户端、GUI 顶栏、对话文案（如「请先完成认识自己」）
- **系统层**：README 架构图、设计文档、代码注释
- **引擎阶段**：`pipeline.py` / `status` / playbooks 文件名（`1-intake.md` 等）

> `playbooks/3-analyze.md` 内的 **fit / match / wind / risk 四层评分**是 L2 决策层内的分析维度，与上表 L0–L4 **编号无关**。

## 五步旅程（用户看到的）

```
认识自己 → 探索世界 → 做出决策 → 开始行动 → 持续追踪
```

| 步骤 | 系统层 | 用户含义 | 引擎阶段 | 主要产出 |
|------|--------|----------|----------|----------|
| **① 认识自己** | L0 构建画像 | 我是谁、能做什么、不能做什么 | `intake` | `profile.yaml` · `constraints.yaml` · `narrative.md` |
| **② 探索世界** | L1 探索世界 | 行业、趋势、岗位机会 | `scan` | `signals/*.yaml` · `saved_jobs.yaml` |
| **③ 做出决策** | L2 做出决策 | 比较机会矩阵，自行选择 | `analyze`（+ 可选 `plan`） | `opportunities.yaml` → `opportunities.md` ★核心★ |
| **④ 开始行动** | L3 开始行动 | （可选）简历与投递策略 | `execute` | `execution_pack.md` |
| **⑤ 持续追踪** | L4 持续追踪 | （可选）漏斗、反馈、迭代矩阵 | `track` / `replan` | `applications.yaml` · 修订矩阵 |

## 完成判据（旅程层）

| 步骤 | 视为完成当… | 备注 |
|------|-------------|------|
| 认识自己 | `validate` 无错误 | 必选 |
| 探索世界 | 至少 1 条信号 **或** 已有收藏岗位 | 必选 |
| 做出决策 | `opportunities.md` 已渲染 | 必选 · **核心交付** |
| 开始行动 | `execution_pack.md` 存在 | 可选（L3 战术延伸） |
| 持续追踪 | `applications.yaml` 有投递记录 | 可选（L4 长期机制） |

**主流程完成** = 「做出决策」完成。之后默认停留在「持续追踪」步骤，提示可选的 L3/L4 延伸；L3 不再是 L2 的必经门槛。

当前步骤 = 第一个尚未完成的**必选**步骤；核心完成后停留在「持续追踪」。

## GUI 映射

| Tab | 归属步骤 |
|-----|----------|
| 对话 | 认识自己（入口） |
| 我的画像 | 认识自己（结果） |
| 行业趋势 | 探索世界 |
| 岗位收藏 | 探索世界 |
| 机会矩阵 | 做出决策 |

步骤 ④⑤ 暂无独立 Tab，通过 CLI / Agent 执行；GUI 顶栏旅程条显示当前步骤与下一步提示。

**核心完成后（`opportunities.md` 已渲染）**：旅程条显示 **「✓ 已完成」** 徽章，副标题为「已完成 — 机会矩阵已就绪」；L3/L4 可选步骤不再高亮为当前步骤。

## 开发引用

```python
from career_compass.journey import build_journey_status

status = build_journey_status(data_dir)
# status.current → know_self | explore | decide | act | track
# status.engine_stage → intake | scan | analyze | ...
```

`uv run career-compass status` 同时输出用户旅程与引擎阶段。
