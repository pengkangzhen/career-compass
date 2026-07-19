from pathlib import Path

from career_compass.render import render_execution_pack, render_job_pack, render_opportunities


def test_render_opportunities(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "机会矩阵" in out
    assert "LLM 应用工程师" in out
    assert "综合 A" in out or "综合 {{" not in out


def test_render_opportunities_overview_columns(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "方向" in out
    assert "岗位名称" in out
    assert "相关企业" in out
    assert "核心工作" in out
    assert "组织类型" in out
    assert "市场称呼示例" in out
    assert "典型岗位" not in out
    out = render_opportunities(examples_dir / "opportunities.yaml")
    assert "系统不替你做选择" in out
    assert "统一架构" in out
    assert "比较优势" in out
    assert "L1" not in out and "L2" not in out


def test_render_opportunities_summary_table_not_glued(examples_dir: Path):
    out = render_opportunities(examples_dir / "opportunities.yaml")
    # Markdown audit guard: no `| 维度 |` header glued onto a non-table line
    for line in out.splitlines():
        if "## " in line:
            assert "| 维度 |" not in line, f"table glued to heading: {line[:120]}"
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
