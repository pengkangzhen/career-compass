"""Phase 2 匹配引擎 —— 确定性/heuristic，无外部 LLM 调用。

职责：
- 画像 × 岗位族 → match_score + skill_gaps
- 市场信号 → competition_index
- 生成候选 Opportunity 列表（4-7 个）
"""
from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from .schema import (
    Constraints,
    IndustryGraph,
    Opportunity,
    Profile,
    ProjectsFile,
    RoleFamily,
    RoleTaxonomy,
    Signal,
    SkillGap,
    TaxonomyRoleFamily,
    is_placeholder,
)

# geo / 出海标记（constraints.geo 未包含时硬过滤）
_OVERSEAS_MARKERS = ("海外", "硅谷", "美国", "欧洲", "出国", "abroad", "relocation", "博后（海外")
_DOMESTIC_ONLY_VISA = ("国内", "无出国", "不出国", "仅国内")

# 技能别名/子串匹配（中英混排）
_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python", "py"),
    "pytorch": ("pytorch", "torch"),
    "rag": ("rag", "检索增强", "retrieval"),
    "llm": ("llm", "大模型", "gpt", "langchain"),
    "运筹优化": ("运筹", "optimization", "or", "mip", "gurobi", "规划"),
    "机器学习": ("机器学习", "ml", "machine learning"),
    "spark": ("spark",),
    "sql": ("sql",),
    "分布式训练": ("分布式", "deepspeed", "fsdp"),
    "ros": ("ros", "ros2"),
    "计算机视觉": ("cv", "vision", "视觉"),
    "c++": ("c++", "cpp"),
    "分子建模": ("分子", "chem", "化学"),
    "生物统计": ("生物统计", "biostat", "统计"),
}

# 竞争信号关键词
_COMP_HIGH = ("内卷", "过剩", "裁员", "供过于求", "饱和", "竞争激烈", "红海", "降本裁员")
_COMP_LOW = ("缺口", "人才短缺", "需求增长", "供不应求", "蓝海", "紧缺", "扩招")


def _normalize(text: str) -> str:
    return text.strip().lower()


