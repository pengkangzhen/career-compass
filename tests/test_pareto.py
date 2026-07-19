"""Pareto 前沿视图测试。"""
from datetime import date
from pathlib import Path

import pytest

from career_compass.pareto import (
    DEFAULT_DIMENSIONS,
    DIM_COMPETITION,
    DIM_FIT,
    DIM_HIRING_FIT,
    DIM_MATCH,
    DIM_WIND,
    cell_dimension_vector,
    compute_pareto_front,
    pareto_from_matrix,
)
from career_compass.render import render_pareto_view
from career_compass.schema import (
    Constraints,
    EmployerAxis,
    CapabilityAxis,
    MatrixCell,
    Opportunity,
    OpportunityMatrix,
)


# ---------- fixtures ----------

def _make_cell(
    capability_id: str,
    employer_id: str,
    *,
    fit: str = "中",
    match: str = "中",
    wind: str = "弱顺风",
    risk: str = "高",
    hiring_fit: str = "",
    eligibility: str = "pass",
    competition_index: float | None = 0.5,
    composite: str = "C",
    blocked: bool = False,
    costs: list[str] | None = None,
) -> MatrixCell:
    return MatrixCell(
        capability_id=capability_id,
        employer_id=employer_id,
        fit=fit,
        fit_rationale="",
        match=match,
        match_rationale="",
        wind=wind,
        wind_rationale="",
        risk=risk,
        risk_rationale="",
        composite=composite,
        hiring_fit=hiring_fit,
        eligibility=eligibility,
        blocked=blocked,
        competition_index=competition_index,
        costs=costs or [],
    )


def _make_opportunity(
    direction: str,
    *,
    fit: str = "中",
    match: str = "中",
    wind: str = "弱顺风",
    risk: str = "高",
    hiring_fit: str = "",
    eligibility: str = "pass",
    competition_index: float | None = 0.5,
    composite: str = "C",
) -> Opportunity:
    return Opportunity(
        direction=direction,
        fit=fit,
        fit_rationale="",
        match=match,
        match_rationale="",
        wind=wind,
        wind_rationale="",
        risk=risk,
        risk_rationale="",
        composite=composite,
        hiring_fit=hiring_fit,
        eligibility=eligibility,
        competition_index=competition_index,
    )


# ---------- 维度映射 ----------

class TestDimensionVector:
    def test_three_level_labels(self):
        v = cell_dimension_vector(_make_cell("a", "b", fit="高", match="低"))
        assert v[DIM_FIT] == 1.0
        assert v[DIM_MATCH] == 0.0

    def test_wind_four_levels(self):
        assert cell_dimension_vector(_make_cell("a", "b", wind="顺风"))[DIM_WIND] == 1.0
        assert cell_dimension_vector(_make_cell("a", "b", wind="逆风"))[DIM_WIND] == 0.0
        assert 0 < cell_dimension_vector(_make_cell("a", "b", wind="弱顺风"))[DIM_WIND] < 1.0

    def test_risk_is_inverted(self):
        # risk=低 → 试错成本低 → 高分
        assert cell_dimension_vector(_make_cell("a", "b", risk="低"))["trial_cost"] == 1.0
        assert cell_dimension_vector(_make_cell("a", "b", risk="高"))["trial_cost"] == 0.0

    def test_competition_is_inverted(self):
        # competition_index 低 = 竞争少 = 高分
        v = cell_dimension_vector(_make_cell("a", "b", competition_index=0.1))
        assert v[DIM_COMPETITION] == pytest.approx(0.9)

    def test_hiring_fit_falls_back_to_eligibility(self):
        # 空 hiring_fit 时从 eligibility 推导
        v = cell_dimension_vector(_make_cell("a", "b", eligibility="pass", hiring_fit=""))
        assert v[DIM_HIRING_FIT] == 1.0
        v = cell_dimension_vector(_make_cell("a", "b", eligibility="fail", hiring_fit=""))
        assert v[DIM_HIRING_FIT] == 0.0

    def test_unknown_label_is_neutral(self):
        # 未知标签 → 0.5，不支配也不被支配
        v = cell_dimension_vector(_make_cell("a", "b", fit="奇怪值"))
        assert v[DIM_FIT] == 0.5

    def test_missing_competition_is_neutral(self):
        v = cell_dimension_vector(_make_cell("a", "b", competition_index=None))
        assert v[DIM_COMPETITION] == 0.5


# ---------- 支配关系 ----------

