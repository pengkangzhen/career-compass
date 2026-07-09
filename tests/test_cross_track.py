from pathlib import Path

from career_compass.cross_track import (
    assess_cross_track,
    cross_track_match_adjustment,
    is_or_method_role,
    or_method_strength,
    render_cross_track_section,
)
from career_compass.match import generate_orthogonal_matrix, score_profile_vs_role
from career_compass.schema import (
    Constraints,
    Profile,
    TaxonomyRoleFamily,
    load_constraints,
    load_employer_types,
    load_industry_graph,
    load_profile,
    load_role_taxonomy,
)


def _or_profile() -> Profile:
    return load_profile(Path(__file__).resolve().parent.parent / "data" / "profile.yaml")


def test_reinforcement_learning_does_not_match_molecular_modeling():
    profile = Profile.model_validate({
        "name": "t",
        "skills": {
            "core": ["运筹优化：启发式 / 元启发式 / 强化学习混合求解", "Python"],
            "adjacent": [],
            "frontier": [],
        },
        "strength_evidence": [],
        "preferences": {"energized_by": [], "drained_by": [], "values_ranked": []},
    })
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="biopharma",
        subsector_id="drug_discovery",
        value_chain_node_id="ai_drug_design",
        role="计算化学",
        required_skills=["分子建模", "Python", "机器学习"],
    )
    from career_compass.match import skill_match_level
    assert skill_match_level("分子建模", profile) is None
    scored = score_profile_vs_role(profile, None, role)
    assert scored["match_score"] < 0.5


def test_or_profile_detects_logistics_saturation():
    from career_compass.cross_track import resolve_market_saturation
    from career_compass.schema import load_industry_graph

    profile = _or_profile()
    graph = load_industry_graph(Path(__file__).resolve().parent.parent / "data" / "industry_graph.yaml")
    role = TaxonomyRoleFamily(
        id="sc",
        industry_id="or_supply_chain",
        subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="供应链优化工程师",
        required_skills=["运筹优化", "MIP", "Python"],
    )
    sat = resolve_market_saturation(
        role, graph, {},
        domain_anchor=1.0,
        raw_match_score=0.85,
        industry_name="运筹优化 / 供应链智能化",
    )
    assert sat.saturation == "high"
    assert "饱和" in sat.saturation_note


def test_saturation_not_shown_without_track_affinity():
    from career_compass.cross_track import resolve_market_saturation
    from career_compass.schema import load_industry_graph

    graph = load_industry_graph(Path(__file__).resolve().parent.parent / "data" / "industry_graph.yaml")
    role = TaxonomyRoleFamily(
        id="sc",
        industry_id="or_supply_chain",
        subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="供应链优化工程师",
        required_skills=["运筹优化", "MIP", "Python"],
    )
    sat = resolve_market_saturation(
        role, graph, {},
        domain_anchor=0.2,
        raw_match_score=0.3,
    )
    assert sat.saturation == ""


def test_semiconductor_or_is_cross_track_with_domain_gap():
    profile = _or_profile()
    role = TaxonomyRoleFamily(
        id="semi",
        industry_id="semicon",
        subsector_id="fab_manufacturing",
        value_chain_node_id="fab_scheduling",
        role="晶圆厂排程优化工程师",
        required_skills=["运筹优化", "MIP", "Python"],
        skill_transfer_default="高",
    )
    assert is_or_method_role(role)
    assert or_method_strength(profile) >= 0.75
    cross = assess_cross_track(profile, role, domain_anchor=0.35, raw_match_score=0.8)
    assert cross.is_cross_track
    assert cross.method_transfer == "高"
    assert cross.domain_gap == "高"
    adjusted = cross_track_match_adjustment(0.8, 0.35, cross)
    assert adjusted > 0.8 * 0.35  # 不应被行业锚点完全压死


def test_orthogonal_matrix_includes_semiconductor_for_or_profile():
    data = Path(__file__).resolve().parent.parent / "data"
    profile = load_profile(data / "profile.yaml")
    constraints = load_constraints(data / "constraints.yaml")
    graph = load_industry_graph(data / "industry_graph.yaml")
    roles = load_role_taxonomy(data / "role_taxonomy.yaml")
    employers = load_employer_types(data / "employer_types.yaml")
    matrix = generate_orthogonal_matrix(
        profile, constraints, graph, roles, employers, {},
    )
    cap_ids = {c.id for c in matrix.capability_axes}
    assert "semi_fab_or" in cap_ids or "semi_yield_or" in cap_ids

    section = render_cross_track_section(profile, matrix)
    assert "交叉赛道洞察" in section
    assert "半导体" in section
