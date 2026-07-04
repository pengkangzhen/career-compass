from datetime import date
from pathlib import Path

import pytest

from career_compass.match import (
    collect_profile_skills,
    competition_label_to_float,
    estimate_competition_index,
    generate_candidate_opportunities,
    passes_constraints,
    score_profile_vs_role,
)
from career_compass.schema import (
    Constraints,
    Profile,
    ProjectsFile,
    ProjectEvidence,
    RiskAppetite,
    RoleTaxonomy,
    Signal,
    TaxonomyRoleFamily,
    load_industry_graph,
    load_profile,
    load_role_taxonomy,
)

REPO_DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def graph():
    return load_industry_graph(REPO_DATA / "industry_graph.yaml")


@pytest.fixture
def taxonomy():
    return load_role_taxonomy(REPO_DATA / "role_taxonomy.yaml")


@pytest.fixture
def example_profile(examples_dir: Path):
    return load_profile(examples_dir / "profile.yaml")


def test_score_profile_vs_role_high_match(example_profile, taxonomy):
    role = next(r for r in taxonomy.role_families if r.id == "llm_app_engineer")
    result = score_profile_vs_role(example_profile, None, role)
    assert result["match_score"] >= 0.5
    assert isinstance(result["skill_gaps"], list)


def test_score_profile_vs_role_with_projects(example_profile, taxonomy):
    role = next(r for r in taxonomy.role_families if r.id == "llm_app_engineer")
    projects = ProjectsFile(
        scanned_on=date.today(),
        projects=[
            ProjectEvidence(
                path="/tmp/x",
                name="demo",
                inferred_signals=["RAG", "LangChain"],
            ),
        ],
    )
    buckets = collect_profile_skills(example_profile, projects)
    assert "rag" in buckets["all"] or any("rag" in t for t in buckets["all"])
    result = score_profile_vs_role(example_profile, projects, role)
    assert result["match_score"] >= 0.5


def test_estimate_competition_index_high():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="ai_llm",
        subsector_id="llm_apps",
        value_chain_node_id="rag_agent",
        role="LLM 应用工程师",
        required_skills=["Python"],
    )
    signals = {
        "market": [
            Signal(
                topic="AI 应用",
                finding="供给过剩、内卷严重，纯 wrapper 岗位饱和",
                source="test",
                retrieved_on=date.today(),
            ),
        ],
    }
    assert estimate_competition_index(role, signals) == "high"


def test_estimate_competition_index_low():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="or_supply_chain",
        subsector_id="supply_chain_planning",
        value_chain_node_id="network_optimization",
        role="供应链优化工程师",
        required_skills=["MIP"],
    )
    signals = {
        "market": [
            Signal(
                topic="OR 人才",
                finding="优化算法人才短缺，需求增长快",
                source="test",
                retrieved_on=date.today(),
            ),
        ],
    }
    assert estimate_competition_index(role, signals) == "low"


def test_competition_label_to_float():
    assert competition_label_to_float("low") < competition_label_to_float("high")


def test_passes_constraints_low_risk_filters_low_match():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="ai_llm",
        subsector_id="llm_apps",
        value_chain_node_id="rag_agent",
        role="LLM 应用工程师",
        typical_seniority="1-3年",
        required_skills=["Python"],
    )
    constraints = Constraints(risk_appetite=RiskAppetite.low)
    assert passes_constraints(role, constraints, 0.2) is False
    assert passes_constraints(role, constraints, 0.6) is True


def test_passes_constraints_short_runway_blocks_phd():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="biopharma",
        subsector_id="drug_discovery",
        value_chain_node_id="ai_drug_design",
        role="计算化学",
        typical_seniority="博士 / 博后",
        required_skills=["Python"],
    )
    constraints = Constraints(financial_runway_months=3)
    assert passes_constraints(role, constraints, 0.8) is False


def test_passes_constraints_geo_blocks_overseas():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="ai_llm",
        subsector_id="llm_apps",
        value_chain_node_id="rag_agent",
        role="海外博后（top lab）",
        typical_seniority="博后 2-3 年",
        required_skills=["Python"],
    )
    constraints = Constraints(geo=["上海", "北京"])
    assert passes_constraints(role, constraints, 0.8) is False


def test_passes_constraints_geo_allows_overseas_when_noted():
    role = TaxonomyRoleFamily(
        id="x",
        industry_id="ai_llm",
        subsector_id="llm_apps",
        value_chain_node_id="rag_agent",
        role="海外博后",
        typical_seniority="博后",
        required_skills=["Python"],
    )
    constraints = Constraints(geo=["上海", "海外可选"])
    assert passes_constraints(role, constraints, 0.8) is True


def test_generate_candidate_opportunities_count(example_profile, graph, taxonomy):
    constraints = Constraints(risk_appetite=RiskAppetite.medium)
    opps = generate_candidate_opportunities(
        example_profile,
        constraints,
        graph,
        taxonomy,
        signals={},
        projects=None,
        min_count=4,
        max_count=7,
    )
    assert 4 <= len(opps) <= 7
    first = opps[0]
    assert first.industry
    assert first.role_families
    assert first.composite in {"A", "B", "C", "D", "E", "F"}


def test_generate_opportunities_have_phase2_fields(example_profile, graph, taxonomy):
    constraints = Constraints()
    opps = generate_candidate_opportunities(
        example_profile, constraints, graph, taxonomy, {},
    )
    o = opps[0]
    assert o.value_chain_node
    assert o.skill_gaps is not None
    assert o.competition_index is not None