class TestDomination:
    def test_simple_dominance(self):
        # A 在所有维度 >= B 且一维严格 > → A 支配 B
        a = _make_cell("a", "private", fit="高", match="高", wind="顺风", risk="低")
        b = _make_cell("b", "private", fit="中", match="中", wind="弱顺风", risk="高")
        report = compute_pareto_front([a, b])
        front_labels = {e.label for e in report.front}
        dominated_labels = {e.label for e in report.dominated}
        assert front_labels == {"a × private"}
        assert dominated_labels == {"b × private"}

    def test_pareto_front_keeps_incomparable(self):
        # A 强 fit 弱 wind；B 弱 fit 强 wind → 都在前沿
        a = _make_cell("a", "private", fit="高", match="低", wind="逆风", risk="高")
        b = _make_cell("b", "private", fit="低", match="高", wind="顺风", risk="低")
        report = compute_pareto_front([a, b])
        assert len(report.front) == 2
        assert len(report.dominated) == 0

    def test_partial_domination_is_not_domination(self):
        # A 在 fit/wind 更好，但在 risk 更差 → 互不支配
        a = _make_cell("a", "private", fit="高", match="高", wind="顺风", risk="高")
        b = _make_cell("b", "private", fit="中", match="中", wind="弱顺风", risk="低")
        report = compute_pareto_front([a, b])
        assert len(report.front) == 2
        assert len(report.dominated) == 0

    def test_three_way_chain(self):
        # A > B > C 在所有维度
        a = _make_cell("a", "x", fit="高", match="高", wind="顺风", risk="低")
        b = _make_cell("b", "x", fit="中", match="中", wind="弱顺风", risk="高")
        c = _make_cell("c", "x", fit="低", match="低", wind="逆风", risk="高")
        report = compute_pareto_front([a, b, c])
        assert len(report.front) == 1
        assert report.front[0].label == "a × x"
        # b 应被 a 支配，c 应被 a 和 b 都支配
        b_entry = next(e for e in report.entries if e.label == "b × x")
        c_entry = next(e for e in report.entries if e.label == "c × x")
        assert "a × x" in b_entry.dominated_by
        assert "a × x" in c_entry.dominated_by
        assert "b × x" in c_entry.dominated_by

    def test_identical_cells_both_on_front(self):
        # 完全相同的两个 cell：互不严格支配 → 都在前沿
        a = _make_cell("a", "x", fit="高", match="中")
        b = _make_cell("b", "x", fit="高", match="中")
        report = compute_pareto_front([a, b])
        assert len(report.front) == 2


# ---------- 边界情况 ----------

class TestEdgeCases:
    def test_empty_input(self):
        report = compute_pareto_front([])
        assert report.size == 0
        assert report.front == []

    def test_single_cell_is_front(self):
        a = _make_cell("a", "x", fit="中", match="中")
        report = compute_pareto_front([a])
        assert len(report.front) == 1
        assert report.front[0].is_pareto

    def test_blocked_cells_excluded_by_default(self):
        a = _make_cell("a", "x", fit="高", match="高", blocked=True)
        b = _make_cell("b", "x", fit="低", match="低", blocked=False)
        report = compute_pareto_front([a, b])
        # blocked 被排除，只剩 b
        assert report.size == 1
        assert report.entries[0].label == "b × x"

    def test_blocked_cells_included_when_flag_set(self):
        a = _make_cell("a", "x", fit="高", match="高", blocked=True)
        b = _make_cell("b", "x", fit="低", match="低", blocked=False)
        report = compute_pareto_front([a, b], exclude_blocked=False)
        assert report.size == 2
        assert len(report.front) == 1
        assert report.front[0].label == "a × x"

    def test_custom_dimensions(self):
        # 仅看 fit + wind 两个维度
        a = _make_cell("a", "x", fit="高", match="低", wind="逆风", risk="低")
        b = _make_cell("b", "x", fit="低", match="高", wind="顺风", risk="高")
        report = compute_pareto_front([a, b], dimensions=("fit", "wind"))
        # 两维上互不可比 → 都在前沿
        assert len(report.front) == 2

    def test_custom_dimensions_can_cause_domination(self):
        # 全维度下互不支配；只看 fit 时 a 严格支配 b
        a = _make_cell("a", "x", fit="高", match="低", wind="逆风", risk="高")
        b = _make_cell("b", "x", fit="中", match="高", wind="顺风", risk="低")
        full = compute_pareto_front([a, b])
        assert len(full.front) == 2
        fit_only = compute_pareto_front([a, b], dimensions=("fit",))
        # 单维上 a(高) > b(中)，严格支配
        assert len(fit_only.front) == 1
        assert fit_only.front[0].label == "a × x"


# ---------- distinctive dims（前沿独占最高分） ----------

