"""Phase 3 — track / replan / jd-analyze 测试。"""
from datetime import date
from pathlib import Path

import pytest

from career_compass.jd_analyze import analyze_jd_file, analyze_jd_text
from career_compass.replan import analyze_replan, apply_replan_suggestions
from career_compass.schema import (
    Application,
    ApplicationStatus,
    ApplicationTier,
    ApplicationsFile,
    Opportunity,
    OpportunityMatrix,
    load_opportunities,
    load_profile,
    save_applications,
)
from career_compass.track import add_application, funnel_stats, update_application


def test_track_add_and_funnel(tmp_path: Path):
    apps_path = tmp_path / "applications.yaml"
    app = add_application(apps_path, "TestCo", "MLE", tier=ApplicationTier.A, channel="内推")
    assert app.id
    assert apps_path.exists()

    stats = funnel_stats(apps_path)
    assert stats["total"] == 1

    update_application(apps_path, app.id, status=ApplicationStatus.rejected, feedback="缺 CUDA")
    stats2 = funnel_stats(apps_path)
    assert stats2["rejected_count"] == 1
    assert "缺 CUDA" in stats2["feedback_keywords"][0]


def test_replan_suggestions(tmp_path: Path, examples_dir: Path):
    apps_path = tmp_path / "applications.yaml"
    data = ApplicationsFile(
        updated_on=date.today(),
        applications=[
            Application(
                id="x1",
                company="A",
                role="R",
                direction="LLM 应用工程师",
                tier=ApplicationTier.A,
                applied_on=date.today(),
                status=ApplicationStatus.ghosted,
            ),
            Application(
                id="x2",
                company="B",
                role="R",
                direction="LLM 应用工程师",
                tier=ApplicationTier.A,
                applied_on=date.today(),
                status=ApplicationStatus.ghosted,
            ),
            Application(
                id="x3",
                company="C",
                role="R",
                direction="LLM 应用工程师",
                tier=ApplicationTier.A,
                applied_on=date.today(),
                status=ApplicationStatus.ghosted,
            ),
        ],
    )
    save_applications(apps_path, data)

    opps_path = examples_dir / "opportunities.yaml"
    report = analyze_replan(apps_path, opps_path)
    assert any(s.kind == "tripwire" for s in report.suggestions)


def test_apply_replan_downgrade():
    matrix = OpportunityMatrix(
        generated_on=date.today(),
        directions=[
            Opportunity(
                direction="LLM 应用工程师",
                fit="高", fit_rationale="x", match="高", match_rationale="x",
                wind="顺风", wind_rationale="x", risk="可逆", risk_rationale="x",
                composite="A",
            ),
        ],
    )
    from career_compass.replan import ReplanSuggestion

    revised = apply_replan_suggestions(matrix, [
        ReplanSuggestion(
            kind="downgrade_direction",
            target="LLM 应用工程师",
            reason="test",
        ),
    ])
    assert revised.directions[0].composite == "B"


def test_jd_analyze(examples_dir: Path):
    profile = load_profile(examples_dir / "profile.yaml")
    jd_path = examples_dir / "sample_jd.txt"
    result = analyze_jd_file(jd_path, profile)
    assert result.top_skills
    assert 0 <= result.coverage_rate <= 1


def test_jd_analyze_inline(examples_dir: Path):
    profile = load_profile(examples_dir / "profile.yaml")
    text = "需要 Python LLM RAG Kubernetes 向量数据库"
    result = analyze_jd_text(text, profile)
    assert any("Python" in s or "LLM" in s for s in result.top_skills)
