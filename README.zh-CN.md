[English](README.md) | **简体中文**

# 北斗星

> 投简历**之前**的职业生涯决策引擎。自动分析**用户画像 × 产业结构 × 行业趋势 × 市场竞争**，在内卷环境下给出**精准、个性化、可执行**的职业规划——从「选什么行业、找什么岗位」到「怎么进、怎么避坑、怎么验证」。

## 项目目标

北斗星要解决的不是「AI 帮你想一个职业方向」，而是在**竞争激烈、供给过剩**的环境里，把职业决策做成**有证据、可复现、可迭代**的系统问题：

| 你要回答的问题 | 北斗星怎么帮 |
|---|---|
| **选什么行业？** | 产业结构分析：价值链位置、护城河/陷阱、红蓝海与内卷密度 |
| **找什么岗位？** | 岗位族匹配：职级带、技能缺口、目标公司梯队、地域策略 |
| **我凭什么进？** | 证据化画像：项目/论文/经历 → 可核验优势，对齐 JD 要求 |
| **现在进还来得及吗？** | 趋势 + 时机窗口：赛道周期、个人时间线（毕业/年龄/签证） |
| **会不会选错？** | 可逆性设计 + 压测 + tripwire：先试再 commit，假设失效自动预警 |
| **投了没回音怎么办？** | 反馈闭环：投递漏斗 → 反推定位偏差 → 调整权重（规划中） |

**核心原则不变**：系统给**排序后的选项和依据**，不替用户拍板；价值观、家庭/地理硬约束、最终方向选择，仍由用户确认。

## 为什么不直接问 ChatGPT？

直接问 AI 求职建议 = 零结构、零证据、零可复现、容易追热点踩浅坑。北斗星把职业规划做成**数据 + 引擎 + 压测**的工程问题：

| 直接问 AI / 普通测评 | 北斗星 |
|---|---|
| 反问「你觉得适合做什么」，或扔空表让你填 | **自动采集 + 短对话补缺口**：从简历/项目/公开资料抽取画像，只就 values/constraints/证据追问 |
| 模糊印象、训练数据先验当依据 | 每条趋势/供需信号**带来源 + 日期 + 置信度**；分析只引用 brief 里的证据 |
| 一个拍脑袋的方向 | **分层交付**：行业 → 赛道 → 岗位族 → 公司梯队 → 90 天行动 |
| 只讲「顺风」，不讲内卷 | 显式量化**竞争密度**、浅层陷阱、学历/年龄硬门槛 |
| 一次性乐观推演 | pre-mortem + tripwire；没被压过的策略不算完成 |

## 系统架构（目标形态）

```
L0 证据采集（自动）          简历/CV · 代码项目 · 公开资料 · 短对话（values/constraints）
        ↓
L1 市场情报引擎（自动）      趋势 Agent · 供需/薪酬 Agent · 产业结构 Agent · 岗位图谱 Agent
        ↓
L2 匹配引擎（规则 + 模型）   硬约束过滤 → 多维评分 → 技能缺口推断 → 内卷/可进入性校正
        ↓
L3 决策交付（个性化）        行业/赛道推荐 · 岗位/职级推荐 · 求职定位包 · 路径 + 压测
```

**内卷不是忽略项，是评分维度之一**：供给增速、JD 技能堆叠、浅层岗位（如纯 API wrapper）、学历/年龄卡位，都会进入推荐权重——「精准」是 fit × 窗口 × 可进入性 × 可逆性的帕累托前沿，不是追最热赛道。

## 完整交付物（目标）

主交付物从「机会矩阵」演进为**求职定位包**，覆盖四层：

### 战略层 — 往哪走
- 行业 / 二级赛道排序（含深 vs 浅：价值链哪一环、对应 `trap`）
- 红蓝海与**竞争密度指数**
- 时机窗口（赛道周期 + 个人时间线）

### 战术层 — 进什么门
- **岗位族推荐**（如 MLE / Applied Scientist / OR Engineer / PM-Tech）
- **职级带**（应届 / 1–3 年 / 博士直聘 / 博后过渡）
- **目标公司梯队**（冲刺 / 主投 / 保底）
- **地域策略**（一线 / 新一线 / 出海，对齐 constraints）