class TestDistinctiveDims:
    def test_distinctive_dims_when_one_cell_wins_a_dim(self):
        # 前沿里两个 cell：a 在 fit 最高、b 在 wind 最高
        a = _make_cell("a", "x", fit="高", match="中", wind="中", risk="中")
        b = _make_cell("b", "x", fit="中", match="中", wind="顺风", risk="中")
        report = compute_pareto_front([a, b])
        a_entry = next(e for e in report.front if e.label == "a × x")
        b_entry = next(e for e in report.front if e.label == "b × x")
        assert "fit" in a_entry.distinctive_dims
        assert "wind" in b_entry.distinctive_dims

    def test_no_distinctive_when_tied(self):
        # a 在 fit 最高，b 在 match 最高，但两者在 wind 上并列最高 → wind 不算 distinctive
        a = _make_cell("a", "x", fit="高", match="低", wind="顺风", risk="中")
        b = _make_cell("b", "x", fit="低", match="高", wind="顺风", risk="中")
        report = compute_pareto_front([a, b])
        # a/b 在 wind 上都最高 → 不算任何人的 distinctive
        for e in report.front:
            assert "wind" not in e.distinctive_dims
        # 但 fit/match 各有独占者
        a_entry = next(e for e in report.front if e.label == "a × x")
        b_entry = next(e for e in report.front if e.label == "b × x")
        assert "fit" in a_entry.distinctive_dims
        assert "match" in b_entry.distinctive_dims


# ---------- 从 OpportunityMatrix 入口 ----------

class TestParetoFromMatrix:
    def test_prefers_cross_matrix_when_available(self):
        cells = [
            _make_cell("a", "private", fit="高", match="高"),
            _make_cell("b", "private", fit="低", match="低"),
        ]
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A"), CapabilityAxis(id="b", name="B")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=cells,
        )
        report = pareto_from_matrix(matrix)
        assert report.size == 2
        assert len(report.front) == 1
        assert report.front[0].label == "a × private"

    def test_falls_back_to_primary(self):
        # 没有 cross_matrix → 用 primary
        opps = [
            _make_opportunity("LLM 应用", fit="高", match="高"),
            _make_opportunity("传统后端", fit="低", match="低"),
        ]
        matrix = OpportunityMatrix(generated_on=date.today(), primary=opps)
        report = pareto_from_matrix(matrix)
        assert report.size == 2
        assert report.front[0].cell.direction == "LLM 应用"


# ---------- 渲染 ----------

class TestRender:
    def test_render_contains_front_section(self, tmp_path):
        cells = [
            _make_cell("a", "private", fit="高", match="中", wind="顺风", risk="低", composite="A"),
            _make_cell("b", "private", fit="低", match="高", wind="逆风", risk="低", composite="B"),
        ]
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A"), CapabilityAxis(id="b", name="B")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=cells,
        )
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        out = render_pareto_view(path)
        assert "Pareto 前沿" in out
        assert "前沿方向" in out
        assert "a × private" in out
        assert "b × private" in out
        # 两者互不支配 → 都在前沿
        assert "被支配方向" not in out

    def test_render_shows_dominated_section(self, tmp_path):
        cells = [
            _make_cell("a", "private", fit="高", match="高", wind="顺风", risk="低", composite="A"),
            _make_cell("b", "private", fit="中", match="中", wind="弱顺风", risk="高", composite="C"),
        ]
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A"), CapabilityAxis(id="b", name="B")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=cells,
        )
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        out = render_pareto_view(path)
        assert "被支配方向" in out
        assert "a × private" in out  # 前沿
        assert "b × private" in out  # 被支配

    def test_render_dimension_explainer(self, tmp_path):
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=[_make_cell("a", "private")],
        )
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        out = render_pareto_view(path)
        assert "维度说明" in out
        assert "核心竞争力" in out
        assert "Ikigai" in out

    def test_render_custom_dims(self, tmp_path):
        cells = [
            _make_cell("a", "private", fit="高", match="低", wind="逆风", risk="高"),
            _make_cell("b", "private", fit="低", match="高", wind="顺风", risk="低"),
        ]
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A"), CapabilityAxis(id="b", name="B")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=cells,
        )
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        # 只看 fit 单维 → a 严格支配 b
        out = render_pareto_view(path, dimensions=("fit",))
        assert "被支配方向" in out
        assert "b × private" in out

    def test_render_empty_matrix(self, tmp_path):
        matrix = OpportunityMatrix(generated_on=date.today())
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        out = render_pareto_view(path)
        assert "无前沿方向" in out

    def test_render_distinctive_dims_in_spotlight(self, tmp_path):
        cells = [
            _make_cell("a", "private", fit="高", match="中", wind="中", risk="中"),
            _make_cell("b", "private", fit="中", match="中", wind="顺风", risk="中"),
        ]
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id="a", name="A"), CapabilityAxis(id="b", name="B")],
            employer_axes=[EmployerAxis(id="private", name="民企")],
            cross_matrix=cells,
        )
        from career_compass.schema import save_opportunities
        path = tmp_path / "opportunities.yaml"
        save_opportunities(path, matrix)

        out = render_pareto_view(path)
        assert "独占强项" in out
        assert "核心竞争力" in out  # a 独占 fit
        assert "行业趋势" in out     # b 独占 wind


