"""Schema 2.3 资格闸门（EligibilityGate）测试。"""
from datetime import date
from pathlib import Path

import pytest

from career_compass.eligibility import (
    EligibilityResult,
    apply_composite_cap,
    evaluate_eligibility,
    load_eligibility_rules,
)
from career_compass.match import generate_orthogonal_matrix
from career_compass.pipeline import validate_eligibility, validate_eligibility_with_profile
from career_compass.schema import (
    Constraints,
    Education,
    EducationLevel,
    EducationStatus,
    EmployerPreference,
    MatrixCell,
    OpportunityMatrix,
    Profile,
    TaxonomyRoleFamily,
    derive_education_summary,
    load_employer_types,
    load_industry_graph,
    load_profile,
    load_role_taxonomy,
)

REPO_DATA = Path(__file__).resolve().parent.parent / "data"
RULES_PATH = REPO_DATA / "hiring_eligibility_rules.yaml"


@pytest.fixture
def rules():
    return load_eligibility_rules(RULES_PATH).rules


# ---------- 画像工厂 ----------


def _profile_211_phd_enrolled() -> Profile:
    """二本本 + 211 硕博在读（彭康振 canonical case）。"""
    return Profile(
        name="测试",
        education=[
            Education(level=EducationLevel.bachelor, degree="学士",
                      school="山东交通学院", school_tier="二本",
                      major="物联网工程", end_year=2020, status=EducationStatus.graduated),
            Education(level=EducationLevel.master, degree="硕士",
                      school="大连海事大学", school_tier="211",
                      major="交通运输", end_year=2023, status=EducationStatus.graduated),
            Education(level=EducationLevel.phd, degree="博士在读",
                      school="大连海事大学", school_tier="211",
                      major="物流工程与管理", end_year=2028, status=EducationStatus.enrolled),
        ],
        skills={"core": ["Python", "运筹优化"]},
        strength_evidence=[{"claim": "擅长 X", "proof": "做了 Y"}],
        preferences={"values_ranked": ["research"]},
    )


def _profile_985_phd_in_hand() -> Profile:
    return Profile(
        name="测试",
        education=[
            Education(level=EducationLevel.bachelor, degree="学士",
                      school="某 985", school_tier="985",
                      major="CS", end_year=2018, status=EducationStatus.graduated),
            Education(level=EducationLevel.phd, degree="博士",
                      school="某 985", school_tier="985",
                      major="OR", end_year=2024, status=EducationStatus.graduated),
        ],
        skills={"core": ["Python"]},
        strength_evidence=[{"claim": "擅长 X", "proof": "Y"}],
        preferences={"values_ranked": ["research"]},
    )


# ---------- role 工厂 ----------


def _faculty_211_role() -> TaxonomyRoleFamily:
    return TaxonomyRoleFamily(
        id="academia_faculty_211",
        industry_id="or_supply_chain", subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="高校物流 / 交通教职（211 研究型）",
        employer_type_id="public_institution",
        employer_subtype="university_faculty",
        institution_tier="211",
        required_skills=["运筹优化", "Python"],
        typical_companies={"A": ["大连海事大学", "上海海事大学"]},
    )


def _faculty_general_role() -> TaxonomyRoleFamily:
    return TaxonomyRoleFamily(
        id="academia_faculty_general",
        industry_id="or_supply_chain", subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="普通本科高校物流 / 交通教职",
        employer_type_id="public_institution",
        employer_subtype="university_faculty",
        institution_tier="普通本科",
        required_skills=["运筹优化", "Python"],
        typical_companies={"A": ["山东交通学院"]},
    )


def _civil_service_role() -> TaxonomyRoleFamily:
    return TaxonomyRoleFamily(
        id="civil_service_transport",
        industry_id="or_supply_chain", subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="交通类公务员",
        employer_type_id="civil_service",
        employer_subtype="civil_service_admin",
        required_skills=["行测"],
        typical_companies={"A": ["交通运输部"]},
    )


def _head_research_role() -> TaxonomyRoleFamily:
    return TaxonomyRoleFamily(
        id="ai_lab_research",
        industry_id="ai_llm", subsector_id="llm_infra",
        value_chain_node_id="pretrain_finetune",
        role="AI Lab research scientist",
        employer_type_id="private",
        employer_subtype="private_tech",
        institution_tier="985",
        required_skills=["Python"],
        typical_companies={"A": ["字节 AI Lab"]},
    )


# ---------- tests ----------


