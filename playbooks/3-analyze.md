# Playbook 3 — Analyze（机会矩阵 · 核心交付物）

> 目标：产出**机会矩阵** —— 几个可比较、有依据的职业方向。这是本项目的**主交付物**，不是中间步骤。
> 输出落到 `data/opportunities.yaml`（结构化数据，唯一事实源），再渲染成 `data/opportunities.md`。

## 输入

```bash
uv run career-compass brief
```

可选 —— 用匹配引擎生成**机器初稿**（Phase 2）：

```bash
uv run career-compass match --write-draft   # → data/opportunities.draft.yaml
```

审阅 draft 后复制/修订为 `data/opportunities.yaml`，或从零手写。match 产出含 industry / 岗位族 / skill_gaps / competition_index，但 **fit/match/wind 叙事仍需你按四层框架补全**。

brief 是你唯一的分析依据。brief 里没有的东西，不要凭空用（不要把模型先验当信号）。

## 第一步：列候选方向

不要凭空想。候选方向必须从证据里**长出来**，每个方向能追溯到 brief 里的一条依据。三个来源交叉：
- **目标行业池（`sectors.yaml`）× 你的能力** —— 把 core / 可迁移能力投到宏观热门赛道上（半导体、AI、新能源、生物医药…）。这是首要来源。
- core skill × frontier skill 的**组合**（"X + Y 型的人很少"）
- signals 里提到的**需求增速**方向 + 经历里**可迁移**的能力（如 OR 建模 → ML/定价/风控/供应链优化）

**关键纪律 —— 深 vs 浅**：任何沾到某个 sector 的方向，必须参考该 sector 的 `trap` 来填 `costs`/`risk`。热门赛道里真正的价值在"深"的环节（AI 懂训练、芯片能落地），停在"浅"的环节（只会调 API、只会发论文）就是陷阱——这类方向要在 `costs` 里写明"易被替代/无壁垒"，或直接降 `composite`。

先列 4-7 个候选。**少于 4 个说明 scan 不够**，回 2-scan。

## 第二步：四层框架评分（每个方向都过一遍）

### L1 比较优势 → `fit`（高/中/低）
"在这个方向上，什么是别人难以复制的？" 答不出 → 低。用 `strength_evidence` 的证据，不是用户自评。

### L2 Ikigai 四圈 + 期权 → `match`（高/中/低）
- 四圈交集：热爱(energized_by) × 擅长(core) × 被需要(trends) × 有回报(market)
- **期权价值**：这条路打开的后续可选项越多，分越高（写进 `opens_up`）

### L3 顺风/逆风 → `wind`（顺风/弱顺风/逆风）
从 signals 看需求增速 vs 供给增速。引信号到 `wind_rationale`。矛盾信号要显式标注。

### L4 试错成本 → `risk`（低/高）
走错第一步代价多大？低 = 可试可退（副项目/学习/聊人）；高 = 一次性投入（辞职/出国/读博）。结合 `constraints.risk_appetite` / `reversibility_bias`。

## 第三步：先过 constraints 墙

违反 constraints 的方向（如 geo 限定却要异地）**直接剔除**，不要打低分留它在表里。

## 第四步：填 `opens_up` / `costs` / `first_step`

每个方向还要写：
- `opens_up`：这条路具体通向哪些后续位置/技能/身份（期权价值落地）
- `costs`：选它**排除**了哪些路（机会成本）
- `first_step`：一个**具体、低成本**的第一步（学/试/副项目/聊人，不是辞职）

## 第五步：综合评分 `composite`（A-F）

A=强烈推荐，B=值得认真考虑，C=备选，D=勉强，E/F=基本不考虑。**要敢打低分**，全 A 等于没分析。

## 写入数据

机会矩阵分 **主业**（primary）与 **副业**（side）两层，外加 **统一架构**说明两者如何共用能力栈、互相喂养（不是互斥二选一）。

```yaml
generated_on: 2026-07-04
unified_theme: "能力栈 X 如何同时服务主业 offer 与副业可见度……"
shared_assets:
  - "MAKO / domain 知识 / 核心技能……"
synergy_notes: "副业 demo 如何同时是主业 first_step……"

primary:   # 主业：换 offer / 职级 / 身份
  - direction: "..."
    fit: 高
    fit_rationale: "..."
    # ……同前
    first_step: "..."

side:      # 副业：可见度 / 人脉 / 可选收入；用 synergizes_with 指向协同的主业方向
  - direction: "开源 + 技术博客"
    synergizes_with: ["Agent 平台工程师", "供应链决策 AI"]
    fit: 高
    # ……
    first_step: "..."
```

**划分原则**：
- **主业**：时间投入大头、决定主身份与主现金流的路径（全职 offer、教职、研究院等）
- **副业**：共用同一能力栈，换可见度/人脉/项目收入；很多 `first_step` 与主业重叠——这正是「统一」而非「互质」
- 旧字段 `directions` 仍可读，自动视为 `primary`

然后渲染：
```bash
uv run career-compass render-opportunities
```

## 完成判据

`data/opportunities.md` 生成，**主业 ≥4 个方向**、各字段非空、评分有区分度；**副业 ≥1 个**且写清 `synergizes_with` 与 `unified_theme`。

**到此就是交付物。** 用户想深入某个方向，才进可选的 `4-plan`。不要自动收敛到一个方向。

## 反模式

- ❌ 候选方向只有用户"一直想做的"，没有从证据长出来
- ❌ 所有方向都打高分（不敢做减法）
- ❌ constraints 当软建议而不是墙
- ❌ 把"收敛到一个方向"在这一步做了（那是 4-plan 的事，且要用户自己选）