### 执行层 — 怎么进
- **技能缺口图**（目标岗位 JD 聚类 vs 现有 evidence）
- **叙事定位**（一句话 pitch、简历/作品集重构建议）
- **投递策略**（渠道、内推 vs 海投、可逆实验设计）

### 反馈层 — 跑起来之后
- **投递漏斗** —— `track funnel`：applied → interview → offer
- **Replan** —— 反馈反推 composite 降档、追加 skill_gaps → `opportunities.revised.yaml`

## 亮点

### 已实现（v0.3 · Phase 1–3）
- 🧠 **引导式构建个人画像** —— Agent 边聊边提炼 `profile.yaml` / `narrative.md` / `constraints.yaml`；约束当硬墙
- 📂 **项目自动取证** —— `scan-projects` 从指定代码库提取技术栈 / 依赖 / 规模 / 论文成果（opt-in，不扫整盘）
- 🌐 **画像驱动的信号采集** —— `scan-plan` 派生检索查询（含 sectors/constraints）；`new-signal` 入库并同 topic 去重
- ⚙️ **Pipeline 编排** —— `status` / `run --stage` 检测阶段、预检与下一步提示
- 🎯 **机会矩阵** —— 个人 × 信号 × 赛道池，四层评分；Schema 2.0 岗位族/技能缺口/竞争指数
- 🗺️ **Industry Graph + Role Taxonomy** —— 结构化产业/岗位知识 + **geo 硬过滤**
- 📊 **匹配引擎 v1** —— `match`：技能对齐、竞争启发、浅层 trap 惩罚
- 📦 **求职定位包** —— `render-pack` → `job_pack.md`
- 🚀 **求职执行包** —— `render-execution`：pitch、证据故事、简历建议、投递策略 → `execution_pack.md`
- 📋 **投递追踪 + Replan** —— `track` / `replan` 反馈闭环
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

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
claude                                    # 在本项目目录打开 Claude Code
# 然后说："帮我做职业规划" —— Agent 会引导你聊着天把画像建好（自动从 templates 拷贝并填 data/）
```

**macOS 桌面 App（MVP）** — 四个主界面：**个人画像 · 行业趋势 · 职位收藏 · 机会矩阵**

```bash
uv sync --group gui
uv run career-compass-app
```

> 依赖：[uv](https://docs.astral.sh/uv/) + [Claude Code](https://claude.com/claude-code)（或任何会读 `CLAUDE.md` 的 AI 编码 CLI）。GUI 使用 macOS 系统 WebKit（pywebview），无需 Tk。Dock 图标见 `assets/app-icon.png`（北斗七星）。

## 工作流

**当前（v0.2，Agent 驱动）：**

```
1-intake       引导式构建画像     → profile.yaml / narrative.md / constraints.yaml  [必选]
2-scan         联网检索趋势       → signals/*.yaml（带来源+日期）                     [必选]
3-analyze      四层框架评分       → opportunities.yaml → opportunities.md  ★交付物★  [必选]
4-plan         展开路径           → strategy.md（用户选定方向后才进）                 [可选]
5-stress-test  压力测试           → 修订 strategy.md                                  [可选]
```

**目标（自动化 pipeline）：**

```
intake（短聊补 values/constraints）→ scan（Agent 集群自动采集）→ analyze（匹配引擎）
    → 求职定位包（行业 + 岗位 + 缺口 + 行动）→ [可选] plan + stress-test + 反馈闭环
```

1–3 是主流程。4–5 在用户从推荐中**自行选定**方向后进入。

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
| `uv run career-compass render-pack [--stdout]` | 渲染求职定位包 → `job_pack.md` |
| `uv run career-compass render-execution [--stdout]` | 渲染求职执行包 → `execution_pack.md` |
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

**v0.3 · Phase 1–3 已落地** — 从画像 → 匹配 → 定位包 → 执行包 → 投递追踪 → replan 闭环可用。Phase 4（全自动 scan、持续情报 OS）仍为规划。

## License

MIT © Peng Kangzhen
