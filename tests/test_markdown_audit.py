"""Markdown 渲染产物结构审计。"""
from pathlib import Path

import pytest

from career_compass.markdown_audit import audit_markdown
from career_compass.render import (
    render_execution_pack,
    render_job_pack,
    render_opportunities,
)


def _repo_data() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def test_opportunities_markdown_structure(examples_dir: Path):
    md = render_opportunities(examples_dir / "opportunities.yaml")
    issues = audit_markdown(md, "examples/opportunities")
    assert not issues, "\n".join(issues)


def test_opportunities_user_data_if_present():
    opps = _repo_data() / "opportunities.yaml"
    if not opps.exists():
        pytest.skip("no user opportunities.yaml")
    md = render_opportunities(opps)
    issues = audit_markdown(md, "data/opportunities")
    assert not issues, "\n".join(issues)


def test_job_pack_markdown_structure(examples_dir: Path):
    rt = _repo_data() / "role_taxonomy.yaml"
    md = render_job_pack(
        examples_dir / "opportunities.yaml",
        examples_dir / "profile.yaml",
        rt if rt.exists() else None,
    )
    issues = audit_markdown(md, "job_pack")
    assert not issues, "\n".join(issues)


def test_execution_pack_markdown_structure(examples_dir: Path):
    rt = _repo_data() / "role_taxonomy.yaml"
    md = render_execution_pack(
        examples_dir / "opportunities.yaml",
        examples_dir / "profile.yaml",
        examples_dir / "narrative.md",
        examples_dir / "constraints.yaml",
        rt if rt.exists() else None,
    )
    issues = audit_markdown(md, "execution_pack")
    assert not issues, "\n".join(issues)
