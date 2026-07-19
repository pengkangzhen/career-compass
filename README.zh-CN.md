[English](README.md) | **简体中文**

# 北斗星

一句话介绍：北斗星——一个帮迷茫的人做「方向选择题」的AI职业规划决策引擎

> 投简历**之前**的职业生涯决策引擎。在**用户画像 × 产业结构**两维基础信息上，叠加**行业趋势**（含风口/夕阳、竞争强度）与**试错成本**作为评价指标，给出**排序后的方向选项 + 依据**——回答「选什么行业、找什么岗位、凭什么进、值不值得现在进」。**到此为止**，简历优化、投递策略、面试辅导留给下游加速器工具。

## 项目目标

北斗星要解决的不是「AI 帮你想一个职业方向」，而是在**竞争激烈、供给过剩**的环境里，把职业决策做成**有证据、可复现、可迭代**的系统问题：


| 你要回答的问题    | 北斗星怎么帮                          |
| ---------- | ------------------------------- |
| **选什么行业？** | 产业结构分析：价值链位置、护城河/陷阱、红蓝海与内卷密度    |
| **找什么岗位？** | 岗位族匹配：职级带、技能缺口、目标公司梯队、地域策略      |
| **我凭什么进？** | 证据化画像：项目/论文/经历 → 可核验优势，对齐 JD 要求 |


**核心原则不变**：系统给**排序后的选项和依据**，不替用户拍板；价值观、家庭/地理硬约束、最终方向选择，仍由用户确认。

## 差异化：做「导航仪」，不做「加速器」

求职与职业规划赛道已有大量工具，但多数集中在**投简历前后**的战术环节。北斗星切入的是它们共同留空的**战略层**——在「我到底该往哪走」这个问题上，做重、做深、做长期。

### 现有工具三类


| 类型           | 代表                                 | 强项                   | 局限                               |
| ------------ | ---------------------------------- | -------------------- | -------------------------------- |
| **通用大模型**    | ChatGPT、Claude                     | 覆盖面广、对话灵活            | 建议泛泛；无结构化用户画像；训练先验当「趋势」；一次性、不可复现 |
| **招聘平台衍生**   | BOSS 直聘、前程无忧                       | 岗位库全、投递链路短           | **立场偏向雇主**——推的是平台上的在招岗，不是用户最优方向  |
| **垂直 AI 工具** | 言笔 AI、CareerLead AI、Eightfold AI 等 | 简历优化、面试模拟、岗位匹配等单点做得深 | 功能散在「求职加速器」；很少回答「该不该进这个赛道」       |




### 现有工具的“集体盲区”


| 盲区         | 常见做法                  | 北斗星                                                            |
| ---------- | --------------------- | -------------------------------------------------------------- |
| **只治标不治本** | 改简历、练面试——默认用户已经确定职业方向 | **职业导航仪**：先解决「适合做什么、进哪条赛道」，再谈怎么进                               |
| **缺乏长线视角** | 一次性生成——无版本、无迭代        | **长期陪伴**：画像/策略可版本化；信号可 rescan                                  |
| **宏观视角缺失** | 只对在招 JD——产业结构缺位       | **宏观视角**：用户画像 × 产业结构为基础；**行业趋势**（含风口/夕阳、竞争强度、深/浅价值链、内卷密度）与**试错成本**作为评价维度进入 `composite`      |
| **立场不够中立** | 以平台/雇主利益优先            | 坚持“用户立场”——无平台佣金、无雇主 KPI；给排序选项与依据，不替用户拍板                        |




### 北斗星立足点

1. 不是“优化简历”，而是“职业规划”。
2. 长期陪伴：成为我的职业生涯的“长期合伙人”。
3. 构建“宏观视野”：将行业趋势、政策导向融入算法，提供超越“眼前岗位”的洞察。
4. 坚持“用户立场”：永远站在用户一边，用中立赢得信任。



## 系统架构（目标形态）

**术语约定**（全项目统一，详见 `[docs/user-journey.md](docs/user-journey.md)`）：

**核心三层（北斗星的边界）：**

| 层级  | 系统层（架构/代码） | 用户层（GUI / 对话） | 引擎阶段（CLI / Agent）  |
| --- | ---------- | ------------- | ------------------ |
| L0  | **构建画像**   | 认识自己          | `intake`           |
| L1  | **行业趋势**   | 探索世界          | `scan`             |
| L2  | **机会矩阵**   | 做出决策          | `analyze`          |

> analyze 阶段内的 **fit / match / wind / risk 四层评分**（见 `playbooks/3-analyze.md`）是决策层内的评分维度，与上表系统架构 L0–L2 **不是同一套编号**。

