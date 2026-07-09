# Matching Engine（Phase 2）

> 确定性/heuristic 匹配引擎，**无外部 LLM API 调用**。产出候选 `Opportunity` 供 Agent 或用户审阅，不替代 playbook 四层框架的人工判断。

用户分型、扩展 ROI 与数据分层见 [architecture-users.md](architecture-users.md)。

## 数据依赖

| 文件 | 模型 | 说明 |
|------|------|------|
| `data/industry_graph.yaml` | `IndustryGraph` | 行业 → 子赛道 → 价值链节点（含 trap / value_is_in / **market_saturation**） |
| `data/cross_track.yaml` | `CrossTrackFile` | 交叉赛道注册（方法论可迁移 + 行业缺口，全用户共享） |
| `data/role_taxonomy.yaml` | `RoleTaxonomy` | 岗位族 × 图谱节点，含 required_skills、公司梯队 |
| `data/profile.yaml` | `Profile` | 技能 core/adjacent/frontier |
| `data/projects.yaml` | `ProjectsFile` | inferred_signals 并入 adjacent |
| `data/constraints.yaml` | `Constraints` | 硬约束过滤 |
| `data/signals/*.yaml` | `Signal` | 竞争密度与 wind 启发 |
| `data/skill_aliases.yaml` | `SkillAliasesFile` | 技能 canonical → 别名；JD 词表扩展 |
| `data/capability_registry.yaml` | `CapabilityRegistry` | capability_id → 展示名（正交矩阵） |
| `data/method_patterns.yaml` | `MethodPatternsFile` | OR/LLM/ML 方法论 marker、亲和度阈值、交叉打分权重 |
| `data/jd_link_rules.yaml` | `JdLinkRulesFile` | 收藏 JD → capability_id / 雇主 hint（`jd_link.py`） |

注册表加载见 `src/career_compass/registry.py`。**扩展匹配能力优先改 YAML，不改 Python。**

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
brief → match --write-draft → Agent 审阅/补 rationale → opportunities.yaml → render-opportunities
```

（可选）`render-pack` 汇总视图 · `render-execution` 行动手册 · `track`/`replan` 长期修正

Draft 是**机器初稿**；四层框架的叙事（fit_rationale、opens_up、costs）仍需 Agent 按 playbook 3 补全或修订。

## 已知局限（v1）

- 技能匹配为关键词/heuristic，无语义 embedding
- **行业域亲和**：`industry_graph.yaml` 各行业 `domain_markers`；未知行业默认 `method_patterns.yaml` → `unknown_domain_anchor`（0.35）
- **别名安全**：短中文别名需词界匹配，避免「化学」误命中「强化学习」
- **交叉赛道**（`cross_track.py` + `data/cross_track.yaml`）：方法论可迁移 ≠ 行业背景匹配
- **赛道饱和**（`industry_graph.yaml` 节点 `market_saturation`）：全用户共享的市场标注；仅当画像与该赛道 **亲和度 ≥ 50%** 或 **技能匹配 ≥ 55%** 时对当前用户生效；`scan` 信号可动态抬高竞争感知
- constraints 仅覆盖 risk/runway/employer_scope（**geo/签证/户口已移除**：北斗星只定择业方向，不选城市；海外方向默认纳入矩阵）
- composite 为简单规则，非帕累托优化
- industry_graph 已深度覆盖 5 行业（AI/LLM、OR/供应链、机器人、生物医药、半导体）；其余 sectors 为宏观池
- wind 依赖 signals 与行业名子串匹配，可能漏检
- 正交矩阵稀疏：无 taxonomy 岗位的 (capability × employer) 单元不会出现

## Phase 2.2（已实现）

- `employer_types.yaml` + `role_taxonomy_public.yaml`
- `match` 默认输出 `capability_axes × employer_axes → cross_matrix`
- `constraints.employer_preference` + L5 `skill_transfer` / `hard_gates`
- 见 `docs/schema-v2.2.md`

## Phase 3 方向

- 投递漏斗反推权重
- JD 聚类驱动的 skill_gaps
- 更细公司梯队约束（geo 已移除，不再作为方向约束）
- 可选 LLM 层仅用于 narrative，保持在 playbook 侧
