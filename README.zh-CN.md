[English](README.md) | **简体中文**

# 北斗星


一句话介绍：北斗星——一个帮迷茫的人做「方向选择题」的AI职业规划决策引擎


> 投简历**之前**的职业生涯决策引擎。自动分析**用户画像 × 产业结构 × 行业趋势 × 市场竞争**，在内卷环境下给出**精准、个性化、可执行**的职业规划——从「选什么行业、找什么岗位」到「怎么进、怎么避坑、怎么验证」。

## 项目目标

北斗星要解决的不是「AI 帮你想一个职业方向」，而是在**竞争激烈、供给过剩**的环境里，把职业决策做成**有证据、可复现、可迭代**的系统问题：

| 你要回答的问题 | 北斗星怎么帮 |
|---|---|
| **选什么行业？** | 产业结构分析：价值链位置、护城河/陷阱、红蓝海与内卷密度 |
| **找什么岗位？** | 岗位族匹配：职级带、技能缺口、目标公司梯队、地域策略 |
| **我凭什么进？** | 证据化画像：项目/论文/经历 → 可核验优势，对齐 JD 要求 |
| **现在进还来得及吗？** | 趋势 + 时机窗口：赛道周期、个人时间线（毕业/年龄/签证） |
| **会不会选错？** | 低试错成本设计 + 压测 + tripwire：先试再加大投入，假设失效自动预警 |
| **投了没回音怎么办？** | 反馈闭环：`track funnel` → `replan` 反推定位偏差、修订机会矩阵 |

**核心原则不变**：系统给**排序后的选项和依据**，不替用户拍板；价值观、家庭/地理硬约束、最终方向选择，仍由用户确认。

## 差异化：做「导航仪」，不做「加速器」

求职与职业规划赛道已有大量工具，但多数集中在**投简历前后**的战术环节。北斗星切入的是它们共同留空的**战略层**——在「我到底该往哪走」这个问题上，做重、做深、做长期。

### 现有工具三类

| 类型 | 代表 | 强项 | 局限 |
|------|------|------|------|
| **通用大模型** | ChatGPT、Claude | 覆盖面广、对话灵活 | 建议泛泛；无结构化画像；训练先验当「趋势」；一次性、不可复现 |
| **招聘平台衍生** | BOSS 直聘、前程无忧 | 岗位库全、投递链路短 | **立场偏向雇主**——推的是平台上的在招岗，不是用户最优方向 |
| **垂直 AI 工具** | 言笔 AI、CareerLead AI、Eightfold AI 等 | 简历优化、面试模拟、岗位匹配等单点做得深 | 功能散在「求职加速器」；很少回答「该不该进这个赛道」 |

### 现有工具的“集体盲区”

| 盲区 | 常见做法 | 北斗星 |
|------|----------|--------|
| **治标，非治本** | 改简历、练面试、提高匹配度——假设方向已定 | **职业导航仪**：先解决「适合做什么、进哪条赛道」，再谈怎么进 |
| **缺乏长线视角** | 一次性咨询、单次生成、用完即走 | **长期陪伴**：画像与策略可版本化；信号可 rescan；投递漏斗 → replan 持续校正 |
| **宏观视角缺失** | 只看「你 × 在招 JD」，忽略产业结构变迁 | **画像 × 产业结构 × 趋势 × 竞争**四维分析；深/浅价值链、内卷密度进评分 |
| **立场不中立** | 招聘平台有动力推自家岗位；B 端工具服务雇主筛选 | **不卖岗位，只卖方向**——无平台佣金、无雇主 KPI；给用户排序选项与依据，不替用户拍板 |

### 北斗星立足点

1. 不是“优化简历”，而是“职业规划”。
2. 长期陪伴：成为我的职业生涯的“长期合伙人”。
3. 构建“宏观视野”：将行业趋势、政策导向融入算法，提供超越“眼前岗位”的洞察。
4. 坚持“用户立场”：永远站在用户一边，用中立赢得信任。

## 系统架构（目标形态）

**术语约定**（全项目统一，详见 [`docs/user-journey.md`](docs/user-journey.md)）：

| 层级 | 系统层（架构/代码） | 用户层（GUI / 对话） | 引擎阶段（CLI / Agent） |
|------|---------------------|----------------------|-------------------------|
| L0 | **构建画像** | 认识自己 | `intake` |
| L1 | **探索世界** | 探索世界 | `scan` |
| L2 | **做出决策** | 做出决策 | `analyze` |
| L3 | **开始行动** | 开始行动 | `execute` |
| L4 | **持续追踪** | 持续追踪 | `track` / `replan` |

> analyze 阶段内的 **fit / match / wind / risk 四层评分**（见 `playbooks/3-analyze.md`）是决策层内的评分维度，与上表系统架构 L0–L4 **不是同一套编号**。

