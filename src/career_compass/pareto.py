"""Pareto 前沿视图 —— 替代字母档的多目标决策层。

为什么需要：
    当前 `_composite_from_scores`（match.py）用一组魔法权重把多维塌缩成 A-F，
    隐含"用户的偏好等于这组权重"。但职业决策本质是多目标问题——
    "fit 高但 wind 逆风" vs "fit 中但 wind 顺风" 之间没有客观优劣，
    应交给用户做价值判断，而不是被字母档掩盖。

做什么：
    - 把每个 ScoredPath 的标签维度（高/中/低、顺风/逆风、…）映射到 0-1 数值
    - 计算非支配集（Pareto 前沿）—— 在所有维度上都不差于、且至少一维严格优于
    - 返回结构化报告：前沿 + 被支配者 + 由谁支配 + 各 cell 的强项

设计原则（契合 north star "never chooses for the user"）：
    Pareto 前沿就是"这些方向在客观指标上互不可比，需要你来定价值排序"。
    本模块是 **additive layer**：不修改 ScoredPath.composite，只提供新视图。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .schema import MatrixCell, Opportunity


# ---------- 维度定义 ----------

DIM_FIT = "fit"                  # L1 比较优势
DIM_MATCH = "match"              # L2 Ikigai 四圈
DIM_WIND = "wind"                # L3 顺风 / 逆风
DIM_TRIAL_COST = "trial_cost"    # L4 试错成本（低=好）
DIM_HIRING_FIT = "hiring_fit"    # Schema 2.3 资格闸门（与 fit 正交）
DIM_COMPETITION = "competition"  # 竞争密度（低=好）

DEFAULT_DIMENSIONS: tuple[str, ...] = (
    DIM_FIT,
    DIM_MATCH,
    DIM_WIND,
    DIM_TRIAL_COST,
    DIM_HIRING_FIT,
    DIM_COMPETITION,
)

DIM_LABEL_ZH: dict[str, str] = {
    DIM_FIT: "比较优势",
    DIM_MATCH: "Ikigai",
    DIM_WIND: "顺风",
    DIM_TRIAL_COST: "试错",
    DIM_HIRING_FIT: "资格",
    DIM_COMPETITION: "竞争",
}

# ---------- 标签 → 0-1 数值（所有维度统一为"越高越好"） ----------

_LEVEL_3 = {"高": 1.0, "中": 0.5, "低": 0.0}
_WIND_4 = {"顺风": 1.0, "弱顺风": 0.67, "中": 0.33, "逆风": 0.0}
# risk 字段语义反向：低试错成本 = 高分
_RISK_TO_SCORE = {"低": 1.0, "高": 0.0}
_ELIG_TO_HIRING = {"pass": "高", "review": "中", "fail": "低"}


def cell_dimension_vector(cell: MatrixCell | Opportunity) -> dict[str, float]:
    """把 ScoredPath 标签维度映射为 {dim: 0-1}；所有维度统一"越高越好"。

    缺失字段（旧 schema / 未填）回退到 0.5 中性值，既不支配也不被支配。
    """
    hiring = cell.hiring_fit or ""
    if hiring not in _LEVEL_3:
        hiring = _ELIG_TO_HIRING.get(getattr(cell, "eligibility", "pass"), "中")

    comp = cell.competition_index
    comp_score = (1.0 - comp) if comp is not None else 0.5

    return {
        DIM_FIT: _LEVEL_3.get(cell.fit, 0.5),
        DIM_MATCH: _LEVEL_3.get(cell.match, 0.5),
        DIM_WIND: _WIND_4.get(cell.wind, 0.5),
        DIM_TRIAL_COST: _RISK_TO_SCORE.get(cell.risk, 0.5),
        DIM_HIRING_FIT: _LEVEL_3.get(hiring, 0.5),
        DIM_COMPETITION: comp_score,
    }


# ---------- 支配关系 ----------

def _strictly_dominates(
    a: dict[str, float],
    b: dict[str, float],
    dims: tuple[str, ...],
) -> bool:
    """a 支配 b：所有维度 a >= b，且至少一维严格 >。"""
    has_strict = False
    for d in dims:
        if a[d] > b[d]:
            has_strict = True
        elif a[d] < b[d]:
            return False
    return has_strict


# ---------- 报告数据结构 ----------

@dataclass
class ParetoEntry:
    cell: MatrixCell | Opportunity
    vector: dict[str, float]
    is_pareto: bool = False
    dominated_by: list[str] = field(default_factory=list)
    distinctive_dims: list[str] = field(default_factory=list)  # 前沿中此 cell 独占最高分的维度

    @property
    def label(self) -> str:
        if isinstance(self.cell, MatrixCell):
            return self.cell.direction_label
        return self.cell.direction


@dataclass
class ParetoReport:
    entries: list[ParetoEntry]
    dimensions: tuple[str, ...]

    @property
    def front(self) -> list[ParetoEntry]:
        return [e for e in self.entries if e.is_pareto]

    @property
    def dominated(self) -> list[ParetoEntry]:
        return [e for e in self.entries if not e.is_pareto]

    def front_cells(self) -> list[MatrixCell | Opportunity]:
        return [e.cell for e in self.front]

    @property
    def size(self) -> int:
        return len(self.entries)


# ---------- 主入口 ----------

def compute_pareto_front(
    cells: Iterable[MatrixCell | Opportunity],
    dimensions: tuple[str, ...] = DEFAULT_DIMENSIONS,
    *,
    exclude_blocked: bool = True,
) -> ParetoReport:
    """计算 Pareto 前沿。O(n²) —— 矩阵规模 10-50 cell，足够。

    exclude_blocked=True 时跳过 eligibility=fail/blocked 的 cell：
    它们在所有维度上都不应被推荐，参与比较会让前沿噪声化。
    """
    cell_list = list(cells)
    if exclude_blocked:
        cell_list = [c for c in cell_list if not getattr(c, "blocked", False)]

    entries = [
        ParetoEntry(cell=c, vector=cell_dimension_vector(c))
        for c in cell_list
    ]
    n = len(entries)

    # O(n²) 两两比较，填 dominated_by
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if _strictly_dominates(entries[j].vector, entries[i].vector, dimensions):
                label = entries[j].label
                if label not in entries[i].dominated_by:
                    entries[i].dominated_by.append(label)

    for e in entries:
        e.is_pareto = not e.dominated_by

    _annotate_distinctive_dims(entries, dimensions)

    # 稳定排序：前沿在前；同组内按 label 字典序
    entries.sort(key=lambda e: (not e.is_pareto, e.label))
    return ParetoReport(entries=entries, dimensions=dimensions)


def _annotate_distinctive_dims(
    entries: list[ParetoEntry],
    dims: tuple[str, ...],
) -> None:
    """对每个前沿 cell，标出它在整个前沿中独占最高分的维度（解释 trade-off 用）。

    若多个前沿 cell 在某维度并列最高，则该维度不算任何人的 distinctive。
    """
    front = [e for e in entries if e.is_pareto]
    if not front:
        return
    for d in dims:
        scores = [e.vector[d] for e in front]
        max_score = max(scores)
        winners = [e for e in front if e.vector[d] == max_score]
        if len(winners) == 1:
            winners[0].distinctive_dims.append(d)


# ---------- 便捷入口：从 OpportunityMatrix 直接算 ----------

def pareto_from_matrix(
    matrix,
    dimensions: tuple[str, ...] = DEFAULT_DIMENSIONS,
) -> ParetoReport:
    """优先用 cross_matrix（Schema 2.2 正交矩阵）；否则回退到 primary。"""
    if matrix.uses_orthogonal_matrix():
        return compute_pareto_front(matrix.cross_matrix, dimensions)
    return compute_pareto_front(matrix.primary, dimensions)