def test_derive_education_summary_second_bachelor_211_phd_enrolled():
    s = derive_education_summary(_profile_211_phd_enrolled())
    assert s.first_degree_tier == "二本"
    assert s.highest_degree_tier == "211"
    assert s.highest_degree_school == "大连海事大学"
    assert s.phd_status == "enrolled"
    assert "二本本" in s.pedigree_pattern and "211博" in s.pedigree_pattern


def test_faculty_211_blocks_second_bachelor(rules):
    p = _profile_211_phd_enrolled()
    c = Constraints()
    r = evaluate_eligibility(_faculty_211_role(), p, c,
                             typical_companies=["大连海事大学"], rules=rules)
    assert r.status == "fail"
    assert r.blocked is True
    assert r.composite_cap == "D"
    assert "faculty_211_first_degree" in r.rules_matched


def test_faculty_general_passes_second_bachelor(rules):
    p = _profile_211_phd_enrolled()
    r = evaluate_eligibility(_faculty_general_role(), p, Constraints(),
                             typical_companies=["山东交通学院"], rules=rules)
    # 普通本科教职：第一学历规则 pass；phd_in_hand 仍 review（在读）
    assert r.status == "review"
    assert r.blocked is False
    assert "phd_in_hand_required" in r.rules_matched
    assert "faculty_211_first_degree" not in r.rules_matched


def test_faculty_985_passes_985_bachelor(rules):
    p = _profile_985_phd_in_hand()
    role = TaxonomyRoleFamily(
        id="x", industry_id="a", subsector_id="b", value_chain_node_id="c",
        role="985 教职", employer_type_id="public_institution",
        employer_subtype="university_faculty", institution_tier="985",
        required_skills=["Python"], typical_companies={"A": ["某 985"]},
    )
    # typical_companies 用与博士校不同的学校，避免 same_institution 触发
    r = evaluate_eligibility(role, p, Constraints(),
                             typical_companies=["另一所 985"], rules=rules)
    assert r.status == "pass"


def test_phd_in_hand_required_enrolled_review(rules):
    p = _profile_211_phd_enrolled()
    # 普通本科教职，博士在读 → phd_in_hand 触发 review
    r = evaluate_eligibility(_faculty_general_role(), p, Constraints(),
                             typical_companies=["山东交通学院"], rules=rules)
    assert r.status == "review"
    assert r.composite_cap == "B"


def test_same_institution_avoidance_review(rules):
    p = _profile_211_phd_enrolled()  # 博士校 = 大连海事大学
    # 用 985 第一学历画像避免被 faculty_211 拦，单独验证 same_institution
    p985 = Profile(
        education=[
            Education(level=EducationLevel.bachelor, degree="学士",
                      school="某 985", school_tier="985", major="CS",
                      end_year=2018, status=EducationStatus.graduated),
            Education(level=EducationLevel.phd, degree="博士",
                      school="大连海事大学", school_tier="211", major="OR",
                      end_year=2024, status=EducationStatus.graduated),
        ],
        skills={"core": ["Python"]},
        strength_evidence=[{"claim": "X", "proof": "Y"}],
        preferences={"values_ranked": ["research"]},
    )
    r = evaluate_eligibility(_faculty_211_role(), p985, Constraints(),
                             typical_companies=["大连海事大学"], rules=rules)
    # 985 本 → faculty_211 第一学历 pass；同校 → review
    assert "same_institution_avoidance" in r.rules_matched
    assert r.status == "review"


def test_civil_service_age_35_fails(rules):
    p = _profile_985_phd_in_hand()
    c = Constraints(age=36)
    r = evaluate_eligibility(_civil_service_role(), p, c,
                             typical_companies=["交通运输部"], rules=rules)
    assert r.status == "fail"
    assert r.blocked is True
    assert r.composite_cap == "D"
    assert "civil_service_age_35" in r.rules_matched


def test_civil_service_age_under_35_passes(rules):
    p = _profile_985_phd_in_hand()
    c = Constraints(age=30)
    r = evaluate_eligibility(_civil_service_role(), p, c,
                             typical_companies=["交通运输部"], rules=rules)
    assert r.status == "pass"


def test_head_research_second_bachelor_review_not_fail(rules):
    p = _profile_211_phd_enrolled()
    r = evaluate_eligibility(_head_research_role(), p, Constraints(),
                             typical_companies=["字节 AI Lab"], rules=rules)
    # 二本本 + 头部 AI Lab research → review（不 hard fail），cap B
    assert r.status == "review"
    assert r.blocked is False
    assert r.composite_cap == "B"
    assert "first_degree_barrier_head_research" in r.rules_matched