```
L0 构建画像 · 认识自己 · intake
     简历/CV · 代码项目 · 短对话（values/constraints）→ profile / constraints / narrative
        ↓
L1 探索世界 · scan
     趋势检索 · 供需/薪酬信号 · 产业结构 · 岗位图谱 → signals/*.yaml · saved_jobs.yaml
        ↓
L2 做出决策 · analyze
     硬约束过滤 → 多维评分 → 技能缺口 → 内卷/可进入性校正 → 机会矩阵
        ↓
L3 开始行动 · execute
     求职定位包 · 执行包（pitch / 简历建议 / 投递策略）
        ↓
L4 持续追踪 · track
     投递漏斗 → replan → 修订矩阵；[可选] plan + stress-test
```

**内卷不是忽略项，是评分维度之一**：供给增速、JD 技能堆叠、浅层岗位（如纯 API wrapper）、学历/年龄卡位，都会进入推荐权重——「精准」是 fit × 窗口 × 可进入性 × 试错成本的帕累托前沿，不是追最热赛道。

## 你会拿到什么

北斗星的核心交付是 **一份机会矩阵**（`opportunities.md`）——几个有依据、可比较的方向，**排序 + 理由，不替你拍板**。矩阵渲染自 `opportunities.yaml`，勿手改 `.md`。

### 机会矩阵：每个方向四个模块

| 模块 | 回答什么 |
|------|----------|
| **往哪走** | 行业/赛道、适合什么岗位 |
| **凭什么** | 可验证优势、还缺什么 |
| **值不值得现在进** | 竞争强度、顺风/逆风、时机 |
| **坑在哪** | 浅层热门岗、机会成本、试错代价 |

`opportunities.md` 渲染完成 = **北斗星主流程结束**（L2 做出决策）。

### 可选延伸（不是核心交付）

| 何时 | 做什么 | 文件/命令 |
|------|--------|-----------|
| 从矩阵**自行选定**一个方向后 | 方向深化 | `strategy.md`（`4-plan` / `5-stress-test`） |
| 准备真投递时 | 战术延伸（L3） | `render-execution` → `execution_pack.md` |
| 投递进行中 | 长期修正（L4） | `track` / `replan` → 修订机会矩阵 |

> `render-pack` → `job_pack.md` 为与矩阵重叠的汇总视图，一般不必单独生成。

## 亮点

### 已实现（v0.3 · Phase 1–3）
- 🧠 **L0 构建画像** —— Agent 边聊边提炼 `profile.yaml` / `narrative.md` / `constraints.yaml`；约束当硬墙
- 📂 **项目扫描（画像证据）** —— `scan-projects` 从指定代码库提取技术栈 / 依赖 / 规模 / 论文成果（opt-in，不扫整盘）
- 🌐 **L1 探索世界** —— `scan-plan` 派生检索查询；`new-signal` 入库并同 topic 去重（带来源+日期）
- ⚙️ **Pipeline 编排** —— `status` / `run --stage` 检测阶段、预检与下一步提示
- 🎯 **机会矩阵（核心交付）** —— `render-opportunities` → `opportunities.md`；每方向四模块：往哪走 / 凭什么 / 值不值得现在进 / 坑在哪
- 📊 **L2 匹配引擎 v1** —— `match`：技能对齐、竞争强度、浅层岗位惩罚
- 🗺️ **产业/岗位知识库** —— Industry Graph + Role Taxonomy，支撑矩阵生成
- 🚀 **（可选）行动手册** —— `render-execution` → `execution_pack.md`
- 📋 **（可选）投递追踪与修正** —— `track` / `replan` 反馈闭环
- 🔍 **JD 分析** —— `jd-analyze` 技能词频 vs 画像缺口
- 🏭 **预置热门赛道池** —— 9 大行业，深/浅陷阱
- 🛡️ **可选压测** —— pre-mortem + tripwire（playbook 5）

### 规划中（Phase 4+）
- 🤖 **Scan Agent 集群** —— 全自动联网检索写 signal
- 🔄 **定期 rescan** —— 信号过期自动提醒
- 📦 **多 profile / 可 fork 行业知识包**

## 适合谁

- 在「学术界 vs 工业界、研究 vs 工程、热门 vs 可持续」之间需要**有据决策**的人
- 面对内卷赛道，想搞清「该进深水区还是该换细分/岗位族」的人
- 希望职业选择**可复盘、可迭代**，而不是一次性 ChatGPT 问答的人

## 快速开始

### 1. 对话建画像（二选一）

| 方式 | 用法 |
|------|------|
| **编码助手（Skill）** | 打开本仓库，在 Claude Code / Cursor 里说「帮我做职业规划」；或 `./scripts/install-cursor-skill.sh` 全局安装 Skill |
| **图形界面对话** | 配置 LLM 后 `uv run career-compass-app --web`，在浏览器「对话」Tab 聊天建画像 |

两者都写入 `data/profile.yaml` 等，并用 `uv run career-compass validate` 校验。

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
uv sync --group gui   # 仅 GUI 路径需要
```

### 2. 图形界面（对话 + 查看）

```bash
# LLM（CloudBase / Anthropic / OpenAI 任选）
export CC_CLOUDBASE_BASE_URL="https://....api.tcloudbasegateway.com/v1/ai/cloudbase"
export CC_CLOUDBASE_API_KEY="..."

