"""渲染辅助：聚合 brief、渲染机会矩阵（核心交付物）、渲染 strategy.md 骨架。"""
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template

from .cross_track import render_cross_track_section
from .schema import (
    CapabilityAxis,
    EducationStatus,
    Opportunity,
    SkillGap,
    load_constraints,
    load_employer_types,
    load_industry_graph,
    load_opportunities,
    load_profile,
    load_projects,
    load_role_taxonomy,
    load_sectors,
    load_signals,
)


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "career_compass").exists():
            return parent
    return Path.cwd()


_REPO_DATA = _find_repo_root() / "data"


def brief(
    profile_path: Path,
    constraints_path: Path,
    narrative_path: Path,
    signals_dir: Path,
    sectors_path: Path,
    projects_path: Path,
    industry_graph_path: Path | None = None,
    role_taxonomy_path: Path | None = None,
) -> str:
    """聚合所有数据文件为一份分析用 brief。"""
    profile = load_profile(profile_path)
    constraints = load_constraints(constraints_path)
    signals = load_signals(signals_dir)
    sectors = load_sectors(sectors_path)
    projects = load_projects(projects_path).projects if projects_path.exists() else []
    narrative = narrative_path.read_text(encoding="utf-8") if narrative_path.exists() else "(narrative.md 尚未填写)"

    lines: list[str] = ["# 北斗星 Brief\n"]

    lines.append("## Profile")
    if profile.education:
        lines.append("### 教育背景")
        for edu in profile.sorted_education():
            tier = f" ({edu.school_tier})" if edu.school_tier else ""
            grad = edu.graduation_hint()
            time_part = f"，{grad}" if grad else ""
            status = "在读" if edu.status == EducationStatus.enrolled else "已毕业"
            dept = f" · {edu.department}" if edu.department else ""
            extra: list[str] = []
            if edu.ranking_or_gpa:
                extra.append(edu.ranking_or_gpa)
            if edu.honors:
                extra.append(edu.honors)
            if edu.thesis_or_focus:
                extra.append(f"方向: {edu.thesis_or_focus}")
            if edu.advisor:
                extra.append(f"导师: {edu.advisor}")
            tail = f" — {' · '.join(extra)}" if extra else ""
            lines.append(
                f"- **{edu.level_label()}** {edu.school}{tier} · {edu.major}{dept}"
                f" · {status}{time_part}{tail}"
            )
        lines.append("")
    lines.append("```yaml\n" + yaml.safe_dump(
        profile.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    ) + "```")

    lines.append("## Constraints（硬边界，分析必须遵守）")
    lines.append("```yaml\n" + yaml.safe_dump(
        constraints.model_dump(mode="json"), allow_unicode=True, sort_keys=False
    ) + "```")

    lines.append("## Narrative（职业故事 / 偏好 / 红线）\n")
    lines.append(narrative)

    lines.append("\n## 目标行业池（用户调研；source 未补齐的视为待验证）")
    if sectors:
        for s in sectors:
            tag = "✅已验证" if s.source.strip() else "⚠️待验证"
            lines.append(f"\n- **{s.name}** [{tag}]")
            if s.why_hot:
                lines.append(f"  - why hot: {s.why_hot}")
            if s.value_is_in:
                lines.append(f"  - 价值在: {s.value_is_in}")
            if s.trap:
                lines.append(f"  - ⚠️陷阱: {s.trap}")
            if s.fit_notes:
                lines.append(f"  - 与你的交叉: {s.fit_notes}")
    else:
        lines.append("\n(尚无目标行业池 —— 把调研的赛道写进 data/sectors.yaml)")

    lines.append("\n## Projects（scan-projects 自动采集的证据）")
    if projects:
        for p in projects:
            head = f"**{p.name}** — {p.description}" if p.description else f"**{p.name}**"
            lines.append(f"\n- {head}")
            if p.inferred_signals:
                lines.append(f"  - 信号: {', '.join(p.inferred_signals)}")
            if p.key_dependencies:
                lines.append(f"  - 关键依赖: {', '.join(p.key_dependencies)}")
            lang = ", ".join(f"{k}({v})" for k, v in list(p.languages.items())[:4])
            if lang:
                lines.append(f"  - 语言: {lang}")
            bits = [f"{p.scale.files} files"]
            if p.scale.commits is not None:
                bits.append(f"{p.scale.commits} commits")
            if p.scale.has_tests:
                bits.append("有测试")
            if p.artifacts:
                bits.append("·".join(p.artifacts))
            lines.append(f"  - 规模/成果: {' · '.join(bits)}")
    else:
        lines.append("\n(尚无项目证据 —— 跑 `uv run career-compass scan-projects <dir...>` 采集)")

    lines.append("\n## External Signals（带来源与日期）")
    if signals:
        for domain, sigs in signals.items():
            lines.append(f"\n### {domain}")
            for s in sigs:
                url = f"  {s.source_url}" if s.source_url else ""
                lines.append(
                    f"- [{s.confidence}] {s.topic}: {s.finding} — {s.source}{url} ({s.retrieved_on})"
                )
    else:
        lines.append("\n(尚无外部信号 —— 先跑 playbook 2-scan)")

    if industry_graph_path and industry_graph_path.exists():
        graph = load_industry_graph(industry_graph_path)
        lines.append("\n## Industry Graph（产业结构 · Phase 2）")
        for ind in graph.industries[:6]:
            lines.append(f"\n### {ind.name}")
            if ind.why_hot:
                lines.append(f"- 热度: {ind.why_hot}")
            for sub in ind.subsectors[:2]:
                lines.append(f"- **{sub.name}**")
                for node in sub.value_chain_nodes[:2]:
                    val = node.value_is_in[:60] + ("…" if len(node.value_is_in) > 60 else "")
                    lines.append(f"  - {node.name}: 价值在「{val}」")
                    if node.trap:
                        trap = node.trap[:60] + ("…" if len(node.trap) > 60 else "")
                        lines.append(f"    - ⚠️ trap: {trap}")

    if role_taxonomy_path and role_taxonomy_path.exists():
        taxonomy = load_role_taxonomy(role_taxonomy_path)
        lines.append("\n## Role Taxonomy（岗位族 · Phase 2 摘要）")
        for rf in taxonomy.role_families[:8]:
            req = ", ".join(rf.required_skills[:4])
            emp = f" · 雇主={rf.employer_type_id}" if rf.employer_type_id else ""
            lines.append(f"- **{rf.role}** ({rf.typical_seniority}) — 需: {req}{emp}")

    employer_path = (sectors_path.parent / "employer_types.yaml")
    if employer_path.exists():
        et = load_employer_types(employer_path)
        lines.append("\n## Employer Types（雇主性质轴 · Schema 2.2）")
        for e in et.employer_types:
            lines.append(f"- **{e.name}** (`{e.id}`) — 稳定:{e.stability} · 天花板:{e.ceiling}")
            if e.trap:
                lines.append(f"  - ⚠️陷阱: {e.trap}")

    return "\n".join(lines)


