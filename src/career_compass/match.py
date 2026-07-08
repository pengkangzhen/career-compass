"""Phase 2 匹配引擎 —— 确定性/heuristic，无外部 LLM 调用。

职责：
- 画像 × 岗位族 → match_score + skill_gaps
- 市场信号 → competition_index
- 生成候选 Opportunity 列表（4-7 个）
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Iterable

from .eligibility import (
    apply_composite_cap,
    composite_to_hiring_fit,
    evaluate_eligibility,
)
from .schema import (
    CapabilityAxis,
    Constraints,
    EmployerAxis,
    EmployerTypesFile,
    IndustryGraph,
    MatrixCell,
    Opportunity,
    OpportunityMatrix,
    Profile,
    ProjectsFile,
    RoleFamily,
    RoleTaxonomy,
    Signal,
    SkillGap,
    TaxonomyRoleFamily,
    is_placeholder,
)

# Schema 2.3 资格闸门规则文件（match 阶段加载；缺失则放行）
_ELIGIBILITY_RULES_FILENAME = "hiring_eligibility_rules.yaml"

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


# ---------- Schema 2.2 正交矩阵（能力 × 雇主性质）----------

_CAPABILITY_LABELS: dict[str, str] = {
    "sc_optimization": "供应链 / 物流优化",
    "or_ml_hybrid": "OR+ML 混合工程",
    "decision_agent_or": "决策智能 Agent（OR × LLM）",
    "llm_agent_app": "LLM / Agent 应用",
    "ai_training": "MLE / 模型训练",
    "academia_research": "高校教职 / 科研",
    "applied_research": "科研院所应用研究",
    "policy_admin": "政策 / 综合管理（公务员）",
}


def capability_id_for_role(role_family: TaxonomyRoleFamily) -> str:
    if role_family.capability_id:
        return role_family.capability_id
    return role_family.value_chain_node_id or role_family.id


def capability_label(capability_id: str, fallback_role: str = "") -> str:
    return _CAPABILITY_LABELS.get(capability_id) or fallback_role or capability_id


def passes_employer_scope(role_family: TaxonomyRoleFamily, constraints: Constraints) -> bool:
    allowed = constraints.allowed_employer_ids()
    return role_family.employer_type_id in allowed


def _employer_composite_boost(employer_id: str, constraints: Constraints) -> float:
    pref = constraints.employer_preference
    if not pref.priority:
        return 0.0
    if employer_id not in pref.priority:
        return -0.03 if pref.strong_preference else 0.0
    idx = pref.priority.index(employer_id)
    n = len(pref.priority)
    return 0.1 * (n - idx) / n


def _skill_transfer_for_role(
    role_family: TaxonomyRoleFamily,
    match_score: float,
) -> tuple[str, str]:
    if role_family.skill_transfer_default:
        level = role_family.skill_transfer_default
        return level, f"taxonomy 默认技能迁移度: {level}"
    if role_family.employer_type_id == "civil_service":
        return "低", "公务员路径以行测/申论/行政能力为主，专业技术迁移有限"
    if match_score >= 0.7:
        return "高", f"岗位 required_skills 与画像对齐 {match_score:.0%}"
    if match_score >= 0.45:
        return "中", f"部分技能可迁移，需补缺口（对齐度 {match_score:.0%}）"
    return "低", f"技能栈偏离较大（对齐度 {match_score:.0%}）"


def _apply_public_sector_gates(
    role_family: TaxonomyRoleFamily,
    constraints: Constraints,
    composite: str,
    costs: list[str],
) -> str:
    """L5：体制内硬门槛 → 可能下调 composite。"""
    gates = constraints.public_sector_gates
    emp = role_family.employer_type_id
    if emp not in ("civil_service", "public_institution", "central_soe", "local_soe"):
        return composite

    penalty = 0
    if constraints.age and constraints.age >= 35 and emp == "civil_service":
        costs.append("年龄接近/超过部分公务员岗位上限")
        penalty += 1
    if emp == "civil_service" and gates.accept_exam_prep_months is not None:
        if gates.accept_exam_prep_months < 6:
            costs.append("备考窗口 <6 个月，公务员路径试错成本高")
            penalty += 1
    if gates.accept_non_research_roles is False and emp == "civil_service":
        costs.append("用户不接受非研究/行政综合岗")
        penalty += 1

    if penalty >= 2:
        return _composite_downgrade(composite)
    if penalty == 1:
        return _composite_downgrade(composite) if composite in ("A", "B") else composite
    return composite


def _composite_downgrade(composite: str) -> str:
    order = ["A", "B", "C", "D", "E", "F"]
    try:
        i = order.index(composite.upper())
    except ValueError:
        return composite
    return order[min(i + 1, len(order) - 1)]


def _build_matrix_cell(
    capability_id: str,
    employer_id: str,
    role_family: TaxonomyRoleFamily,
    scored: dict,
    match_score: float,
    graph: IndustryGraph,
    signals: dict[str, list[Signal]],
    constraints: Constraints,
    profile: Profile,
    eligibility_result,
) -> MatrixCell:
    node = graph.find_node(
        role_family.industry_id,
        role_family.subsector_id,
        role_family.value_chain_node_id,
    )
    trap = node.trap if node else ""
    node_name = node.name if node else role_family.value_chain_node_id
    industry_name = graph.industry_name(role_family.industry_id)
    shallow = _is_shallow_node(trap, role_family)

    if shallow:
        match_score = max(0.0, match_score - 0.15)

    comp_label = estimate_competition_index(role_family, signals)
    comp_float = competition_label_to_float(comp_label)
    fit = _level_label(match_score)
    wind, wind_rationale = _wind_from_signals(industry_name, signals)
    risk = "低" if constraints.reversibility_bias == "high" else "高"
    costs: list[str] = []
    composite = _composite_from_scores(
        match_score + _employer_composite_boost(employer_id, constraints),
        fit, wind, risk, comp_label, shallow,
    )
    composite = _apply_public_sector_gates(role_family, constraints, composite, costs)

    if shallow and trap:
        costs.append(f"浅层陷阱: {trap}")
    if comp_label == "high":
        costs.append("竞争密度偏高，需差异化叙事")
    if role_family.hard_gates:
        costs.append(f"硬门槛: {', '.join(role_family.hard_gates[:3])}")

    skill_transfer, st_rationale = _skill_transfer_for_role(role_family, match_score)
    if skill_transfer == "低" and composite in ("A", "B"):
        composite = _composite_downgrade(composite)

    # Schema 2.3 资格闸门 —— 在 composite 所有 domain-fit 调整之后封顶
    elig_status = eligibility_result.status
    composite = apply_composite_cap(composite, eligibility_result.composite_cap)
    if elig_status != "pass":
        costs.append(
            f"资格关[{elig_status}]: {eligibility_result.rationale}"
            + (f"（规则: {', '.join(eligibility_result.rules_matched)}）"
               if eligibility_result.rules_matched else "")
        )

    role_snap = RoleFamily(
        role=role_family.role,
        seniority=role_family.typical_seniority,
        match_score=match_score,
        competition_index=comp_float,
    )

    return MatrixCell(
        capability_id=capability_id,
        employer_id=employer_id,
        fit=fit,
        fit_rationale=(
            f"技能覆盖 {match_score:.0%}；岗位: {role_family.role}；"
            f"价值链: {node.value_is_in if node else '—'}"
        ),
        match=fit,
        match_rationale="Ikigai+期权 heuristic：core/adjacent 与岗位 required_skills 对齐度",
        wind=wind,
        wind_rationale=wind_rationale,
        risk=risk,
        risk_rationale="结合 constraints.reversibility_bias 默认",
        composite=composite,
        opens_up=[f"{industry_name} · {node_name} · {employer_id}"],
        costs=costs,
        first_step=(
            f"针对 {role_family.role}（{employer_id}）: "
            + (scored["skill_gaps"][0].skill if scored["skill_gaps"] else role_family.entry_mechanism or "调研入口")
        ),
        role_families=[role_snap],
        skill_gaps=scored["skill_gaps"],
        competition_index=comp_float,
        entry_mechanism=role_family.entry_mechanism,
        hard_gates=list(role_family.hard_gates),
        skill_transfer=skill_transfer,
        skill_transfer_rationale=st_rationale,
        # Schema 2.3 资格闸门字段
        eligibility=elig_status,
        eligibility_rationale=eligibility_result.rationale,
        domain_fit=fit,
        hiring_fit=eligibility_result.hiring_fit,
        blocked=eligibility_result.blocked,
        institution_tier=role_family.institution_tier,
        employer_subtype=role_family.employer_subtype,
        eligibility_rules=list(eligibility_result.rules_matched),
    )


def generate_orthogonal_matrix(
    profile: Profile,
    constraints: Constraints,
    graph: IndustryGraph,
    roles: RoleTaxonomy,
    employer_types: EmployerTypesFile,
    signals: dict[str, list[Signal]],
    projects: ProjectsFile | None = None,
    *,
    min_capabilities: int = 4,
    max_capabilities: int = 7,
    eligibility_rules_path: Path | None = None,
) -> OpportunityMatrix:
    """生成 Schema 2.2 正交机会矩阵：capability_axes × employer_axes → cross_matrix。

    Schema 2.3：每个候选 role_family 先过资格闸门（EligibilityGate）；fail 的 cell
    在 strong_preference 时被剔除，否则保留但 blocked=True 且 composite 封顶 D。
    """
    from .eligibility import load_eligibility_rules

    allowed_employers = constraints.allowed_employer_ids()
    emp_map = employer_types.by_id()

    # 资格规则加载（缺失则放行）
    rules = None
    rules_path = eligibility_rules_path
    if rules_path is None:
        # 默认从 data 目录找；调用方可显式传入
        default_data = Path.cwd() / "data" / _ELIGIBILITY_RULES_FILENAME
        if default_data.exists():
            rules_path = default_data
    if rules_path and rules_path.exists():
        rules = load_eligibility_rules(rules_path).rules

    strong_pref = constraints.employer_preference.strong_preference

    # (capability_id, employer_type_id) -> (match_score, role_family, scored, eligibility_result)
    best: dict[tuple[str, str], tuple[float, TaxonomyRoleFamily, dict, object]] = {}

    for rf in roles.role_families:
        if not passes_employer_scope(rf, constraints):
            continue
        cap_id = capability_id_for_role(rf)
        emp_id = rf.employer_type_id
        scored = score_profile_vs_role(profile, projects, rf)
        match_score = scored["match_score"]
        if not passes_constraints(rf, constraints, match_score):
            continue

        # 资格闸门 —— 在 composite 之前判定
        elig = evaluate_eligibility(
            rf, profile, constraints,
            typical_companies=rf.typical_companies.get("A", []),
            rules=rules,
        )
        # strong_preference 时，资格关 fail 直接剔除（不进矩阵）
        if strong_pref and elig.blocked:
            continue

        key = (cap_id, emp_id)
        prev = best.get(key)
        # 同 (cap, emp) 多 role 时取分高；并列时取资格更严者（让门槛显形）
        if prev is None or match_score > prev[0]:
            best[key] = (match_score, rf, scored, elig)
        elif match_score == prev[0]:
            # 并列：若新 role 资格更严（fail>review>pass），优先取新 role 让门槛可见
            _rank = {"pass": 0, "review": 1, "fail": 2}
            if _rank[elig.status] > _rank[prev[3].status]:
                best[key] = (match_score, rf, scored, elig)

    # 能力轴：按该能力下最佳 match 排序
    cap_scores: dict[str, float] = {}
    for (cap_id, _), (ms, _, _, _) in best.items():
        cap_scores[cap_id] = max(cap_scores.get(cap_id, 0.0), ms)
    ranked_caps = sorted(cap_scores.keys(), key=lambda c: -cap_scores[c])[:max_capabilities]
    if len(ranked_caps) < min_capabilities:
        ranked_caps = sorted(cap_scores.keys(), key=lambda c: -cap_scores[c])

    capability_axes: list[CapabilityAxis] = []
    for cap_id in ranked_caps:
        sample = next(rf for (c, _), (_, rf, _, _) in best.items() if c == cap_id)
        node = graph.find_node(sample.industry_id, sample.subsector_id, sample.value_chain_node_id)
        capability_axes.append(CapabilityAxis(
            id=cap_id,
            name=capability_label(cap_id, sample.role),
            summary=node.value_is_in if node else "",
            industry=graph.industry_name(sample.industry_id),
            value_chain_node=node.name if node else sample.value_chain_node_id,
        ))

    employer_axes: list[EmployerAxis] = [
        EmployerAxis(
            id=e.id,
            name=e.name,
            stability=e.stability,
            ceiling=e.ceiling,
            value_is_in=e.value_is_in,
            trap=e.trap,
            entry_paths=list(e.entry_paths),
            typical_orgs=list(e.typical_orgs),
        )
        for e in employer_types.employer_types
        if e.id in allowed_employers
    ]
    if constraints.employer_preference.priority:
        pri = {eid: i for i, eid in enumerate(constraints.employer_preference.priority)}
        employer_axes.sort(key=lambda ax: pri.get(ax.id, 99))

    # 每个雇主轴至少保留一个能力行（避免公务员/事业编列全空）
    for emp_ax in employer_axes:
        emp_entries = [
            (ms, capability_id_for_role(rf))
            for (cap, emp), (ms, rf, _, _) in best.items()
            if emp == emp_ax.id
        ]
        if not emp_entries:
            continue
        emp_entries.sort(key=lambda x: -x[0])
        ms_best, cap_id = emp_entries[0]
        if cap_id not in ranked_caps:
            ranked_caps.append(cap_id)
            rf = next(
                rf for (c, emp), (_, rf, _, _) in best.items()
                if emp == emp_ax.id and c == cap_id
            )
            node = graph.find_node(rf.industry_id, rf.subsector_id, rf.value_chain_node_id)
            capability_axes.append(CapabilityAxis(
                id=cap_id,
                name=capability_label(cap_id, rf.role),
                summary=node.value_is_in if node else "",
                industry=graph.industry_name(rf.industry_id),
                value_chain_node=node.name if node else rf.value_chain_node_id,
            ))

    cross_matrix: list[MatrixCell] = []
    for cap_id in ranked_caps:
        for emp_ax in employer_axes:
            key = (cap_id, emp_ax.id)
            entry = best.get(key)
            if not entry:
                continue
            ms, rf, scored, elig = entry
            cross_matrix.append(_build_matrix_cell(
                cap_id, emp_ax.id, rf, scored, ms, graph, signals, constraints,
                profile, elig,
            ))

    matrix = OpportunityMatrix(
        generated_on=date.today(),
        capability_axes=capability_axes,
        employer_axes=employer_axes,
        cross_matrix=cross_matrix,
        primary=[],  # 由 synthesized_primary() 按需生成（跳过 blocked）
    )
    return matrix
