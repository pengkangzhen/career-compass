from pathlib import Path

import pytest

from career_compass.jd_link import (
    format_direction,
    load_jd_link_rules,
    resolve_linked_direction,
    score_capability,
)
from career_compass.schema import load_opportunities

REPO_DATA = Path(__file__).resolve().parent.parent / "data"


def test_score_capability_or_jd():
    rules = load_jd_link_rules(REPO_DATA)
    cap, hits = score_capability(
        "Python Gurobi MIP 供应链调度 物流优化",
        rules,
    )
    assert cap == "sc_optimization"
    assert hits >= 2


def test_score_capability_llm_agent():
    rules = load_jd_link_rules(REPO_DATA)
    cap, hits = score_capability(
        "LangGraph LLM Agent RAG 大模型 智能体",
        rules,
    )
    assert cap == "decision_agent_or"
    assert hits >= 2


def test_resolve_with_matrix_uses_employer_hint():
    draft = REPO_DATA / "opportunities.draft.yaml"
    if not draft.is_file():
        pytest.skip("no opportunities draft")
    matrix = load_opportunities(draft)
    linked = resolve_linked_direction(
        "字节跳动 运筹优化 供应链 Agent LangGraph",
        matrix=matrix,
        data_dir=REPO_DATA,
    )
    assert "（" in linked
    assert "民企" in linked or "互联网" in linked


def test_format_direction_fallback_without_matrix():
    assert "半导体" in format_direction("semi_fab_or", None)


def test_resolve_empty_for_unrelated_jd():
    assert resolve_linked_direction("行政助理 会议纪要", data_dir=REPO_DATA) == ""