```
L0 构建画像 · 认识自己 · intake
     简历/CV · 代码项目 · 短对话（values/constraints）→ profile / constraints / narrative
        ↓
L1 行业趋势 · scan
     趋势检索 · 供需/薪酬信号 · 产业结构 · 岗位图谱 · 感兴趣 JD 收藏 → signals/*.yaml · saved_jobs.yaml
        ↓
L2 机会矩阵 · analyze
     硬约束过滤 → 多维评分 → 技能缺口 → 内卷/可进入性校正 → 机会矩阵
        ⛔
     （北斗星到此为止；简历优化 / 投递策略 / 面试辅导 / 漏斗追踪 交给下游工具）
```

**内卷不是忽略项，是评分维度之一**：供给增速、JD 技能堆叠、浅层岗位（如纯 API wrapper）、学历/年龄卡位，都会进入推荐权重——「精准」是 fit × 窗口 × 可进入性 × 试错成本的帕累托前沿，不是追最热赛道。

## 你会拿到什么

北斗星的核心交付是 **一份机会矩阵**（`opportunities.md`）——几个有依据、可比较的方向，**排序 + 理由，不替你拍板**。矩阵渲染自 `opportunities.yaml`，勿手改 `.md`。

### 机会矩阵：每个方向四个模块


| 模块          | 回答什么            |
| ----------- | --------------- |
| **往哪走**     | 行业/赛道、适合什么岗位    |
| **凭什么**     | 可验证优势、还缺什么      |
| **值不值得现在进** | 竞争强度、顺风/逆风、时机   |
| **坑在哪**     | 浅层热门岗、机会成本、试错代价 |


`opportunities.md` 渲染完成 = **北斗星主流程结束**（L2 做出决策）。

### 可选延伸（决策深化，不是投递执行）

| 何时               | 做什么  | 文件/命令                                     |
| ---------------- | ---- | ----------------------------------------- |
| 从矩阵**自行选定**一个方向后 | 方向深化 | `strategy.md`（`4-plan`）+ 压测（`5-stress-test`） |

> 北斗星**不**覆盖：简历优化、投递策略、面试辅导、投递漏斗追踪——这些交给下游「求职加速器」工具。仓库里 `render-execution` / `track` / `replan` / `jd-analyze` CLI 仍可调用（历史实现），但不在主叙事与维护重点内。
>
> `render-pack` → `job_pack.md` 为与矩阵重叠的汇总视图，一般不必单独生成。



## 亮点



### 已实现（v0.4 · 主线 L0–L2）

- 🧠 **L0 构建画像** —— Agent 边聊边提炼 `profile.yaml` / `narrative.md` / `constraints.yaml`；约束当硬墙
- 📂 **项目扫描（画像证据）** —— `scan-projects` 从指定代码库提取技术栈 / 依赖 / 规模 / 论文成果（opt-in，不扫整盘）
- 🌐 **L1 探索世界** —— `scan-plan` 派生检索查询；`new-signal` 入库并同 topic 去重（带来源+日期）；`job add` 收藏感兴趣 JD
- ⚙️ **Pipeline 编排** —— `status` / `run --stage` 检测阶段、预检与下一步提示
- 🎯 **机会矩阵（核心交付）** —— `render-opportunities` → `opportunities.md`；每方向四模块：往哪走 / 凭什么 / 值不值得现在进 / 坑在哪
- 📊 **L2 匹配引擎 v1** —— `match`：技能对齐、竞争强度、浅层岗位惩罚
- 🗺️ **产业/岗位知识库** —— Industry Graph + Role Taxonomy，支撑矩阵生成
- 🛡️ **可选压测** —— pre-mortem + tripwire（playbook 5），帮用户选定方向后做风险检查
- 🤖 **Agent Skill** —— Claude Code / Cursor 对话建画像
- 💬 **GUI 对话** —— `career-compass-app --web`「对话」Tab，与 Skill 等价写入 `data/`
- 🖥️ **CLI + GUI Tab** —— validate、scan、match、查看矩阵
- 🧰 **附加 CLI（投递侧辅助，非主线）** —— `track` / `replan` / `render-execution` / `jd-analyze` / `saved_jobs`：历史实现保留，未作为重点维护方向



### 规划中（Phase 4+）

#### L1 持续情报（已有方向延伸）

- 🤖 **Scan Agent 集群** —— 全自动联网检索写 signal
- 🔄 **定期 rescan** —— 信号过期自动提醒
- 📦 **多 profile / 可 fork 行业知识包**

#### L2 决策增强（OR/ML 数据层）—— 新方向

