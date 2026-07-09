"""Schema 2.2 正交矩阵测试。"""
from datetime import date
from pathlib import Path

import pytest

from career_compass.match import (
    capability_id_for_role,
    generate_orthogonal_matrix,
    passes_employer_scope,
)
from career_compass.render import render_opportunities
from career_compass.schema import (
    Constraints,
    EmployerPreference,
    MatrixCell,
    OpportunityMatrix,
    Profile,
    load_employer_types,
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
def employer_types():
    return load_employer_types(REPO_DATA / "employer_types.yaml")


@pytest.fixture
def example_profile(examples_dir: Path):
    return load_profile(examples_dir / "profile.yaml")


def test_role_taxonomy_merges_public(taxonomy):
    ids = {r.id for r in taxonomy.role_families}
    assert "or_engineer_central_soe" in ids
    assert "civil_service_transport" in ids


def test_capability_id_for_role(taxonomy):
    rf = next(r for r in taxonomy.role_families if r.id == "or_engineer_central_soe")
    assert capability_id_for_role(rf) == "sc_optimization"
    assert rf.employer_type_id == "central_soe"


def test_passes_employer_scope_strong_preference():
    from career_compass.schema import TaxonomyRoleFamily

    rf = TaxonomyRoleFamily(
        id="x", industry_id="a", subsector_id="b", value_chain_node_id="c",
        role="test", employer_type_id="civil_service",
    )
    c = Constraints(
        employer_preference=EmployerPreference(
            include=["private"],
            strong_preference=True,
        ),
    )
    assert passes_employer_scope(rf, c) is False


def test_generate_orthogonal_matrix_shape(example_profile, graph, taxonomy, employer_types):
    matrix = generate_orthogonal_matrix(
        example_profile, Constraints(), graph, taxonomy, employer_types, {},
    )
    assert matrix.uses_orthogonal_matrix()
    assert len(matrix.capability_axes) >= 3
    assert len(matrix.employer_axes) >= 4
    assert len(matrix.cross_matrix) >= 6
    employer_ids = {c.employer_id for c in matrix.cross_matrix}
    assert "central_soe" in employer_ids or "public_institution" in employer_ids


def test_strong_preference_narrows_employer_columns(
    example_profile, graph, taxonomy, employer_types,
):
    constraints = Constraints(
        employer_preference=EmployerPreference(
            include=["private", "central_soe"],
            strong_preference=True,
        ),
    )
    matrix = generate_orthogonal_matrix(
        example_profile, constraints, graph, taxonomy, employer_types, {},
    )
    assert {e.id for e in matrix.employer_axes} <= {"private", "central_soe"}


def test_synthesized_primary_from_cross_matrix(example_profile, graph, taxonomy, employer_types):
    matrix = generate_orthogonal_matrix(
        example_profile, Constraints(), graph, taxonomy, employer_types, {},
    )
    primary = matrix.ranked_primary()
    assert primary
    assert "（" in primary[0].direction  # "能力（雇主）" 合成标签


def test_render_orthogonal_matrix(tmp_path, example_profile, graph, taxonomy, employer_types):
    matrix = generate_orthogonal_matrix(
        example_profile, Constraints(), graph, taxonomy, employer_types, {},
    )
    path = tmp_path / "opportunities.yaml"
    from career_compass.schema import save_opportunities
    save_opportunities(path, matrix)
    out = render_opportunities(path)
    assert "机会矩阵" in out
    assert "主业" in out
    assert "正交矩阵" not in out
    assert "能力轴" not in out
    assert "雇主性质轴" not in out


def test_legacy_primary_still_renders(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "机会矩阵" in out
    assert "LLM 应用工程师" in out
