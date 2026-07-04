# Career-Compass

> 投简历**之前**的职业规划工具。先让 AI 真正懂你——**个人画像 × 行业趋势 × 产业格局**——再产出一张**有证据、可比较、经得起压测的机会矩阵**：给你几个清晰的方向，而不是替你拍板一条路。

## 为什么不直接问 ChatGPT？

直接问 AI 求职建议 = 零结构、零证据、零可复现。Career-Compass 把"职业规划"做成**数据 + 框架 + 压测**的工程问题：

| 直接问 AI / 普通测评 | Career-Compass |
|---|---|
| 反问"你觉得你适合做什么"，或扔张空表让你自己填 | **引导式**：Agent 像职业顾问一样带你聊，边聊边把你的话提炼成结构化画像，只就缺口/证据追问 |
| 模糊印象当依据 | 联网检索的每条趋势**带来源 + 日期 + 置信度**，区分事实与推测 |
| 一个拍脑袋的答案 | 产出**机会矩阵**：N 个方向 × 4 维评分，**决策权在你** |
| 一次性乐观推演 | pre-mortem + tripwire 压测，主动尝试杀死自己的策略 |

## 亮点

- 🧠 **引导式构建个人画像** —— 不用预填、非繁琐问答；Agent 引导你聊，边聊边提炼技能分层、补全优势证据，把约束（年龄/学历/地域/风险偏好）当硬墙
- 📂 **扫描真实项目自动取证** —— `scan-projects` 从你点名的代码库提取技术栈 / 依赖 / 规模 / 论文成果，作为画像的硬证据（opt-in，只看你指定的目录，不扫整盘）
- 🌐 **联网检索行业趋势与产业格局** —— AI 按你的画像派生查询、检索，信号带来源入库（trends / market / landscape 三类）
- 🎯 **机会矩阵是核心交付物** —— 个人 × 信号 × 9 大热门赛道交叉，几个方向逐一打分（契合度 / Ikigai+期权 / 顺风逆风 / 可逆性），**给选项，不替你选**
- 🏭 **预置 9 大热门赛道池** —— 半导体 / AI / 新能源 / 创新药 / 量子 / 机器人 / 商业航天 / AI医学 / 材料，每个标明"**价值在哪 / 陷阱在哪**"（深水区 vs 浅层陷阱）
- 🛡️ **压力测试** —— 选定方向后做 pre-mortem + 挑战关键假设 + 设 tripwire；没被压过的策略不算完成
- 🔧 **数据/逻辑分离，可迭代** —— 画像/信号是唯一事实源，分析逻辑在 playbooks，git 记录策略演进

## 适合谁

- 在"学术界 vs 工业界、研究 vs 工程"之间没想清楚的人
- 想把职业决策从"拍脑袋"变成"有据可查"的人
- 愿意和 Agent 聊一阵（被引导、不用预填表）的人

## 快速开始

```bash
git clone https://github.com/pengkangzhen/career-compass.git
cd career-compass
uv sync
claude                                    # 在本项目目录打开 Claude Code
# 然后说："帮我做职业规划" —— Agent 会引导你聊着天把画像建好（自动从 templates 拷贝并填 data/）
```

> 依赖：[uv](https://docs.astral.sh/uv/) + [Claude Code](https://claude.com/claude-code)（或任何会读 `CLAUDE.md` 的 AI 编码 CLI）。

## 工作流

```
1-intake       Agent 引导式构建画像  → profile.yaml / narrative.md / constraints.yaml  [必选]
2-scan         联网检索趋势          → signals/*.yaml（带来源+日期）                     [必选]
3-analyze      四层框架评分          → opportunities.yaml → opportunities.md  ★交付物★  [必选]
4-plan         展开路径              → strategy.md（用户选定方向后才进）                 [可选]
5-stress-test  压力测试              → 修订 strategy.md                                  [可选]
```

**1-3 是主流程，终点是机会矩阵。** 4-5 可选，且由你自己选定方向后才进入。

## CLI

| 命令 | 作用 |
|---|---|
| `uv run career-compass validate` | 校验画像完整性、标出缺口 |
| `uv run career-compass brief` | 聚合所有数据为分析用 brief |
| `uv run career-compass scan-plan` | 基于画像派生检索查询 |
| `uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]` | 追加一条外部信号 |
| `uv run career-compass scan-projects <path>...` | 扫描指定项目目录，自动提取证据 |
| `uv run career-compass render-opportunities` | **渲染机会矩阵** |
| `uv run career-compass render-strategy` | 渲染 strategy.md 骨架 |

## 设计原则

- **数据与代码分离**：用户/外部数据在 `data/`；分析逻辑在 `playbooks/`（纯 Markdown）；`src/` 只做校验/抓取/渲染。
- **唯一事实源**：`profile.yaml` 是画像唯一来源；`opportunities.yaml` 是矩阵唯一来源，`.md` 是渲染产物，覆盖重写、历史交 git。
- **证据驱动**：优势必须挂证据，信号必须带来源，方向评分必须引依据。
- **给选项不拍板**：核心交付物是机会矩阵（几个方向），不替用户收敛到一个。

## 状态

v0.2 alpha。CLI 管道 + 项目扫描已端到端验证；`SKILL.md` 作为可安装 skill 的触发机制仍在打磨。欢迎 issue / PR。

## License

MIT © Peng Kangzhen
