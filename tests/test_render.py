from pathlib import Path

from career_compass.render import render_execution_pack, render_job_pack, render_opportunities


def test_render_opportunities(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "机会矩阵" in out
    assert "LLM 应用工程师" in out
    assert "综合 A" in out or "综合 {{" not in out


def test_render_opportunities_phase2_fields(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "系统不替你做选择" in out
    assert "对比摘要" in out
    assert "四维评分说明" in out
    assert "比较优势" in out
    assert "L1" not in out and "L2" not in out
    assert "技能" in out or "RAG" in out


def test_render_job_pack(examples_dir: Path):
    out = render_job_pack(
        examples_dir / "opportunities.yaml",
        examples_dir / "profile.yaml",
        role_taxonomy_path=Path(__file__).resolve().parent.parent / "data" / "role_taxonomy.yaml",
    )
    assert "求职定位包" in out
    assert "90 天" in out
    assert "LLM 应用工程师" in out


def test_render_execution_pack(examples_dir: Path):
    repo_data = Path(__file__).resolve().parent.parent / "data"
    out = render_execution_pack(
        examples_dir / "opportunities.yaml",
        examples_dir / "profile.yaml",
        examples_dir / "narrative.md",
        examples_dir / "constraints.yaml",
        role_taxonomy_path=repo_data / "role_taxonomy.yaml",
    )
    assert "求职执行包" in out
    assert "Pitch" in out
    assert "投递策略" in out
    assert "track add" in out