def test_apply_composite_cap():
    assert apply_composite_cap("A", "D") == "D"
    assert apply_composite_cap("B", "B") == "B"
    assert apply_composite_cap("C", None) == "C"
    assert apply_composite_cap("D", "B") == "D"  # 已劣于 cap 不动


# ---------- matrix 级集成 ----------


def test_matrix_211_faculty_capped_at_d_and_blocked():
    """彭康振 canonical case：211 教职格 composite 被 cap 到 D 且 blocked。"""
    p = _profile_211_phd_enrolled()
    graph = load_industry_graph(REPO_DATA / "industry_graph.yaml")
    tax = load_role_taxonomy(REPO_DATA / "role_taxonomy.yaml")
    et = load_employer_types(REPO_DATA / "employer_types.yaml")
    matrix = generate_orthogonal_matrix(
        p, Constraints(), graph, tax, et, {},
        eligibility_rules_path=RULES_PATH,
    )
    faculty_cells = [c for c in matrix.cross_matrix
                     if c.employer_subtype == "university_faculty"
                     and c.institution_tier == "211"]
    assert faculty_cells, "应有 211 教职格 cell"
    cell = faculty_cells[0]
    assert cell.eligibility == "fail"
    assert cell.blocked is True
    assert cell.composite == "D"
    assert cell.hiring_fit == "低"


def test_matrix_blocked_cell_excluded_from_ranked_primary():
    p = _profile_211_phd_enrolled()
    graph = load_industry_graph(REPO_DATA / "industry_graph.yaml")
    tax = load_role_taxonomy(REPO_DATA / "role_taxonomy.yaml")
    et = load_employer_types(REPO_DATA / "employer_types.yaml")
    matrix = generate_orthogonal_matrix(
        p, Constraints(), graph, tax, et, {},
        eligibility_rules_path=RULES_PATH,
    )
    blocked_ids = {c.capability_id for c in matrix.blocked_cells()}
    for o in matrix.ranked_primary():
        assert not any(c in o.direction for c in blocked_ids) or not o.blocked
    # ranked_primary 不得含 blocked opportunity
    assert all(not o.blocked for o in matrix.ranked_primary())


def test_validate_eligibility_fail_with_high_composite_errors():
    """构造一个 fail 但 composite=A 的 cell → validate 报 ERROR。"""
    cell = MatrixCell(
        capability_id="academia_research", employer_id="public_institution",
        fit="高", fit_rationale="x", match="高", match_rationale="x",
        wind="顺风", wind_rationale="x", risk="低", risk_rationale="x",
        composite="A",
        eligibility="fail",
        eligibility_rationale="第一学历门槛",
        blocked=False,  # 不一致，但 validate 看 composite
        institution_tier="211", employer_subtype="university_faculty",
    )
    matrix = OpportunityMatrix(generated_on=date.today(), cross_matrix=[cell])
    result = validate_eligibility(matrix)
    assert any("应 ≤D" in e.message for e in result.errors)


def test_validate_eligibility_with_profile_211_faculty_pass_errors():
    """211 教职格 eligibility=pass 但画像二本 → ERROR。"""
    cell = MatrixCell(
        capability_id="academia_research", employer_id="public_institution",
        fit="高", fit_rationale="x", match="高", match_rationale="x",
        wind="顺风", wind_rationale="x", risk="低", risk_rationale="x",
        composite="A",
        eligibility="pass",  # 错误通过
        institution_tier="211", employer_subtype="university_faculty",
    )
    matrix = OpportunityMatrix(generated_on=date.today(), cross_matrix=[cell])
    result = validate_eligibility_with_profile(matrix, _profile_211_phd_enrolled())
    assert any("211/985 教职格" in e.message for e in result.errors)


def test_strong_preference_drops_blocked_cell():
    """strong_preference=True 时，blocked cell 被完全剔除（不进矩阵）。"""
    p = _profile_211_phd_enrolled()
    graph = load_industry_graph(REPO_DATA / "industry_graph.yaml")
    tax = load_role_taxonomy(REPO_DATA / "role_taxonomy.yaml")
    et = load_employer_types(REPO_DATA / "employer_types.yaml")
    c = Constraints(
        employer_preference=EmployerPreference(
            include=["public_institution"], strong_preference=True,
        ),
    )
    matrix = generate_orthogonal_matrix(
        p, c, graph, tax, et, {},
        eligibility_rules_path=RULES_PATH,
    )
    # 211 教职格被 blocked → strong_preference 下整列剔除，不应出现 211 university_faculty cell
    faculty_211 = [cell for cell in matrix.cross_matrix
                   if cell.employer_subtype == "university_faculty"
                   and cell.institution_tier == "211"]
    assert faculty_211 == []
