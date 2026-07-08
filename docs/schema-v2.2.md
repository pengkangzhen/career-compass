# Schema 2.2 — 正交机会矩阵（能力 × 雇主性质）

> Phase 2.2 核心演进：机会矩阵从「单一方向列表」升级为 **双正交轴 + 交叉单元**。
> 向后兼容 Schema 2.1 的 `primary` / `side` 扁平列表。

## 动机

中国区职业决策常有两个独立问题：

1. **做什么**（能力/行业方向）—— OR 工程师 vs Agent 工程师 vs 教职
2. **在哪类组织做**（雇主性质）—— 民企 vs 央企 vs 事业编 vs 公务员

旧版矩阵把两者混在 `direction` 字符串里，导致：

- 强偏好体制内的用户看不到结构化对比
- Agent 容易只写市场化路径
- `typical_companies` 里的「国企保底」无法评分

## 数据结构

```yaml
generated_on: 2026-07-08
unified_theme: "..."
shared_assets: [...]

capability_axes:    # 轴 1：能力 / 行业（与雇主无关）
  - id: sc_optimization
    name: "供应链 / 物流优化"
    industry: "运筹优化 / 供应链智能化"
    value_chain_node: "网络规划 / 库存优化"

employer_axes:      # 轴 2：雇主性质（与具体技能无关）
  - id: central_soe
    name: "央企"
    stability: high
    ceiling: medium
    entry_paths: ["校园招聘", "社会招聘"]

cross_matrix:       # 交叉单元 = 核心评分实体
  - capability_id: sc_optimization
    employer_id: central_soe
    fit: 高
    composite: B
    entry_mechanism: "央企校园招聘"
    hard_gates: []
    skill_transfer: 高
    skill_transfer_rationale: "..."
    # … 同 Opportunity 的四层评分字段 …

primary: []         # 可选；空则 render 从 cross_matrix 合成最佳列视图
side: []
```

## Constraints 扩展

| 字段 | 说明 |
|------|------|
| `employer_preference.include` | 考虑的雇主类型 id |
| `employer_preference.exclude` | 硬排除 |
| `employer_preference.priority` | 排序与 composite 加权 |
| `employer_preference.strong_preference` | true 时矩阵仅保留 include \ exclude |
| `public_sector_gates.*` | 公务员/事业编 L5 门槛 |

雇主类型定义见 `data/employer_types.yaml`。

## 岗位族扩展

`role_taxonomy.yaml` / `role_taxonomy_public.yaml`：

| 字段 | 说明 |
|------|------|
| `capability_id` | 所属能力轴 |
| `employer_type_id` | 所属雇主轴（默认 `private`） |
| `entry_mechanism` | 入口机制 |
| `hard_gates` | 硬门槛列表 |
| `skill_transfer_default` | L5 默认迁移度 |

## CLI

```bash
uv run career-compass match --write-draft    # 正交矩阵（默认）
uv run career-compass match --legacy         # Schema 2.1 单轴
uv run career-compass render-opportunities   # 渲染交叉表 + 按雇主汇总
```

## Analyze 纪律（playbook 3）

1. 必须先有 `employer_preference`（intake 必问）
2. 每个 `capability_id` 至少覆盖 2 个 `employer_id`（除非 strong_preference 仅 1 列）
3. 体制内单元必须填 `entry_mechanism` / `hard_gates` / `skill_transfer`
4. 禁止把「公务员」与「民企 OR 岗」合并为一个 direction

## 向后兼容

- 旧 `opportunities.yaml` 仅含 `primary`：`uses_orthogonal_matrix()` 为 false，render 走 legacy 视图
- `Opportunity.employer_id` 可选，用于扁平列表标注雇主
- `ranked_primary()` 无 primary 时从 cross_matrix 按能力轴取最佳 cell 合成
