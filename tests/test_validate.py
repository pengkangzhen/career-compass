from pathlib import Path

from career_compass.schema import (
    Profile,
    is_placeholder,
    load_constraints,
    load_profile,
    validate_constraints,
    validate_narrative,
)


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