# Jinja 空白纪律（避免 Markdown 粘行 / 表格断裂）：
# - 列表、段落：标题行与 `- item` 之间保留空行；{% for %} 不要用 {%- 吃掉空行
# - 表格：表头分隔线 `|---|` 与首行数据之间不能有空行；表体用 {% for row -%} 贴紧
# - 块级元素（## / | table）前保留空行；{% endif %} 后若接下一块，模板里显式留空行
_OPPORTUNITIES_TEMPLATE = """# 机会矩阵 — {{ generated_on }}

> **本项目的核心交付物。** 多条可比、有证据、可执行的方向，按综合评级排序。
> **系统不替你做选择** —— 请结合价值观、硬约束与风险偏好自行判断。

{% if unified_theme %}
## 统一架构

{{ unified_theme }}

{% endif %}
{% if shared_assets %}
**共享资产**（多条方向共用，不必重复建设）：

{% for a in shared_assets %}
- {{ a }}
{% endfor %}

{% endif %}
## 每个方向回答四个问题

| 模块 | 问什么 |
|------|--------|
| **往哪走** | 去哪个行业/赛道、在价值链哪一环创造价值 |
| **凭什么** | 你有什么可验证优势、还缺什么 |
| **值不值得现在进** | 竞争多激烈、现在是顺风还是逆风 |
| **坑在哪** | 浅层热门岗、主要机会成本、试错代价 |

下方 **核心竞争力 / Ikigai / 行业趋势 / 试错成本** 是矩阵内的评分维度（与上方四个用户模块不是同一套分类）：

| 维度 | 问什么 | 常见评级 |
|------|--------|----------|
| **核心竞争力** | 在这个方向上，什么是别人难以复制的？ | 高 / 中 / 低 |
| **Ikigai** | 热爱 × 擅长 × 被需要 × 有回报（期权见 `opens_up`） | 高 / 中 / 低 |
| **行业趋势** | 外部市场：需求在涨还是饱和内卷？ | 顺风 / 弱顺风 / 中 / 逆风 |
| **试错成本** | 走错第一步要付出多少？ | 低 / 高 |

**综合评级 A–F**：A=强烈推荐 · B=值得认真比较 · C=备选 · D=勉强

---

{% if cross_track_section %}
{{ cross_track_section }}
{% endif %}
## 机会矩阵

> 下列方向已综合你的能力、偏好与约束；按综合评级排序，**系统不替你做选择**。
> **矩阵按「方向」（你解决什么问题 + 行业赛道）组织，不按岗位头衔**——AI 浪潮下岗位名快速生灭，但「解决什么问题、用什么能力组合」相对稳定；岗位名称与相关企业仅供投递检索参考。

### 方向总览

| # | 方向 | 岗位名称 | 相关企业 | 核心工作 | 组织类型 | 核心竞争力 | Ikigai | 行业趋势 | 试错成本 | 综合 |
|---|------|----------|----------|----------|----------|----------|------------|-----------|--------|------|
{% for row in primary_rows -%}
| {{ loop.index }} | {{ row.positioning }}{% if row.track and row.track != row.positioning %} · {{ row.track }}{% endif %} | {{ row.top_role }} | {{ row.related_companies }} | {{ row.summary[:48] }}{% if row.summary|length > 48 %}…{% endif %} | {{ row.emp_label }} | {{ row.opp.fit }} | {{ row.opp.match }} | {{ row.opp.wind }} | {{ row.opp.risk }} | {{ row.opp.composite }} |
{% else -%}
| — | (暂无方向) | — | — | — | — | — | — | — | — | — |
{% endfor %}

### 方向对比摘要

| 方向 | 综合 | 核心竞争力（一句话） | 主要机会成本 | 试错第一步 |
|------|------|-------------------|-------------|-----------|
{% for row in primary_rows -%}
| {{ row.positioning }}{% if row.track and row.track != row.positioning %} · {{ row.track }}{% endif %} | {{ row.opp.composite }} | {{ row.opp.fit_rationale[:60] }}{% if row.opp.fit_rationale|length > 60 %}…{% endif %} | {{ row.opp.costs[0] if row.opp.costs else "—" }} | {{ row.opp.first_step[:50] if row.opp.first_step else "—" }}{% if row.opp.first_step and row.opp.first_step|length > 50 %}…{% endif %} |
{% endfor %}

### 方向详情

{% for row in primary_rows %}
#### {{ loop.index }}. {{ row.positioning }}（{{ row.emp_label }}）　·　综合 {{ row.opp.composite }}

> {{ row.summary }}

**往哪走**

{% set o = row.opp %}

{% if o.industry %}- 行业/赛道：{{ o.industry }}
{% endif %}
{% if o.value_chain_node %}- 价值链位置：{{ o.value_chain_node }}
{% endif %}
{% if o.role_families %}
- 市场称呼示例（岗位名会变，能力组合才是锚点；仅供投递检索）：

| 当前常见称呼 | 资历 | 匹配度 |
|-------------|------|--------|
{% for rf in o.role_families -%}
| {{ rf.role }} | {{ rf.seniority or "—" }} | {{ rf.match_score if rf.match_score is not none else "—" }} |
{% endfor %}

{% endif %}
**凭什么**

| 维度 | 评级 | 依据 |
|------|------|------|
| 核心竞争力 | {{ o.fit }} | {{ o.fit_rationale }} |
{% if o.skill_gaps %}
- 还缺什么：

{% for g in o.skill_gaps %}
  - **{{ g.skill }}**（{{ g.priority }}）— 当前 {{ g.current_level or "?" }}，目标 {{ g.target_level or "?" }}{% if g.notes %} · {{ g.notes }}{% endif %}
{% endfor %}

{% endif %}
**值不值得现在进**

| 维度 | 评级 | 依据 |
|------|------|------|
| 行业趋势 | {{ o.wind }} | {{ o.wind_rationale }} |
| Ikigai | {{ o.match }} | {{ o.match_rationale }} |

**坑在哪**

| 维度 | 评级 | 依据 |
|------|------|------|
| 试错成本 | {{ o.risk }} | {{ o.risk_rationale }} |

**主要机会成本**

{% for x in o.costs %}
- {{ x }}
{% else %}
- (待填：浅层岗位陷阱、易被替代风险等)
{% endfor %}

**打开的选项**

{% for x in o.opens_up %}
- {{ x }}
{% else %}
- (待填)
{% endfor %}

**试错第一步**：{{ o.first_step or "(待填)" }}

---
{% endfor %}

## 下一步（可选）

**核心交付到此结束。** 请从矩阵中**自行选定**方向；以下为可选延伸：

- **方向深化**：`playbooks/4-plan.md` → `strategy.md`（可选 `5-stress-test` 压测）
- **战术延伸**：`render-execution` → 行动手册（简历、投递策略）
- **长期修正**：开始投递后用 `track` / `replan` 迭代机会矩阵
"""