匹配引擎当前是**确定性 heuristic**（透明、可审计、无外部 API 调用）。Phase 4 计划在其之上加一层**可选的 data-driven 增量**。原则：始终报告 delta vs heuristic baseline，让用户看见 ML 改了什么、为什么改；冷启动阶段 heuristic 是基线，数据足够才让 ML 接管。

- 📊 **数据分析层** —— 把投递漏斗、JD 语料、面试反馈作为新数据源：isotonic regression 把 heuristic `match_score` 校准成可验证的 `P(interview)`；技能共现矩阵 → embedding cosine 替代关键词子串匹配（解决"强化学习 ↔ RLHF / Agent"这类语义近邻）。这是把北斗星从「启发式工具」升级为「数据驱动决策系统」的转折点
- 🎰 **Bayesian Bandit 投递建议** —— 每个 `(方向 × 雇主性质 × 公司档位)` 视为一只臂，Thompson sampling 自动平衡探索（试新方向）与利用（投已知转化高的），替代当前 `replan` 里的硬阈值规则。**需要用户 opt-in 使用 `track`**（北斗星主线不含投递追踪，此为可选闭环）
- 📐 **Pareto 前沿视图** —— 机会矩阵的 6 个评分维度（核心竞争力 / Ikigai / 行业趋势 / 试错 / 资格 / 竞争）本质不可公度；当前用字母档 A–F 压成单一排名会掩盖 trade-off（实测会出现「综合 A 但被严格支配」的方向）。Pareto 前沿呈现「哪些方向互不可比、需要你做价值判断」，配合两两对比 + 偏好敏感度（「如果我最在意试错成本，谁最优」）。已有原型 `career-compass pareto`，可视化形态待定（静态图信息量有限，倾向 GUI 交互式探索）



## 适合谁

- 在「学术界 vs 工业界、研究 vs 工程、热门 vs 可持续」之间需要**有据决策**的人
- 面对内卷赛道，想搞清「该进深水区还是该换细分/岗位族」的人
- 希望职业选择**可复盘、可迭代**，而不是一次性 ChatGPT 问答的人



## 快速开始



### 1. 对话建画像（二选一）


| 方式              | 用法                                                                                                   |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| **编码助手（Skill）** | 打开本仓库，在 Claude Code / Cursor 里说「帮我做职业规划」；或 `./scripts/install-cursor-skill.sh` 全局安装 Skill            |
| **图形界面对话**      | `uv run career-compass-app` 或 `./scripts/beidou.sh`（LLM 默认读项目根 `.env`，见 `templates/llm.env.example`） |


两者都写入 `data/profile.yaml` 等，并用 `uv run career-compass validate` 校验。

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
uv sync --group gui   # 仅 GUI 路径需要
```



### 2. 图形界面（对话 + 查看）

```bash
./scripts/beidou.sh              # 浏览器打开（推荐）
uv run career-compass-app
uv run career-compass-app --desktop   # 桌面窗口（需 pywebview）
```

LLM 默认 **腾讯云 CloudBase**（`hy3-preview`）。项目根 `.env` 自动加载；可复制 `templates/llm.env.example` 修改。

## 工作流

北斗星只覆盖**决策前三步**——「投简历之前」严格定义。完成判据见 `[docs/user-journey.md](docs/user-journey.md)`。

```
认识自己 → 探索世界 → 做出决策   ⛔   （投简历 / 简历优化 / 投递追踪由下游工具承接）
  intake      scan       analyze