def _skill_tokens(skills: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for s in skills:
        n = _normalize(s)
        out.add(n)
        for alias_key, aliases in _SKILL_ALIASES.items():
            if any(a in n for a in aliases) or n in aliases:
                out.add(alias_key)
    return out


def collect_profile_skills(
    profile: Profile,
    projects: ProjectsFile | None = None,
) -> dict[str, set[str]]:
    """返回 core / adjacent / frontier / all 四套 token 集合。"""
    core = _skill_tokens(profile.skills.core)
    adjacent = _skill_tokens(profile.skills.adjacent)
    frontier = _skill_tokens(profile.skills.frontier)
    if projects:
        proj = _skill_tokens(
            sig for p in projects.projects for sig in p.inferred_signals
        )
        adjacent |= proj
        frontier |= proj
    return {
        "core": core,
        "adjacent": adjacent,
        "frontier": frontier,
        "all": core | adjacent | frontier,
    }


def _skill_matches(required: str, buckets: dict[str, set[str]]) -> str | None:
    """若匹配返回所在层级 core/adjacent/frontier，否则 None。"""
    req = _normalize(required)
    req_tokens = {req}
    for alias_key, aliases in _SKILL_ALIASES.items():
        if any(a in req for a in aliases) or req in aliases:
            req_tokens.add(alias_key)
    for level in ("core", "adjacent", "frontier"):
        if req_tokens & buckets[level]:
            return level
    # 子串 fallback
    for level in ("core", "adjacent", "frontier"):
        for tok in buckets[level]:
            if req in tok or tok in req:
                return level
    return None


def score_profile_vs_role(
    profile: Profile,
    projects: ProjectsFile | None,
    role_family: TaxonomyRoleFamily,
) -> dict:
    """计算 match_score (0-1) 与 skill_gaps 列表。"""
    buckets = collect_profile_skills(profile, projects)
    required = role_family.required_skills
    nice = role_family.nice_to_have

    if not required:
        return {"match_score": 0.5, "skill_gaps": []}

    matched_weights = 0.0
    total_weight = 0.0
    gaps: list[SkillGap] = []

    for skill in required:
        total_weight += 1.0
        level = _skill_matches(skill, buckets)
        if level == "core":
            matched_weights += 1.0
        elif level == "adjacent":
            matched_weights += 0.75
        elif level == "frontier":
            matched_weights += 0.4
            gaps.append(SkillGap(
                skill=skill,
                current_level="frontier",
                target_level="core for target role",
                priority="high",
                notes="已在学习区，需强化到可交付",
            ))
        else:
            gaps.append(SkillGap(
                skill=skill,
                current_level="none",
                target_level="core for target role",
                priority="high",
                notes="缺口技能",
            ))

    for skill in nice:
        total_weight += 0.3
        level = _skill_matches(skill, buckets)
        if level:
            matched_weights += 0.3
        else:
            gaps.append(SkillGap(
                skill=skill,
                current_level="none",
                target_level="nice-to-have",
                priority="medium",
            ))

    match_score = matched_weights / total_weight if total_weight else 0.0
    return {"match_score": round(min(1.0, max(0.0, match_score)), 3), "skill_gaps": gaps}


def _flatten_signals(signals: dict[str, list[Signal]]) -> list[Signal]:
    out: list[Signal] = []
    for sigs in signals.values():
        out.extend(sigs)
    return out


def estimate_competition_index(
    role_family: TaxonomyRoleFamily,
    market_signals: dict[str, list[Signal]],
) -> str:
    """返回 low / medium / high。"""
    text_parts: list[str] = [role_family.role, role_family.industry_id]
    text_parts.extend(role_family.required_skills)
    for sig in _flatten_signals(market_signals):
        text_parts.extend([sig.topic, sig.finding])

    blob = " ".join(text_parts).lower()
    high_hits = sum(1 for k in _COMP_HIGH if k in blob)
    low_hits = sum(1 for k in _COMP_LOW if k in blob)

    # 浅层岗位族默认竞争更高
    shallow_roles = ("应用工程师", "产品经理", "数据分析师", "wrapper")
    if any(s in role_family.role for s in shallow_roles):
        high_hits += 1

    if high_hits > low_hits + 1:
        return "high"
    if low_hits > high_hits + 1:
        return "low"
    return "medium"


def competition_label_to_float(label: str) -> float:
    return {"low": 0.25, "medium": 0.5, "high": 0.75}.get(label, 0.5)


def _is_shallow_node(trap: str, role: TaxonomyRoleFamily) -> bool:
    """浅层定位惩罚：岗位与 trap 关键词重叠。"""
    if not trap:
        return False
    trap_lower = trap.lower()
    shallow_markers = ("api", "wrapper", "只会", "demo", "ppt", "excel", "me-too", "组装")
    role_blob = f"{role.role} {' '.join(role.required_skills)}".lower()
    if any(m in trap_lower for m in shallow_markers):
        if any(m in role_blob for m in ("应用", "产品", "rag", "agent")):
            return True
    return False


def _geo_allows_overseas(constraints: Constraints) -> bool:
    """geo 或 notes 是否允许出海/异地。"""
    if constraints.geo and not any(is_placeholder(g) for g in constraints.geo):
        geo_blob = " ".join(constraints.geo).lower()
        if any(k in geo_blob for k in ("海外", "出国", "全球", "remote", "远程")):
            return True
    notes = (constraints.notes or "").lower()
    if any(k in notes for k in ("出海", "出国", "海外可选")):
        return True
    return False


def _role_requires_overseas(role_family: TaxonomyRoleFamily) -> bool:
    blob = f"{role_family.role} {role_family.typical_seniority} {' '.join(role_family.required_skills)}"
    return any(m in blob for m in _OVERSEAS_MARKERS)


def skill_match_level(
    required: str,
    profile: Profile,
    projects: ProjectsFile | None = None,
) -> str | None:
    """公开 API：技能在画像中的层级 core/adjacent/frontier，未匹配返回 None。"""
    buckets = collect_profile_skills(profile, projects)
    return _skill_matches(required, buckets)


def passes_constraints(
    role_family: TaxonomyRoleFamily,
    constraints: Constraints,
    match_score: float,
) -> bool:
    """硬约束过滤；违反则剔除。"""
    # 低风险偏好 + 高竞争浅层岗
    if constraints.risk_appetite.value == "low":
        if "创业" in role_family.role or match_score < 0.35:
            return False

    # 财务 runway 过短 → 剔除博士/博后级长周期岗
    if constraints.financial_runway_months and constraints.financial_runway_months < 6:
        if re.search(r"博士|博后", role_family.typical_seniority):
            return False

    # geo：未声明出海则剔除明显海外岗
    if constraints.geo and not any(is_placeholder(g) for g in constraints.geo):
        if _role_requires_overseas(role_family) and not _geo_allows_overseas(constraints):
            return False

    # visa / family：国内限定
    visa = (constraints.visa or "").lower()
    if visa and any(k in visa for k in _DOMESTIC_ONLY_VISA):
        if _role_requires_overseas(role_family):
            return False

    return True


def _level_label(score: float) -> str:
    if score >= 0.7:
        return "高"
    if score >= 0.45:
        return "中"
    return "低"


def _wind_from_signals(industry_name: str, signals: dict[str, list[Signal]]) -> tuple[str, str]:
    hits: list[str] = []
    for sig in _flatten_signals(signals):
        blob = f"{sig.topic} {sig.finding}"
        if industry_name[:4] in blob or any(
            kw in blob for kw in industry_name.split("/")[:1]
        ):
            hits.append(f"{sig.topic}: {sig.finding[:80]}")
    if hits:
        return "顺风", "；".join(hits[:2])
    return "弱顺风", "brief 中暂无直接行业信号，按产业结构默认弱顺风"


def _composite_from_scores(
    match_score: float,
    fit: str,
    wind: str,
    risk: str,
    competition: str,
    shallow_penalty: bool,
) -> str:
    score = match_score
    if fit == "高":
        score += 0.15
    elif fit == "低":
        score -= 0.1
    if wind == "顺风":
        score += 0.1
    elif wind == "逆风":
        score -= 0.15
    if risk in ("低", "可逆"):
        score += 0.05
    if competition == "high":
        score -= 0.12
    elif competition == "low":
        score += 0.05
    if shallow_penalty:
        score -= 0.2

    if score >= 0.75:
        return "A"
    if score >= 0.6:
        return "B"
    if score >= 0.45:
        return "C"
    if score >= 0.3:
        return "D"
    return "E"


def generate_candidate_opportunities(
    profile: Profile,
    constraints: Constraints,
    graph: IndustryGraph,
    roles: RoleTaxonomy,
    signals: dict[str, list[Signal]],
    projects: ProjectsFile | None = None,
    *,
    min_count: int = 4,
    max_count: int = 7,
) -> list[Opportunity]:
    """生成 4-7 个候选 Opportunity，Phase 2 字段尽量填充。"""
    candidates: list[tuple[float, Opportunity]] = []

    for rf in roles.role_families:
        scored = score_profile_vs_role(profile, projects, rf)
        match_score = scored["match_score"]
        if not passes_constraints(rf, constraints, match_score):
            continue

        node = graph.find_node(rf.industry_id, rf.subsector_id, rf.value_chain_node_id)
        trap = node.trap if node else ""
        node_name = node.name if node else rf.value_chain_node_id
        industry_name = graph.industry_name(rf.industry_id)
        shallow = _is_shallow_node(trap, rf)

        comp_label = estimate_competition_index(rf, signals)
        comp_float = competition_label_to_float(comp_label)

        if shallow:
            match_score = max(0.0, match_score - 0.15)

        fit = _level_label(match_score)
        wind, wind_rationale = _wind_from_signals(industry_name, signals)
        risk = "低" if constraints.reversibility_bias == "high" else "高"
        composite = _composite_from_scores(
            match_score, fit, wind, risk, comp_label, shallow,
        )

        role_snap = RoleFamily(
            role=rf.role,
            seniority=rf.typical_seniority,
            match_score=match_score,
            competition_index=comp_float,
        )

        costs: list[str] = []
        if shallow and trap:
            costs.append(f"浅层陷阱: {trap}")
        if comp_label == "high":
            costs.append("竞争密度偏高，需差异化叙事")

        opp = Opportunity(
            direction=rf.role,
            industry=industry_name,
            value_chain_node=node_name,
            role_families=[role_snap],
            skill_gaps=scored["skill_gaps"],
            competition_index=comp_float,
            fit=fit,
            fit_rationale=f"技能覆盖 {match_score:.0%}；价值链: {node.value_is_in if node else '—'}",
            match=fit,
            match_rationale="Ikigai+期权 heuristic：core/adjacent 与岗位 required_skills 对齐度",
            wind=wind,
            wind_rationale=wind_rationale,
            risk=risk,
            risk_rationale="结合 constraints.reversibility_bias（低试错成本偏好）默认",
            composite=composite,
            opens_up=[f"{industry_name} · {node_name} 纵深"],
            costs=costs,
            first_step=f"针对 {rf.role} 补齐: "
            + (scored["skill_gaps"][0].skill if scored["skill_gaps"] else "行业调研"),
        )
        candidates.append((match_score, opp))

    candidates.sort(key=lambda x: (-x[0], x[1].composite))
    selected = [o for _, o in candidates[:max_count]]

    if len(selected) < min_count:
        # 不足时用较低分候选补齐
        for _, o in candidates[max_count:]:
            if len(selected) >= min_count:
                break
            if o not in selected:
                selected.append(o)

    return selected[:max_count]
