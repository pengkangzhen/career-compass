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
    assert "主业" in out
    assert "副业" in out
    assert "统一架构" in out
    assert "比较优势" in out
    assert "L1" not in out and "L2" not in out


def test_render_opportunities_side_table_not_glued(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    for line in out.splitlines():
        if "协同主业" in line:
            assert "| 维度 |" not in line, f"table glued to synergizes line: {line[:120]}"
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
