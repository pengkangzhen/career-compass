"""渲染辅助：聚合 brief、渲染机会矩阵（核心交付物）、渲染 strategy.md 骨架。"""
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Template

from .schema import (
    SkillGap,
    load_constraints,
    load_industry_graph,
    load_opportunities,
    load_profile,
    load_projects,
    load_role_taxonomy,
    load_sectors,
    load_signals,
)


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

    lines: list[str] = ["# Career-Compass Brief\n"]

    lines.append("## Profile")
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
            lines.append(f"- **{rf.role}** ({rf.typical_seniority}) — 需: {req}")

    return "\n".join(lines)


_OPPORTUNITIES_TEMPLATE = """# 机会矩阵 — {{ generated_on }}

> **本项目的核心交付物。** 下列方向按综合评级排序，每条均附四维评分依据、期权与成本。
> **系统不替你做选择** —— 请结合自己的价值观、硬约束与风险偏好自行判断。

## 四维评分说明

每个方向从四个维度打分，便于横向比较：

| 维度 | 问什么 | 常见评级 |
|------|--------|----------|
| **比较优势** | 在这个方向上，什么是别人难以复制的？（看 strength_evidence，不是自评） | 高 / 中 / 低 |
| **匹配与期权** | 热爱 × 擅长 × 被需要 × 有回报；以及这条路能打开多少后续选项 | 高 / 中 / 低 |
| **顺风/逆风** | 外部市场：需求在涨还是已经饱和内卷？（看 signals） | 顺风 / 弱顺风 / 中 / 逆风 |
| **可逆性** | 选错了能否低成本退出？先试再定，还是一选就很难回头？ | 可逆 / commit |

**综合评级 A–F**：A=四维整体强 · B=值得认真比较 · C=备选 · D=勉强或仅特定价值观下考虑

## 如何使用

1. 看 **总览表**，比较四个维度与综合评级
2. 看 **对比摘要**，快速权衡「通向什么 / 排除什么」
3. 对感兴趣的方向读 **详情**，核对依据是否认可
4. 自行选定 1 个方向后 → `playbooks/4-plan.md`（可选）

## 总览

| # | 方向 | 比较优势 | 匹配与期权 | 顺风/逆风 | 可逆性 | 综合 |
|---|------|----------|------------|-----------|--------|------|
{% for o in ranked -%}
| {{ loop.index }} | {{ o.direction }} | {{ o.fit }} | {{ o.match }} | {{ o.wind }} | {{ o.risk }} | {{ o.composite }} |
{% endfor %}

## 对比摘要

| 方向 | 综合 | 比较优势（一句话） | 主要机会成本 | 可逆第一步 |
|------|------|-------------------|-------------|-----------|
{% for o in ranked -%}
| {{ o.direction }} | {{ o.composite }} | {{ o.fit_rationale[:60] }}{% if o.fit_rationale|length > 60 %}…{% endif %} | {{ o.costs[0] if o.costs else "—" }} | {{ o.first_step[:50] if o.first_step else "—" }}{% if o.first_step and o.first_step|length > 50 %}…{% endif %} |
{% endfor %}

## 各方向详情

{% for o in ranked %}
### {{ loop.index }}. {{ o.direction }}　·　综合 {{ o.composite }}

{% if o.industry or o.value_chain_node or o.competition_index is not none -%}
**定位**
{% if o.industry -%}
- 行业: {{ o.industry }}
{% endif -%}
{% if o.value_chain_node -%}
- 价值链: {{ o.value_chain_node }}
{% endif -%}
{% if o.competition_index is not none -%}
- 竞争密度: {{ "%.2f"|format(o.competition_index) }}
{% endif -%}
{% endif -%}

{% if o.role_families -%}
**岗位族**

| 岗位 | 职级带 | 匹配度 | 竞争指数 |
|------|--------|--------|----------|
{% for rf in o.role_families -%}
| {{ rf.role }} | {{ rf.seniority or "—" }} | {{ rf.match_score if rf.match_score is not none else "—" }} | {{ rf.competition_index if rf.competition_index is not none else "—" }} |
{% endfor -%}
{% endif -%}

{% if o.skill_gaps -%}
**技能缺口**
{% for g in o.skill_gaps -%}
- **{{ g.skill }}** ({{ g.priority }}) — 当前 {{ g.current_level or "?" }} → 目标 {{ g.target_level or "?" }}{% if g.notes %} · {{ g.notes }}{% endif %}
{% endfor -%}
{% endif -%}

| 维度 | 评级 | 依据 |
|------|------|------|
| 比较优势 | {{ o.fit }} | {{ o.fit_rationale }} |
| 匹配与期权 | {{ o.match }} | {{ o.match_rationale }} |
| 顺风/逆风 | {{ o.wind }} | {{ o.wind_rationale }} |
| 可逆性 | {{ o.risk }} | {{ o.risk_rationale }} |

**打开的选项**（选这条路通向什么）：
{% for x in o.opens_up -%}
- {{ x }}
{% else -%}
- (待填)
{% endfor %}

**机会成本**（选它会排除什么）：
{% for x in o.costs -%}
- {{ x }}
{% else -%}
- (待填)
{% endfor %}

**可逆的第一步**：{{ o.first_step or "(待填)" }}

---
{% endfor %}

## 下一步

从矩阵中**自行选定**一个方向 → `playbooks/4-plan.md` 展开路径（可选 `playbooks/5-stress-test.md` 压测）。
"""


def render_opportunities(opportunities_path: Path) -> str:
    matrix = load_opportunities(opportunities_path)
    return Template(_OPPORTUNITIES_TEMPLATE).render(
        generated_on=matrix.generated_on.isoformat(),
        ranked=matrix.ranked(),
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

{% for item in industries -%}
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

{% for g in skill_gaps -%}
- **{{ g.skill }}** — {{ g.priority }} · {{ g.notes }}
{% else -%}
- (暂无结构化缺口 —— 运行 `career-compass match` 生成)
{% endfor %}

## 90 天第一步

{% for step in first_steps -%}
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

{% for story in evidence_stories -%}
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

{% for step in action_steps -%}
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