```

| 步骤   | 系统层     | 主要产出                                                 | 必选         |
| ---- | ------- | ---------------------------------------------------- | ---------- |
| 认识自己 | L0 构建画像 | `profile.yaml` · `constraints.yaml` · `narrative.md` | ✅          |
| 探索世界 | L1 探索世界 | `signals/*.yaml` · `saved_jobs.yaml`                 | ✅          |
| 做出决策 | L2 做出决策 | `opportunities.yaml` → `opportunities.md`            | ✅ **核心交付** |

**可选深化**（用户从矩阵中**自行选定**方向后）：`plan` → `strategy.md`；`stress-test` → 修订 strategy。仍属于 L2 决策层的延伸，**不是**投递执行。

GUI 顶栏展示用户旅程；CLI / Agent 使用引擎阶段名。`uv run career-compass status` 同时输出用户旅程与引擎阶段。

## CLI

### 主流程（L0–L2，北斗星核心）

| 命令                                                                   | 作用                                         |
| -------------------------------------------------------------------- | ------------------------------------------ |
| `uv run career-compass status`                                       | 检测当前 pipeline 阶段与下一步                       |
| `uv run career-compass run [--stage STAGE]`                          | 阶段预检与编排（intake → scan → analyze）           |
| `uv run career-compass validate`                                     | 校验画像完整性、标出缺口（错误 vs 警告）                     |
| `uv run career-compass brief`                                        | 聚合所有数据为分析用 brief                           |
| `uv run career-compass scan-plan`                                    | 基于画像派生检索查询                                 |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | 追加一条外部信号                                   |
| `uv run career-compass scan-projects <path>...`                      | 扫描指定项目目录，自动提取证据                            |
| `uv run career-compass match [--write-draft]`                        | 运行匹配引擎，可选写 `opportunities.draft.yaml`      |
| `uv run career-compass render-opportunities`                         | 渲染机会矩阵（核心交付）                                |
| `uv run career-compass render-strategy`                              | 渲染 strategy.md 骨架（可选深化）                    |
| `uv run career-compass render-pack [--stdout]`                       | 汇总视图 → `job_pack.md`（一般不必单独生成）             |

### 附加工具（投递侧，历史实现保留）

> 不在主叙事与维护重点内。下游简历 / 投递 / 面试工具通常做得更深，建议优先采用。

| 命令                                                      | 作用                                            |
| ----------------------------------------------------- | ------------------------------------------- |
| `uv run career-compass job add/list/show/analyze/remove` | 感兴趣岗位库（收藏 JD） → `saved_jobs.yaml`           |
| `uv run career-compass jd-analyze <file>`              | JD 技能聚类 vs 画像缺口                              |
| `uv run career-compass render-execution [--stdout]`    | 战术延伸 → `execution_pack.md`（pitch / 简历建议 / 投递策略） |
| `uv run career-compass track add/list/update/funnel`   | 投递追踪 → `applications.yaml`                  |
| `uv run career-compass replan [--write]`              | 反馈闭环 → 修订建议 / `opportunities.revised.yaml`  |

> 详见 `docs/matching-engine.md`（Phase 2）、`docs/schema-v2.md`。



## 文档与语言


| 语言            | 文件                                                                          |
| ------------- | --------------------------------------------------------------------------- |
| 英文（GitHub 默认） | [README.md](README.md) · [CLAUDE.md](CLAUDE.md) · [SKILL.md](SKILL.md)      |
| 简体中文          | 本文件 · [CLAUDE.zh-CN.md](CLAUDE.zh-CN.md) · [SKILL.zh-CN.md](SKILL.zh-CN.md) |


`playbooks/` 与部分 `docs/` 仍为中文（Agent 对话脚本）。

线上部署见 [docs/deployment.md](docs/deployment.md)（Vercel + Render + Neon）。试用：https://career-compass-gilt.vercel.app

## 设计原则

- **证据驱动**：优势挂证据，信号带来源，评分引依据；禁止把模型先验当「检索信号」
- **constraints 是墙**：地理 / 家庭 / 年龄 / 风险偏好等硬约束直接剔除，不是降分留底
- **深 vs 浅**：热门赛道的浅层岗位（无壁垒、易替代）必须显式标注，composite 设上限
- **给选项不拍板**：推荐 Top-N 行业/岗位，用户选定后再展开 plan
- **数据与代码分离**：事实在 `data/`；分析逻辑在 `playbooks/`（逐步代码化进匹配引擎）；`src/` 做校验/采集/渲染
- **可迭代**：git 记录画像与策略演进；信号过期可 rescan
- **范围克制**：止步于「方向选择」，不覆盖简历优化 / 投递策略 / 面试辅导——交给下游工具



## 路线图


| 阶段          | 目标             | 关键产出                                                 |
| ----------- | -------------- | ---------------------------------------------------- |
| **Phase 1** | 自动 pipeline 基础 | `run`/`status` 编排器；validate 收紧；Schema 2.0 字段；scan 去重 |
| **Phase 2** | 市场感知 + 岗位图谱    | Industry Graph、Role Taxonomy、竞争指数、技能缺口、求职定位包 v1 ✅    |
| **Phase 3** | 投递侧附加工具（边界外）   | 执行包、track、replan、jd-analyze（已实现但不在主线，供历史用户使用）         |
| **Phase 4** | 持续情报 OS        | 定期 rescan、多版本 profile、可 fork 的行业知识包                  |



## 状态

**v0.4 · 主线收敛到 L0–L2** — 主流程：画像 → 探索 → 匹配 → **机会矩阵**（核心交付）。Phase 3 的投递侧工具（`track`/`replan`/`render-execution`/`jd-analyze`）保留为附加 CLI，不再作为产品卖点。Phase 4（全自动 scan、持续情报 OS）仍为规划。

## License

MIT © Peng Kangzhen