# ---------- CLI smoke test ----------

class TestCLI:
    def _write_opportunities(self, tmp_path: Path, cells: list[MatrixCell]) -> Path:
        """Create a tmp data dir with opportunities.yaml + minimal employer/cap axes."""
        from career_compass.schema import save_opportunities

        cap_ids = sorted({c.capability_id for c in cells})
        emp_ids = sorted({c.employer_id for c in cells})
        matrix = OpportunityMatrix(
            generated_on=date.today(),
            capability_axes=[CapabilityAxis(id=c, name=c.upper()) for c in cap_ids],
            employer_axes=[EmployerAxis(id=e, name=e) for e in emp_ids],
            cross_matrix=cells,
        )
        save_opportunities(tmp_path / "opportunities.yaml", matrix)
        return tmp_path

    def test_pareto_stdout(self, tmp_path, monkeypatch, capsys):
        import argparse
        import os
        from career_compass.cli import cmd_pareto

        monkeypatch.setenv("CC_DATA", str(tmp_path))
        # cmd_pareto 通过模块顶层 DATA = Path(os.getenv("CC_DATA", "data")) 读取；
        # DATA 在 import 时已绑定，所以需要直接 patch
        import career_compass.cli as cli
        monkeypatch.setattr(cli, "DATA", tmp_path)
        monkeypatch.setattr(cli, "OPPORTUNITIES_YAML", tmp_path / "opportunities.yaml")

        cells = [
            _make_cell("a", "private", fit="高", match="高", wind="顺风", risk="低"),
            _make_cell("b", "private", fit="低", match="低", wind="逆风", risk="高"),
        ]
        self._write_opportunities(tmp_path, cells)

        args = argparse.Namespace(
            dims="",
            include_blocked=False,
            stdout=True,
        )
        rc = cmd_pareto(args)
        assert rc == 0
        captured = capsys.readouterr()
        assert "Pareto 前沿" in captured.out
        assert "a × private" in captured.out

    def test_pareto_writes_file(self, tmp_path, monkeypatch):
        import argparse
        import career_compass.cli as cli

        monkeypatch.setattr(cli, "DATA", tmp_path)
        monkeypatch.setattr(cli, "OPPORTUNITIES_YAML", tmp_path / "opportunities.yaml")

        cells = [_make_cell("a", "private")]
        self._write_opportunities(tmp_path, cells)

        args = argparse.Namespace(
            dims="",
            include_blocked=False,
            stdout=False,
        )
        rc = cli.cmd_pareto(args)
        assert rc == 0
        assert (tmp_path / "pareto.md").exists()

    def test_pareto_rejects_unknown_dim(self, tmp_path, monkeypatch, capsys):
        import argparse
        import career_compass.cli as cli

        monkeypatch.setattr(cli, "DATA", tmp_path)
        monkeypatch.setattr(cli, "OPPORTUNITIES_YAML", tmp_path / "opportunities.yaml")

        cells = [_make_cell("a", "private")]
        self._write_opportunities(tmp_path, cells)

        args = argparse.Namespace(
            dims="not_a_dim",
            include_blocked=False,
            stdout=True,
        )
        rc = cli.cmd_pareto(args)
        assert rc == 1
        captured = capsys.readouterr()
        assert "未知维度" in captured.out

    def test_pareto_custom_dims(self, tmp_path, monkeypatch, capsys):
        import argparse
        import career_compass.cli as cli

        monkeypatch.setattr(cli, "DATA", tmp_path)
        monkeypatch.setattr(cli, "OPPORTUNITIES_YAML", tmp_path / "opportunities.yaml")

        # 只看 fit 一维：a 严格支配 b
        cells = [
            _make_cell("a", "private", fit="高", match="低", wind="逆风", risk="高"),
            _make_cell("b", "private", fit="低", match="高", wind="顺风", risk="低"),
        ]
        self._write_opportunities(tmp_path, cells)

        args = argparse.Namespace(
            dims="fit",
            include_blocked=False,
            stdout=True,
        )
        rc = cli.cmd_pareto(args)
        assert rc == 0
        captured = capsys.readouterr()
        # 单维上 a(高) > b(低)，b 被支配
        assert "被支配方向" in captured.out
        assert "b × private" in captured.out