uv run career-compass-app --web    # WSL 推荐：浏览器打开
uv run career-compass-app          # macOS / 有 GTK 的 Linux 桌面
```

> Skill 细节：`.cursor/skills/career-compass/SKILL.md` · 依赖 [uv](https://docs.astral.sh/uv/)

## 工作流

五步用户旅程与引擎阶段一一对应（不混用别名）。完成判据见 [`docs/user-journey.md`](docs/user-journey.md)。

```
认识自己 → 探索世界 → 做出决策 → 开始行动 → 持续追踪
  intake      scan       analyze     execute      track
```

| 步骤 | 系统层 | 主要产出 | 必选 |
|------|--------|----------|------|
| 认识自己 | L0 构建画像 | `profile.yaml` · `constraints.yaml` · `narrative.md` | ✅ |
| 探索世界 | L1 探索世界 | `signals/*.yaml` · `saved_jobs.yaml` | ✅ |
| 做出决策 | L2 做出决策 | `opportunities.yaml` → `opportunities.md` | ✅ **核心交付** |
| 开始行动 | L3 开始行动 | `execution_pack.md`（`render-execution`） | 可选 |
| 持续追踪 | L4 持续追踪 | `applications.yaml` → `replan` 修订矩阵 | 可选 |

**可选深化**（用户从矩阵中**自行选定**方向后）：`plan` → `strategy.md`；`stress-test` → 修订 strategy。

GUI 顶栏展示用户旅程；CLI / Agent 使用引擎阶段名。`uv run career-compass status` 同时输出两层状态。

## CLI

| 命令 | 作用 |
|---|---|
| `uv run career-compass status` | 检测当前 pipeline 阶段与下一步 |
| `uv run career-compass run [--stage STAGE]` | 阶段预检与编排（intake → scan → analyze） |
| `uv run career-compass validate` | 校验画像完整性、标出缺口（错误 vs 警告） |
| `uv run career-compass brief` | 聚合所有数据为分析用 brief |
| `uv run career-compass scan-plan` | 基于画像派生检索查询 |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | 追加一条外部信号 |
| `uv run career-compass scan-projects <path>...` | 扫描指定项目目录，自动提取证据 |
| `uv run career-compass render-opportunities` | 渲染机会矩阵 |
| `uv run career-compass render-strategy` | 渲染 strategy.md 骨架 |
| `uv run career-compass match [--write-draft]` | 运行匹配引擎，可选写 `opportunities.draft.yaml` |
| `uv run career-compass render-pack [--stdout]` | （可选）汇总视图 → `job_pack.md` |
| `uv run career-compass render-execution [--stdout]` | （可选）战术延伸 → `execution_pack.md` |
| `uv run career-compass track add/list/update/funnel` | 投递追踪 → `applications.yaml` |
| `uv run career-compass replan [--write]` | 反馈闭环 → 修订建议 / `opportunities.revised.yaml` |
| `uv run career-compass jd-analyze <file>` | JD 技能聚类 vs 画像缺口 |

> 详见 `docs/matching-engine.md`（Phase 2）、`docs/phase-3.md`（Phase 3）。

## 文档与语言

| 语言 | 文件 |
|------|------|
| 英文（GitHub 默认） | [README.md](README.md) · [CLAUDE.md](CLAUDE.md) · [SKILL.md](SKILL.md) |
| 简体中文 | 本文件 · [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md) · [SKILL.zh-CN.md](SKILL.zh-CN.md) |

`playbooks/` 与部分 `docs/` 仍为中文（Agent 对话脚本）。

## 设计原则

- **证据驱动**：优势挂证据，信号带来源，评分引依据；禁止把模型先验当「检索信号」
- **constraints 是墙**：地理 / 家庭 / 年龄 / 风险偏好等硬约束直接剔除，不是降分留底
- **深 vs 浅**：热门赛道的浅层岗位（无壁垒、易替代）必须显式标注，composite 设上限
- **给选项不拍板**：推荐 Top-N 行业/岗位，用户选定后再展开 plan
- **数据与代码分离**：事实在 `data/`；分析逻辑在 `playbooks/`（逐步代码化进匹配引擎）；`src/` 做校验/采集/渲染
- **可迭代**：git 记录画像与策略演进；信号过期可 rescan；tripwire 触发 replan

## 路线图

| 阶段 | 目标 | 关键产出 |
|------|------|----------|
| **Phase 1** | 自动 pipeline 基础 | `run`/`status` 编排器；validate 收紧；Schema 2.0 字段；scan 去重 |
| **Phase 2** | 市场感知 + 岗位图谱 | Industry Graph、Role Taxonomy、竞争指数、技能缺口、求职定位包 v1 ✅ |
| **Phase 3** | 求职执行 + 反馈 | 执行包、track、replan、jd-analyze ✅ |
| **Phase 4** | 持续情报 OS | 定期 rescan、多版本 profile、可 fork 的行业知识包 |

## 状态

**v0.3 · Phase 1–3 已落地** — 主流程：画像 → 匹配 → **机会矩阵**（核心交付）。可选：执行包、投递追踪、replan。Phase 4（全自动 scan、持续情报 OS）仍为规划。

## License

MIT © Peng Kangzhen