def _resolve_opportunity_display(
    o: Opportunity,
    *,
    cap_by_name: dict[str, CapabilityAxis],
    emp_by_id: dict[str, str],
    companies_by_role: dict[str, dict[str, list[str]]] | None = None,
) -> dict:
    """为总览表解析展示字段（兼容未填充 capability_name 的旧 YAML）。

    `companies_by_role`: role 名称 → typical_companies dict（A/B/C → list）。
    若提供，则为每条方向查 related_companies（取 A 档，无则取 B 档，无则 "—"）。
    """
    cap_name = o.capability_name
    if not cap_name:
        if "（" in o.direction:
            cap_name = o.direction.split("（", 1)[0].strip()
        else:
            cap_name = o.direction

    emp_label = o.employer_label
    if not emp_label:
        if o.employer_id and o.employer_id in emp_by_id:
            emp_label = emp_by_id[o.employer_id]
        elif "（" in o.direction:
            emp_label = o.direction.split("（", 1)[1].rstrip("）").strip()
        else:
            emp_label = "—"

    top_role = o.role_families[0].role if o.role_families else ""
    positioning = cap_name
    track = o.industry or cap_name

    summary = o.summary or o.value_chain_node or ""
    if not summary:
        cap = cap_by_name.get(cap_name)
        if cap:
            summary = cap.summary or cap.value_chain_node or ""
    if not summary and "价值链:" in o.fit_rationale:
        summary = o.fit_rationale.split("价值链:", 1)[1].strip()
    if not summary:
        summary = "—"

    related_companies = "—"
    if companies_by_role and top_role:
        tiers = companies_by_role.get(top_role)
        if tiers:
            picked = tiers.get("A") or tiers.get("B") or []
            if picked:
                related_companies = " · ".join(picked[:4])

    return {
        "opp": o,
        "cap_name": cap_name,
        "positioning": positioning,
        "emp_label": emp_label,
        "top_role": top_role or "—",
        "track": track,
        "summary": summary,
        "related_companies": related_companies,
    }


