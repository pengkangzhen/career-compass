"""M2 intake：缺口追问、进度、预览。"""
from __future__ import annotations

from pathlib import Path

from career_compass.intake.gaps import (
    compute_intake_progress,
    narrative_sections_ok,
    suggest_followups,
)
from career_compass.intake.preview import build_intake_status
from career_compass.intake.writer import bootstrap_data_dir


def test_suggest_followups_from_education_gap():
    hints = suggest_followups(["education.bachelor（本科院校与专业）"])
    assert hints
    assert any("本科" in h for h in hints)


def test_suggest_followups_limits_to_three():
    errors = [
        "education.bachelor（本科院校与专业）",
        "skills.core（吃饭的本事）",
        "strength_evidence（每条优势要挂证据）",
        "preferences.values_ranked（价值排序驱动取舍）",
        "geo 为空",
    ]
    hints = suggest_followups(errors)
    assert len(hints) <= 3


def test_compute_intake_progress_percent():
    progress = compute_intake_progress(
        has_profile=True,
        name_ok=True,
        role_ok=True,
        education_ok=True,
        skills_ok=False,
        evidence_ok=False,
        values_ok=False,
        narrative_ok=False,
    )
    assert progress.percent == 33  # 2/6 rounded


def test_narrative_sections_ok_requires_content():
    bad = "# Narrative\n\n## 职业故事\n\n\n## 我想要的\n\nx\n\n## 红线\n\ny\n"
    assert narrative_sections_ok(bad) is False
    good = (
        "# Narrative\n\n## 职业故事\n\n从数据工程转向 LLM 应用。\n\n"
        "## 我想要的\n\n技术深度与业务影响平衡。\n\n"
        "## 红线\n\n不接受纯运维岗。\n"
    )
    assert narrative_sections_ok(good) is True


def test_build_intake_status_with_examples(examples_dir: Path):
    status = build_intake_status(examples_dir)
    assert "profile_preview" in status
    assert "progress" in status
    assert status["profile_preview"]["core_skills"]
    assert status["intake_complete"] is True
    assert status["gap_hints"] == []


def test_build_intake_status_empty_dir(tmp_path: Path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "profile.example.yaml").write_text("name: null\n", encoding="utf-8")
    (templates / "constraints.example.yaml").write_text("geo: []\n", encoding="utf-8")
    data = tmp_path / "data"
    bootstrap_data_dir(data, templates)
    status = build_intake_status(data)
    assert status["intake_complete"] is False
    assert status["gap_hints"]
