# Schema 2.3 — 资格闸门（EligibilityGate）

> Phase 2.3：在 Schema 2.2 正交矩阵之上，新增与「domain fit」正交的「hiring fit」确定性引擎。
> 修复系统性缺陷：系统曾把「研究对齐」当「招聘资格」，导致 211 高校教职被推荐给二本第一学历候选人（现实中 CV screen 几乎必被过滤）。

## 动机

中国区招聘有一类**与能力无关**的硬筛：

- 211/985 高校教职的**第一学历门槛**（本科须 985/211/双一流）
- 公务员**年龄线 35**
- 头部研究院/研究岗对第一学历偏严（非 JD 明文，CV screen 启发式）
- 「已取得博士学位」类 JD 对**博士在读**不满足
- 部分高校「**避免近亲繁殖**」政策（本校博士求职同校教职）

旧矩阵只衡量 domain fit（四层评分 + composite），把这类门槛当 soft cost，于是二本本+211博的候选人会看到「高校教职 × 事业编」评 A。Schema 2.3 把 hiring fit 拆成独立闸门，在 composite **之前**裁决。

## 核心概念

| 概念 | 含义 | 由谁衡量 |
|------|------|----------|
| **domain fit** | 研究/能力对齐度 | match 引擎四层评分（fit/match/wind/risk → composite） |
| **hiring fit** | 招聘资格（CV screen 是否过） | 资格闸门 `eligibility.py` |

二者正交：domain fit 高 ≠ hiring fit 通过。

## EligibilityResult

```python
@dataclass
class EligibilityResult:
    status: str          # "pass" | "fail" | "review"
    rationale: str
    composite_cap: str | None   # "D" when fail, "B" when review, None when pass
    blocked: bool        # True when fail
    rules_matched: list[str]
```

裁决规则：

- `fail` → `composite` 不得 > `composite_cap`（通常 D），`cell.blocked=True`
- `review` → `composite` 不得 > B（保留但降权）
- `pass` → 不干预

## 规则文件 `data/hiring_eligibility_rules.yaml`

每条规则：

| 字段 | 说明 |
|------|------|
| `id` | 规则 id |
| `applies_to` | 命中条件（多键 AND，单键内列表 OR）：`employer_subtypes` / `institution_tier_min` / `institution_tiers` / `role_keywords` |
| `conditions` | `bachelor_tier.{allow,deny,uncertain}` / `phd_in_hand_required` / `age_max` / `same_institution` |
| `effect` | `block` / `warn` / `cap_composite_at` |
| `composite_cap` | fail 时的封顶字母 |
| `rationale` | 闸门依据 |
| `sources` | 来源（不杜撰 URL，用「用户案例」「待补: ...」） |

P0 seed 7 条：`faculty_211_first_degree`、`faculty_985_first_degree`、`faculty_regular_undergraduate`、`phd_in_hand_required`、`same_institution_avoidance`、`civil_service_age_35`、`first_degree_barrier_head_research`。

多规则取最严：fail > review > pass。`effect=block` 时 deny→fail、uncertain→review；`effect=warn` 时 deny/uncertain→review（不阻断）。

## 数据模型扩展

### `EducationSummary`（`schema.py`）

```python
class EducationSummary(BaseModel):
    first_degree_tier: str | None       # 本科 school_tier
    highest_degree_tier: str | None
    highest_degree_school: str | None
    phd_status: str  # "in_hand" | "enrolled" | "none"
    pedigree_pattern: str  # e.g. "二本本_211硕博"
    same_institution_risk: bool  # 博士校 == 典型目标院校（match 时算）
```

`derive_education_summary(profile) -> EducationSummary`。`Education.is_first_degree` 对本科自动置位。

### `TaxonomyRoleFamily` 新字段

| 字段 | 说明 |
|------|------|
| `institution_tier` | 211 / 985 / 普通本科 / 科研院所 / 高职高专 / "" |
| `employer_subtype` | university_faculty / research_institute / civil_service_admin / ...（比 `employer_type_id` 更细，资格规则匹配用） |

### `MatrixCell` / `Opportunity` / `ScoredPath` 新字段

| 字段 | 默认 | 说明 |
|------|------|------|
| `eligibility` | `"pass"` | pass / fail / review |
| `eligibility_rationale` | `""` | 闸门依据 |
| `domain_fit` | `""` | 与 `fit` 同义，澄清语义 |
| `hiring_fit` | `""` | pass→高 / review→中 / fail→低 |
| `blocked` | `False` | fail 时 True |
| `institution_tier`（仅 MatrixCell） | `""` | 从 role_family 同步 |
| `employer_subtype`（仅 MatrixCell） | `""` | 从 role_family 同步 |
| `eligibility_rules`（仅 MatrixCell） | `[]` | 命中规则 id |

## 院校层级排序（institution_tier_min 比较用）

```
985(6) > 211(5) = 双一流(5) > 一本(4) > 二本(3) = 普通本科(3) > 三本(2) = 应用型本科(2) > 高职高专(1) > 科研院所(3) > ""(0)
```

## match 引擎集成

`generate_orthogonal_matrix` 在 `passes_constraints` 之后、`_build_matrix_cell` 之前对每个候选 role_family 运行 `evaluate_eligibility`：

- `strong_preference=True` 且 `eligibility.blocked` → 剔除该 cell
- 否则保留 cell，composite 经 `apply_composite_cap` 封顶，`blocked=True` 标记
- 同 (capability_id, employer_type_id) 多 role 并列时取资格更严者（让门槛显形）

`ranked_primary` / `synthesized_primary` / `best_cell_per_capability` 默认 `include_blocked=False`，跳过 blocked cell。

## validate 校验规则

`validate_eligibility_with_profile(matrix, profile)`：

- **ERROR**：cell `eligibility=fail` 但 `composite ∈ {A,B,C}`（封顶未执行）
- **ERROR**：211/985 教职格 `eligibility=pass`，但画像第一学历 ∈ {二本,三本}（资格闸门未运行或错误通过）
- **WARNING**：211/985 教职格 `eligibility=pass` 且无 `rationale`（确认是否已运行）

`cmd_validate` 在 `opportunities.yaml` 存在时自动调用。

## render 渲染

- 交叉矩阵详情新增「资格关」行（评级 + 依据）
- 主网格 blocked cell 用 `~~D~~` 删除线标注
- 新增「资格关未过（blocked — 仅完整对比，不参与推荐）」专节
- `ranked_primary` 已剔除 blocked cell

## 向后兼容

- 旧 `opportunities.yaml` 无 eligibility 字段：Pydantic 默认 `eligibility="pass"`、`blocked=False`，照常加载渲染
- 旧 `role_taxonomy` 无 `institution_tier`/`employer_subtype`：默认空串，资格闸门不触发（`validate` 会对 211/985 教职格报错提示补全）

## CLI

```bash
uv run career-compass match --write-draft    # 自动跑资格闸门
uv run career-compass validate               # 校验资格闸门字段
uv run career-compass render-opportunities   # 渲染含资格关行 + blocked 专节
```