def _display_rows(
    opps: list[Opportunity],
    *,
    cap_by_name: dict[str, CapabilityAxis],
    emp_by_id: dict[str, str],
    companies_by_role: dict[str, dict[str, list[str]]] | None = None,
) -> list[dict]:
    return [
        _resolve_opportunity_display(
            o,
            cap_by_name=cap_by_name,
            emp_by_id=emp_by_id,
            companies_by_role=companies_by_role,
        )
        for o in opps
    ]


def _load_companies_by_role(opportunities_path: Path) -> dict[str, dict[str, list[str]]]:
    """加载 role_taxonomy（含 public），构建 role 名 → typical_companies 映射。

    仅在 opportunities.yaml 同目录或仓库 data/ 下查找；缺失则返回空 dict。
    """
    from .schema import load_role_taxonomy

    candidates = [
        opportunities_path.parent / "role_taxonomy.yaml",
        opportunities_path.parent.parent / "data" / "role_taxonomy.yaml",
        _REPO_DATA / "role_taxonomy.yaml",
    ]
    for p in candidates:
        if p.exists():
            tax = load_role_taxonomy(p)
            return {rf.role: rf.typical_companies for rf in tax.role_families if rf.typical_companies}
    return {}


def render_opportunities(
    opportunities_path: Path,
    profile_path: Path | None = None,
) -> str:
    matrix = load_opportunities(opportunities_path)
    cap_by_name = {c.name: c for c in matrix.capability_axes}
    emp_by_id = {e.id: e.name for e in matrix.employer_axes}
    companies_by_role = _load_companies_by_role(opportunities_path)
    ctx = dict(
        cap_by_name=cap_by_name,
        emp_by_id=emp_by_id,
        companies_by_role=companies_by_role,
    )

    cross_section = ""
    prof_path = profile_path or opportunities_path.parent / "profile.yaml"
    if prof_path.is_file():
        cross_section = render_cross_track_section(load_profile(prof_path), matrix)

    return Template(_OPPORTUNITIES_TEMPLATE).render(
        generated_on=matrix.generated_on.isoformat(),
        unified_theme=matrix.unified_theme,
        shared_assets=matrix.shared_assets,
        cross_track_section=cross_section,
        ranked_primary=matrix.ranked_primary(),
        primary_rows=_display_rows(matrix.ranked_primary(), **ctx),
    )


