# Schema 2.0 — 机会矩阵扩展

> Phase 1 引入 Schema 2.0 **基础字段**，向后兼容 v0.1/v0.2 机会矩阵。旧 YAML 无需修改即可加载；新字段均为可选。

## 演进动机

README 北极星要求交付物从「机会矩阵」演进到「求职定位包」，覆盖：

- 行业 / 价值链位置（深 vs 浅）
- 岗位族 + 职级带
- 竞争密度指数
- 技能缺口图

Schema 2.0 在 `Opportunity` 上预留这些字段，Phase 2 匹配引擎写入，Phase 1 仅做模型与文档落地。

## 新增模型

### `RoleFamily`

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | str | 岗位族名称，如 "MLE" / "Applied Scientist" |
| `seniority` | str | 职级带，如 "1-3年" / "博士直聘" |
| `match_score` | float 0–1 | 与画像匹配度（Phase 2 自动算） |
| `competition_index` | float 0–1 | 该岗位族竞争密度 |

### `SkillGap`

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill` | str | 技能名 |
| `current_level` | str | 当前层级：core / adjacent / frontier |
| `target_level` | str | 目标岗位所需层级 |
| `priority` | str | high / medium / low |
| `notes` | str | 补充说明 |

## `Opportunity` 扩展字段（均可选）

| 字段 | 类型 | 说明 |
|------|------|------|
| `industry` | str | 所属行业 / 二级赛道 |
| `value_chain_node` | 价值链环节（深 vs 浅定位） |
| `role_families` | list[RoleFamily] | 推荐岗位族 |
| `skill_gaps` | list[SkillGap] | 技能缺口 |
| `competition_index` | float 0–1 | 方向级竞争密度 |

## 机会矩阵结构（Schema 2.1）

| 字段 | 说明 |
|------|------|
| `unified_theme` | 多条方向共用能力栈的说明 |
| `shared_assets` | 多条方向共用的资产（项目、技能、domain） |
| `primary` | 方向列表 |
| `directions` | **已废弃**，加载时自动迁移为 `primary` |

## 向后兼容

- 未填 Phase 2 字段时，行为与 v0.2 完全一致。
- `render-opportunities` 在 Phase 2 字段存在时展示 industry / 岗位族 / skill_gaps / competition_index。
- Pydantic 校验：`match_score` / `competition_index` 范围 0–1。

## Industry Graph + Role Taxonomy（Phase 2）

- `data/industry_graph.yaml` → `IndustryGraph`, `load_industry_graph`
- `data/role_taxonomy.yaml` → `RoleTaxonomy`, `load_role_taxonomy`
- 匹配引擎见 `docs/matching-engine.md`

## 占位符闸门（intake / validate）

Phase 1 收紧 `validate`，拒绝以下占位内容（大小写不敏感、子串匹配）：

```
(待填), tbd, todo, 待补, 探索中, 待明确, n/a, 待验证, 示例, 请替换, 请填写
```

影响范围：

- `Profile.gaps()` — strength_evidence、skills.core、name、current_role、**education（本硕博院校/专业）**
- `validate_constraints()` — family / runway / employer_preference（**geo/签证/户口已移除**）
- `validate_narrative()` — 职业故事 / 我想要的 / 红线 章节

## 示例

见 `templates/opportunities.example.yaml` 与 `data/examples/opportunities.yaml`。

## 版本对照

| 版本 | 机会矩阵字段 | 校验 |
|------|-------------|------|
| v0.1 | 四层评分 + composite | 基础 gaps |
| v0.2 | 同上 + sectors / projects | strength proof 占位 |
| **Schema 2.0** | + industry / role_families / skill_gaps / competition_index | 全文件占位符 + narrative 章节 |
