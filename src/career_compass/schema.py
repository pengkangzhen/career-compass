"""Pydantic 模型：profile / constraints / signals / opportunities / sectors —— 唯一事实源的数据契约。

设计原则：
- 画像的可信度来自"证据"。StrengthEvidence 强制每条优势挂一个客观事实。
- Profile.gaps() 是 intake 完整性闸门。
- OpportunityMatrix 是核心交付物；Sector 是宏观行业池（用户调研）。
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, HttpUrl, ValidationError

__all__ = [
    "RiskAppetite", "Education", "Experience", "StrengthEvidence",
    "Preferences", "Skills", "Profile", "Constraints", "Signal",
    "Opportunity", "OpportunityMatrix", "Sector",
    "ValidationError", "load_profile", "load_constraints", "load_signals",
    "load_opportunities", "save_opportunities", "load_sectors",
]


class RiskAppetite(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Education(BaseModel):
    degree: str
    major: str
    school: str
    year: Optional[int] = None
    ranking_or_gpa: Optional[str] = None


class Experience(BaseModel):
    company: str
    role: str
    period: str  # 如 "2023.01-2024.06"
    scope: str   # 你负责什么
    quantified_outcomes: list[str] = Field(default_factory=list)  # 带数字的成果


class StrengthEvidence(BaseModel):
    claim: str   # "我擅长 X"
    proof: str   # 必须是客观事实/事件/数字，禁止空话


class Preferences(BaseModel):
    energized_by: list[str] = Field(default_factory=list)
    drained_by: list[str] = Field(default_factory=list)
    values_ranked: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    core: list[str] = Field(default_factory=list)      # 能教别人、靠它吃饭的
    adjacent: list[str] = Field(default_factory=list)  # 能快速上手、形成组合拳
    frontier: list[str] = Field(default_factory=list)  # 在学/刚接触的


class Profile(BaseModel):
    name: Optional[str] = None
    current_role: Optional[str] = None
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    strength_evidence: list[StrengthEvidence] = Field(default_factory=list)
    preferences: Preferences = Field(default_factory=Preferences)

    def gaps(self) -> list[str]:
        """缺失的关键字段 —— intake 完整性检查。返回空列表表示可进入分析。"""
        missing: list[str] = []
        if not self.education and not self.experience:
            missing.append("education 或 experience 至少要有一个")
        if not self.skills.core:
            missing.append("skills.core（吃饭的本事）")
        if not self.strength_evidence:
            missing.append("strength_evidence（每条优势要挂证据）")
        if not self.preferences.values_ranked:
            missing.append("preferences.values_ranked（价值排序驱动取舍）")
        weak = [
            s.claim
            for s in self.strength_evidence
            if not s.proof.strip() or s.proof.strip().lower() in {"n/a", "tbd", "todo", "待补"}
        ]
        if weak:
            missing.append(f"strength_evidence 缺证据: {weak}")
        return missing


class Constraints(BaseModel):
    geo: list[str] = Field(default_factory=list)
    visa: Optional[str] = None
    family: Optional[str] = None
    financial_runway_months: int = Field(default=0, ge=0)
    risk_appetite: RiskAppetite = RiskAppetite.medium
    reversibility_bias: str = "high"  # high=偏好可逆决策, low=愿意 all-in
    age: Optional[int] = None          # 年龄 —— 国内学术路线对年龄敏感（青基/博新年龄线）
    notes: str = ""                    # 其他硬约束的补充说明


class Signal(BaseModel):
    topic: str
    finding: str
    source: str
    source_url: Optional[HttpUrl] = None
    retrieved_on: date
    confidence: str = "medium"


# ---------- 机会矩阵（核心交付物）----------

class Opportunity(BaseModel):
    direction: str
    fit: str                             # 高/中/低 — L1 比较优势
    fit_rationale: str
    match: str                           # 高/中/低 — L2 Ikigai+期权
    match_rationale: str
    wind: str                            # 顺风/弱顺风/逆风 — L3
    wind_rationale: str
    risk: str                            # 可逆/commit — L4
    risk_rationale: str
    composite: str = "C"                 # A-F
    opens_up: list[str] = Field(default_factory=list)
    costs: list[str] = Field(default_factory=list)
    first_step: str = ""


class OpportunityMatrix(BaseModel):
    generated_on: date
    directions: list[Opportunity] = Field(default_factory=list)

    _RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    def ranked(self) -> list[Opportunity]:
        return sorted(
            self.directions,
            key=lambda o: self._RANK.get(o.composite.strip().upper(), 9),
        )


# ---------- 宏观行业池（用户调研）----------

class Sector(BaseModel):
    name: str
    why_hot: str = ""        # 为什么热（趋势/政策/需求）
    value_is_in: str = ""    # 真正值/护城河在哪 —— "深"的环节
    trap: str = ""           # 警惕停在"浅"的环节（如只会调 API、只会发论文）
    source: str = ""         # 来源；未补齐前，分析时标"待验证"
    fit_notes: str = ""      # 与用户画像的交叉点（analyze 阶段填）


# ---------- 加载器 ----------

def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_profile(path: Path) -> Profile:
    return Profile.model_validate(_load_yaml(path))


def load_constraints(path: Path) -> Constraints:
    return Constraints.model_validate(_load_yaml(path))


def load_signals(signals_dir: Path) -> dict[str, list[Signal]]:
    out: dict[str, list[Signal]] = {}
    if not signals_dir.exists():
        return out
    for p in sorted(signals_dir.glob("*.yaml")):
        raw = _load_yaml(p)
        out[p.stem] = [Signal.model_validate(s) for s in raw.get("signals", [])]
    return out


def load_opportunities(path: Path) -> OpportunityMatrix:
    return OpportunityMatrix.model_validate(_load_yaml(path))


def save_opportunities(path: Path, matrix: OpportunityMatrix) -> None:
    path.write_text(
        yaml.safe_dump(matrix.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def load_sectors(path: Path) -> list[Sector]:
    data = _load_yaml(path)
    return [Sector.model_validate(s) for s in data.get("sectors", [])]


# ---------- 项目证据（scan-projects 自动 harvest）----------

class Scale(BaseModel):
    files: int = 0
    commits: Optional[int] = None
    has_tests: bool = False


class ProjectEvidence(BaseModel):
    path: str
    name: str
    description: str = ""
    is_git: bool = False
    last_commit: Optional[date] = None
    languages: dict[str, int] = Field(default_factory=dict)   # 语言 -> 文件数
    dependency_count: int = 0
    key_dependencies: list[str] = Field(default_factory=list)  # 命中信号表的依赖名
    scale: Scale = Field(default_factory=Scale)
    artifacts: list[str] = Field(default_factory=list)         # paper/ docs/ results/ LaTeX 等
    inferred_signals: list[str] = Field(default_factory=list)  # 推断的技能标签


class ProjectsFile(BaseModel):
    scanned_on: date
    projects: list[ProjectEvidence] = Field(default_factory=list)


def load_projects(path: Path) -> ProjectsFile:
    return ProjectsFile.model_validate(_load_yaml(path))


def save_projects(path: Path, projects: ProjectsFile) -> None:
    path.write_text(
        yaml.safe_dump(projects.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