# strategy.md 骨架（可选阶段）。
_STRATEGY_TEMPLATE = """# Career Strategy — {{ date }}　·　方向：{{ direction | default("(待选定)") }}

> 由 playbook 4-plan 生成（用户从机会矩阵里选定一个方向后才进入此阶段）。每次覆盖重写，历史在 git 里。

## 选定方向及理由
{{ direction_rationale | default("(待填：为什么从机会矩阵里选这个，为什么不选第二名)") }}

## 路径

### 短期 (0-6 月)
{{ short_term | default("(待填：下一步具体动作)") }}

### 中期 (6-18 月)
{{ mid_term | default("(待填)") }}

### 长期 (1-3 年)
{{ long_term | default("(待填：保留分叉点，不要写成预言)") }}

## 关键假设与退出条件
> 每条路径写明"假设 X 成立"和"若 Y 发生则退出/转向"。由 playbook 5-stress-test 挑战。

{{ assumptions | default("(待填)") }}
"""


def render_strategy(ctx: dict) -> str:
    return Template(_STRATEGY_TEMPLATE).render(**ctx)


_JOB_PACK_TEMPLATE = """# 求职定位包 v1 — {{ generated_on }}

> 由 `career-compass render-pack` 从 opportunities.yaml + profile 渲染。改数据源后重新渲染，不要手改。

## 一句话定位

{{ pitch }}

## Top 行业 / 赛道（{{ top_n }}）

{% for item in industries %}
### {{ loop.index }}. {{ item.name }}
- 价值链: {{ item.value_chain }}
- 综合评级: {{ item.composite }}
- 竞争密度: {{ item.competition }}

{% endfor %}
## 推荐岗位族

| 方向 | 职级带 | 匹配度 | 目标公司 A 档 |
|------|--------|--------|---------------|
{% for r in roles -%}
| {{ r.direction }} | {{ r.seniority }} | {{ r.match_score }} | {{ r.companies_a }} |
{% endfor %}

## 技能缺口（跨方向汇总）

{% for g in skill_gaps %}
- **{{ g.skill }}** — {{ g.priority }} · {{ g.notes }}
{% else %}
- (暂无结构化缺口 —— 运行 `career-compass match` 生成)
{% endfor %}

## 90 天第一步

{% for step in first_steps %}
1. {{ step }}
{% endfor %}

## 下一步

- 从机会矩阵中**自行选定** 1 个方向 → `playbooks/4-plan.md`
- 更新画像/信号后重跑: `uv run career-compass match` → 人工审阅 → `render-opportunities` / `render-pack`
"""


