from pathlib import Path

from career_compass.schema import (
    Education,
    EducationLevel,
    EducationStatus,
    Profile,
    is_placeholder,
    infer_education_level,
    load_constraints,
    load_profile,
    validate_constraints,
    validate_narrative,
    validate_profile_text_fields,
)
from datetime import date


def test_is_placeholder():
    assert is_placeholder("(待填)")
    assert is_placeholder("TBD soon")
    assert is_placeholder("")
    assert not is_placeholder("Python / SQL")


def test_profile_gaps_rejects_placeholder_proof(examples_dir: Path):
    profile = load_profile(examples_dir / "profile.yaml")
    assert profile.gaps() == []


def test_profile_gaps_detects_missing_core():
    profile = Profile()
    gaps = profile.gaps()
    assert any("skills.core" in g for g in gaps)


def test_profile_gaps_detects_placeholder_strength():
    profile = Profile(
        skills={"core": ["Python"]},
        strength_evidence=[{"claim": "擅长 X", "proof": "tbd"}],
        preferences={"values_ranked": ["learning"]},
        experience=[{"company": "Co", "role": "R", "period": "2020", "scope": "s"}],
    )
    gaps = profile.gaps()
    assert any("strength_evidence" in g for g in gaps)


def test_validate_constraints_warns_empty_geo():
    from career_compass.schema import Constraints

    result = validate_constraints(Constraints())
    assert any("geo" in w.message for w in result.warnings)


def test_validate_constraints_ok(examples_dir: Path):
    c = load_constraints(examples_dir / "constraints.yaml")
    result = validate_constraints(c)
    assert not any("geo" in w.message and "空" in w.message for w in result.warnings)


def test_validate_narrative_sections(examples_dir: Path):
    text = (examples_dir / "narrative.md").read_text(encoding="utf-8")
    result = validate_narrative(text)
    assert result.ok


def test_validate_narrative_warns_placeholder():
    text = "# N\n\n## 职业故事\n\n（待填）\n\n## 我想要的\n\nok\n\n## 红线\n\nok"
    result = validate_narrative(text)
    assert any("职业故事" in w.message for w in result.warnings)


def test_infer_education_level():
    assert infer_education_level("博士在读") == EducationLevel.phd
    assert infer_education_level("工学硕士") == EducationLevel.master
    assert infer_education_level("本科") == EducationLevel.bachelor


def test_education_normalizes_year_and_status():
    edu = Education(degree="博士在读", major="OR", school="某大学", year=2028)
    assert edu.end_year == 2028
    assert edu.status == EducationStatus.enrolled
    assert edu.resolved_level() == EducationLevel.phd


def test_profile_gaps_requires_bachelor_details():
    profile = Profile(
        education=[
            Education(level=EducationLevel.bachelor, major="(待填)", school="二本"),
        ],
        skills={"core": ["Python"]},
        strength_evidence=[{"claim": "X", "proof": "做了 Y"}],
        preferences={"values_ranked": ["learning"]},
    )
    gaps = profile.gaps()
    assert any("school 请填院校全名" in g for g in gaps)
    assert any("major" in g for g in gaps)


def test_validate_profile_warns_tier_only_school():
    profile = Profile(
        education=[Education(level=EducationLevel.master, major="CS", school="211")],
    )
    result = validate_profile_text_fields(profile)
    assert any("院校全名" in w.message for w in result.warnings)


def test_opportunity_matrix_migrates_legacy_directions():
    from career_compass.schema import Opportunity, OpportunityMatrix

    matrix = OpportunityMatrix(
        generated_on=date.today(),
        directions=[
            Opportunity(
                direction="测试方向",
                fit="高", fit_rationale="x", match="高", match_rationale="x",
                wind="顺风", wind_rationale="x", risk="可逆", risk_rationale="x",
                composite="A",
            ),
        ],
    )
    assert len(matrix.primary) == 1
    assert matrix.primary[0].direction == "测试方向"
    assert matrix.primary[0].risk == "低"  # legacy 可逆 → 低
