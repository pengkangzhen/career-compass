# Matching Engine（Phase 2）

> 确定性/heuristic 匹配引擎，**无外部 LLM API 调用**。产出候选 `Opportunity` 供 Agent 或用户审阅，不替代 playbook 四层框架的人工判断。

## 数据依赖

| 文件 | 模型 | 说明 |
|------|------|------|
| `data/industry_graph.yaml` | `IndustryGraph` | 行业 → 子赛道 → 价值链节点（含 trap / value_is_in） |
| `data/role_taxonomy.yaml` | `RoleTaxonomy` | 岗位族 × 图谱节点，含 required_skills、公司梯队 |
| `data/profile.yaml` | `Profile` | 技能 core/adjacent/frontier |
| `data/projects.yaml` | `ProjectsFile` | inferred_signals 并入 adjacent |
| `data/constraints.yaml` | `Constraints` | 硬约束过滤 |
| `data/signals/*.yaml` | `Signal` | 竞争密度与 wind 启发 |

## 核心 API（`src/career_compass/match.py`）

### `score_profile_vs_role(profile, projects, role_family)`

- 对 `required_skills` 做别名/子串匹配（中英混排）
- core=1.0, adjacent=0.75, frontier=0.4 加权
- 返回 `{ match_score: 0-1, skill_gaps: list[SkillGap] }`

### `estimate_competition_index(role_family, market_signals)`

- 关键词启发：内卷/过剩 → `high`；缺口/紧缺 → `low`
- 浅层岗位族（应用工程师等）默认 +1 high 信号
- 返回 `low` | `medium` | `high`（写入 Opportunity 时映射为 0.25/0.5/0.75）

### `generate_candidate_opportunities(...)`

1. 遍历 taxonomy 全部岗位族
2. `passes_constraints` 硬过滤（risk_appetite、financial_runway）
3. 浅层 trap 惩罚（match_score -0.15，composite 额外降权）
4. 规则映射 fit/match/wind/risk/composite
5. 取 Top 4-7

## CLI

```bash
uv run career-compass match                  # 打印摘要
uv run career-compass match --write-draft    # → data/opportunities.draft.yaml
uv run career-compass render-pack            # → data/job_pack.md
uv run career-compass render-pack --stdout
```

## 推荐 analyze 工作流

```
brief → match --write-draft → Agent 审阅/补 rationale → opportunities.yaml → render-opportunities → render-pack
```

Draft 是**机器初稿**；四层框架的叙事（fit_rationale、opens_up、costs）仍需 Agent 按 playbook 3 补全或修订。

## 已知局限（v1）

- 技能匹配为关键词/heuristic，无语义 embedding
- constraints 仅覆盖 risk/runway，未解析 geo/visa 与岗位地域
- composite 为简单规则，非帕累托优化
- industry_graph 仅 4 行业深度覆盖，其余为占位
- wind 依赖 signals 与行业名子串匹配，可能漏检

## Phase 3 方向

- 投递漏斗反推权重
- JD 聚类驱动的 skill_gaps
- 更细 geo/公司梯队约束
- 可选 LLM 层仅用于 narrative，保持在 playbook 侧