def render_job_pack(
    opportunities_path: Path,
    profile_path: Path,
    role_taxonomy_path: Path | None = None,
    *,
    top_n: int = 3,
) -> str:
    """渲染求职定位包 v1 markdown。"""
    matrix = load_opportunities(opportunities_path)
    profile = load_profile(profile_path)
    ranked = matrix.ranked()

    taxonomy_by_role: dict[str, dict[str, list[str]]] = {}
    if role_taxonomy_path and role_taxonomy_path.exists():
        tax = load_role_taxonomy(role_taxonomy_path)
        for rf in tax.role_families:
            taxonomy_by_role[rf.role] = rf.typical_companies

    core_skills = ", ".join(profile.skills.core[:5])
    top_dir = ranked[0].direction if ranked else "(待定)"
    pitch = f"{profile.current_role or '候选人'} · 核心技能 {core_skills} → 优先探索 {top_dir}"

    industries = []
    seen: set[str] = set()
    for o in ranked:
        key = o.industry or o.direction
        if key in seen:
            continue
        seen.add(key)
        industries.append({
            "name": o.industry or o.direction,
            "value_chain": o.value_chain_node or "—",
            "composite": o.composite,
            "competition": f"{o.competition_index:.2f}" if o.competition_index is not None else "—",
        })
        if len(industries) >= top_n:
            break

    roles = []
    gap_map: dict[str, SkillGap] = {}
    for o in ranked[:top_n + 2]:
        rf = o.role_families[0] if o.role_families else None
        companies = taxonomy_by_role.get(o.direction, {}).get("A", [])
        roles.append({
            "direction": o.direction,
            "seniority": rf.seniority if rf else "—",
            "match_score": f"{rf.match_score:.2f}" if rf and rf.match_score is not None else "—",
            "companies_a": ", ".join(companies[:3]) if companies else "(见 role_taxonomy)",
        })
        for g in o.skill_gaps:
            if g.skill not in gap_map or g.priority == "high":
                gap_map[g.skill] = g

    skill_gaps = sorted(gap_map.values(), key=lambda g: (0 if g.priority == "high" else 1, g.skill))
    first_steps = [o.first_step for o in ranked[:3] if o.first_step]

    return Template(_JOB_PACK_TEMPLATE).render(
        generated_on=matrix.generated_on.isoformat(),
        pitch=pitch,
        top_n=top_n,
        industries=industries,
        roles=roles,
        skill_gaps=skill_gaps,
        first_steps=first_steps or ["补齐最高优先级技能缺口", "与目标岗位从业者做 2 次信息访谈"],
    )


_EXECUTION_PACK_TEMPLATE = """# 求职执行包 — {{ generated_on }}

> Phase 3 交付物：从定位到投递的可执行材料。数据源 opportunities + profile + narrative；由 `render-execution` 渲染，不要手改。

## 一句话 Pitch

{{ pitch }}

## 证据故事（投递叙事素材）

{% for story in evidence_stories %}
### {{ loop.index }}. {{ story.claim }}
- **证据**: {{ story.proof }}
- **怎么用**: 在简历/面试中强调「{{ story.hook }}」

{% endfor %}
## 简历重构建议

- **置顶技能关键词**: {{ resume_keywords }}
- **项目排序**: 按目标方向「{{ top_direction }}」重排，把 {{ top_project_hint }} 放首位
- **避免**: 堆「学习能力」等空话；每条 bullet 挂数字或交付物

## JD 对齐清单（Top 方向）

**目标**: {{ top_direction }} · 综合 {{ top_composite }}

| 维度 | 建议 |
|------|------|
| 行业/价值链 | {{ top_industry }} · {{ top_value_chain }} |
| 岗位族 | {{ top_role }} |
| 竞争密度 | {{ top_competition }} |
| 优先补齐缺口 | {{ top_gaps }} |

## 投递策略

| 梯队 | 策略 |
|------|------|
| A 档（冲刺） | {{ tier_a }} |
| B 档（主投） | {{ tier_b }} |
| C 档（保底） | {{ tier_c }} |

**渠道优先级**: 内推 > 官网 > 猎头（有 domain 证据时内推转化率更高）

## 90 天行动

{% for step in action_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}

## 追踪与 Replan

投递后记录:
```bash
uv run career-compass track add "公司" "岗位" --tier B --direction "{{ top_direction }}"
uv run career-compass track update <id> rejected --feedback "反馈原文"
uv run career-compass track funnel
uv run career-compass replan --write   # 反馈反推修订矩阵
```

## 红线提醒（来自 narrative / constraints）

{{ red_lines }}
"""


def render_execution_pack(
    opportunities_path: Path,
    profile_path: Path,
    narrative_path: Path,
    constraints_path: Path,
    role_taxonomy_path: Path | None = None,
) -> str:
    """渲染求职执行包（Phase 3）。"""
    matrix = load_opportunities(opportunities_path)
    profile = load_profile(profile_path)
    constraints = load_constraints(constraints_path) if constraints_path.exists() else None
    narrative = narrative_path.read_text(encoding="utf-8") if narrative_path.exists() else ""

    ranked = matrix.ranked()
    top = ranked[0] if ranked else None

    core_skills = ", ".join(profile.skills.core[:6])
    top_dir = top.direction if top else "(待定)"
    pitch = f"{profile.current_role or '候选人'} · {core_skills} → {top_dir}"

    evidence_stories = []
    for i, se in enumerate(profile.strength_evidence[:4]):
        evidence_stories.append({
            "claim": se.claim,
            "proof": se.proof[:200],
            "hook": se.claim.split("擅长")[-1].strip() if "擅长" in se.claim else se.claim[:40],
        })

    taxonomy_companies: dict[str, dict[str, list[str]]] = {}
    if role_taxonomy_path and role_taxonomy_path.exists():
        tax = load_role_taxonomy(role_taxonomy_path)
        for rf in tax.role_families:
            taxonomy_companies[rf.role] = rf.typical_companies

    companies = taxonomy_companies.get(top_dir, {}) if top else {}
    tier_a = ", ".join(companies.get("A", [])[:4]) or "(见 role_taxonomy / 自行调研)"
    tier_b = ", ".join(companies.get("B", [])[:4]) or "(同行业 B 档公司)"
    tier_c = ", ".join(companies.get("C", [])[:4]) or "(保底：国企/研究院/成熟业务线)"

    top_gaps = ", ".join(g.skill for g in (top.skill_gaps[:5] if top else [])) or "运行 match / jd-analyze"

    rf0 = top.role_families[0] if top and top.role_families else None
    action_steps = []
    if top and top.first_step:
        action_steps.append(top.first_step)
    action_steps.extend([
        f"针对缺口补齐: {top_gaps.split(',')[0] if top_gaps else '技能调研'}",
        "准备 2 版简历：研究向 / 工程向",
        "本周完成 1 次目标方向信息访谈",
        "开始 B 档主投，保留 1-2 个 A 档冲刺",
    ])

    red_lines = narrative
    if constraints and constraints.notes:
        red_lines = (constraints.notes + "\n\n" + narrative)[:800]

    return Template(_EXECUTION_PACK_TEMPLATE).render(
        generated_on=matrix.generated_on.isoformat(),
        pitch=pitch,
        evidence_stories=evidence_stories or [{"claim": "(待填)", "proof": "补齐 strength_evidence", "hook": "—"}],
        resume_keywords=core_skills,
        top_direction=top_dir,
        top_project_hint=profile.strength_evidence[0].claim[:30] if profile.strength_evidence else "最强项目",
        top_composite=top.composite if top else "—",
        top_industry=top.industry if top else "—",
        top_value_chain=top.value_chain_node if top else "—",
        top_role=rf0.role if rf0 else top_dir,
        top_competition=f"{top.competition_index:.2f}" if top and top.competition_index is not None else "—",
        top_gaps=top_gaps,
        tier_a=tier_a,
        tier_b=tier_b,
        tier_c=tier_c,
        action_steps=action_steps[:6],
        red_lines=red_lines[:600] or "(见 constraints.yaml / narrative.md)",
    )


# ---------- Pareto 前沿视图 ----------

_PARETO_TEMPLATE = """## Pareto 前沿 — 多目标决策视图

> 字母档（A-F）把多个维度压成一个分数，隐含「系统知道你的偏好」。
> 现实中职业选择是多目标问题——核心竞争力、Ikigai、行业趋势、试错成本、
> 资格门槛、竞争密度——彼此不可公度。
>
> **Pareto 前沿** = 在所有维度上都没有其他方向严格优于的方向。
> 它们之间没有客观优劣，**需要你做价值判断**。
> 字母档仍保留作为参考，但前沿视图才是「系统不替你做选择」的真正落点。

### 前沿方向（{{ front|length }} / {{ total }}）

{% if front %}
| 方向 | {% for d in dims %}{{ d.label }} | {% endfor %}综合(参考) | 独占强项 |
|------|{% for d in dims %}----|{% endfor %}------|---------|
{% for e in front -%}
| {{ e.label }} | {% for d in dims %}{{ e.scores[d.key] }} | {% endfor %}{{ e.composite }} | {{ e.distinctive or '—' }} |
{% endfor %}

**如何读**：
{% for e in front %}
- **{{ e.label }}**（综合 {{ e.composite }}）
{%- if e.distinctive %} · 独占强项：{{ e.distinctive }}{% endif %}
{%- if e.costs %} · 注意：{{ e.costs }}{% endif %}
{% endfor %}
{% else %}
（无前沿方向——所有候选都被资格关 blocked，或矩阵为空）
{% endif %}

{% if dominated %}
### 被支配方向（{{ dominated|length }}）

> 这些方向在所有维度上都不优于某个前沿方向。若仍想投，需要明确「我换取了什么」。

| 方向 | 被这些方向支配 | 综合(参考) |
|------|---------------|------|
{% for e in dominated -%}
| {{ e.label }} | {{ e.dominated_by }} | {{ e.composite }} |
{% endfor %}
{% endif %}

{% if dimensions_explainer %}
### 维度说明

| 维度 | 含义 | 数据来源 |
|------|------|---------|
{% for d in dims -%}
| {{ d.label }} | {{ d.desc }} | {{ d.source }} |
{% endfor %}

> 想看不同维度组合的前沿？运行 `career-compass pareto --dims fit,match,wind`。
> 想看被资格关 blocked 的方向？加 `--include-blocked`。
{% endif %}
"""


_PARETO_DIMENSIONS_META: tuple[dict[str, str], ...] = (
    {"key": "fit", "label": "核心竞争力", "desc": "你能拿出的不可复制优势", "source": "ScoredPath.fit (高/中/低)"},
    {"key": "match", "label": "Ikigai", "desc": "热爱×擅长×被需要×回报的交集", "source": "ScoredPath.match"},
    {"key": "wind", "label": "行业趋势", "desc": "外部市场需求趋势", "source": "ScoredPath.wind (顺风/逆风)"},
    {"key": "trial_cost", "label": "试错", "desc": "走错第一步的代价（低=好）", "source": "ScoredPath.risk 反向"},
    {"key": "hiring_fit", "label": "资格", "desc": "与 fit 正交的招聘资格关", "source": "ScoredPath.hiring_fit / eligibility"},
    {"key": "competition", "label": "竞争", "desc": "市场拥挤度（低=好）", "source": "ScoredPath.competition_index 反向"},
)


def _format_dim_score(score: float) -> str:
    """0-1 数值 → 紧凑展示：保留 1 位小数。"""
    return f"{score:.1f}"


def _cell_costs_summary(cell) -> str:
    if not cell.costs:
        return ""
    # 取第一条非 replan 标记的成本，避免重复
    for c in cell.costs:
        if not c.startswith("[replan]"):
            return c[:60] + ("…" if len(c) > 60 else "")
    return cell.costs[0][:60]


def render_pareto_view(
    opportunities_path: Path,
    *,
    dimensions: tuple[str, ...] | None = None,
    include_blocked: bool = False,
    explain_dimensions: bool = True,
) -> str:
    """渲染 Pareto 前沿 markdown 段落。

    dimensions: 维度 key 元组；None 用 pareto.DEFAULT_DIMENSIONS。
    include_blocked: 是否纳入 eligibility=fail/blocked 的 cell（默认排除，让前沿可读）。
    """
    from .pareto import DIM_LABEL_ZH, pareto_from_matrix

    matrix = load_opportunities(opportunities_path)
    if dimensions is None:
        report = pareto_from_matrix(matrix)
    else:
        # 自定义维度子集
        from .pareto import compute_pareto_front
        cells = matrix.cross_matrix if matrix.uses_orthogonal_matrix() else matrix.primary
        report = compute_pareto_front(
            cells, dimensions=dimensions, exclude_blocked=not include_blocked,
        )

    dims_meta = tuple(
        m for m in _PARETO_DIMENSIONS_META if m["key"] in report.dimensions
    )

    def _entry_view(e):
        scores_view = {
            m["key"]: _format_dim_score(e.vector.get(m["key"], 0.5))
            for m in dims_meta
        }
        distinctive_zh = "、".join(
            DIM_LABEL_ZH[d] for d in e.distinctive_dims
        ) if e.distinctive_dims else ""
        return {
            "label": e.label,
            "scores": scores_view,
            "composite": e.cell.composite,
            "distinctive": distinctive_zh,
            "costs": _cell_costs_summary(e.cell),
        }

    return Template(_PARETO_TEMPLATE).render(
        dims=dims_meta,
        front=[_entry_view(e) for e in report.front],
        dominated=[
            {
                "label": e.label,
                "dominated_by": "、".join(e.dominated_by[:3])
                + (f" 等 {len(e.dominated_by)} 个" if len(e.dominated_by) > 3 else ""),
                "composite": e.cell.composite,
            }
            for e in report.dominated
        ],
        total=report.size,
        dimensions_explainer=explain_dimensions,
    )
