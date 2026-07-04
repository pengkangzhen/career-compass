"""Pydantic 模型：profile / constraints / signals / opportunities / sectors —— 唯一事实源的数据契约。

设计原则：
- 画像的可信度来自"证据"。StrengthEvidence 强制每条优势挂一个客观事实。
- Profile.gaps() 是 intake 完整性闸门。
- OpportunityMatrix 是核心交付物；Sector 是宏观行业池（用户调研）。
"""
from __future__ import annotations

import re
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, HttpUrl, ValidationError

__all__ = [
    "RiskAppetite", "EducationLevel", "EducationStatus", "Education", "Experience", "StrengthEvidence",
    "Preferences", "Skills", "Profile", "Constraints", "Signal",
    "RoleFamily", "SkillGap", "Opportunity", "OpportunityMatrix", "Sector",
    "ValueChainNode", "Subsector", "Industry", "IndustryGraph",
    "TaxonomyRoleFamily", "RoleTaxonomy",
    "ValidationError", "ValidationIssue", "ValidationResult",
    "PLACEHOLDER_PATTERNS", "is_placeholder",
    "validate_constraints", "validate_narrative", "validate_profile_text_fields",
    "signal_staleness_days", "count_signals",
    "load_profile", "load_constraints", "load_signals",
    "load_opportunities", "save_opportunities", "load_sectors",
    "load_industry_graph", "load_role_taxonomy",
    "ApplicationStatus", "ApplicationTier", "Application", "ApplicationsFile",
    "load_applications", "save_applications",
    "SavedJobStatus", "SavedJob", "SavedJobsFile",
    "load_saved_jobs", "save_saved_jobs",
]


# ---------- 占位符检测（intake 闸门）----------

PLACEHOLDER_PATTERNS: tuple[str, ...] = (
    "(待填)", "（待填）", "tbd", "todo", "待补", "（待补）", "探索中", "待明确", "（待明确）",
    "n/a", "待验证", "示例", "请替换", "请填写",
)


def is_placeholder(text: str | None) -> bool:
    """文本为空或含占位标记则视为未填实。"""
    if text is None:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    for pat in PLACEHOLDER_PATTERNS:
        if pat.lower() in lower:
            return True
    return False


class ValidationIssue(BaseModel):
    level: str  # "error" | "warning"
    field: str
    message: str


class ValidationResult(BaseModel):
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def merge(self, other: ValidationResult) -> ValidationResult:
        return ValidationResult(
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


class RiskAppetite(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EducationLevel(str, Enum):
    bachelor = "bachelor"
    master = "master"
    phd = "phd"


class EducationStatus(str, Enum):
    graduated = "graduated"
    enrolled = "enrolled"


LEVEL_CN: dict[EducationLevel, str] = {
    EducationLevel.bachelor: "本科",
    EducationLevel.master: "硕士",
    EducationLevel.phd: "博士",
}

TIER_ONLY_SCHOOL_LABELS: frozenset[str] = frozenset({
    "985", "211", "双一流", "一本", "二本", "三本", "海外", "其他",
})


def infer_education_level(degree: str) -> EducationLevel | None:
    """从 degree 文案推断学历层级（兼容旧 profile）。"""
    text = degree.strip().lower()
    if not text:
        return None
    if any(k in text for k in ("博士", "phd", "博后")):
        return EducationLevel.phd
    if any(k in text for k in ("硕士", "master", "研究生")):
        return EducationLevel.master
    if any(k in text for k in ("本科", "学士", "bachelor")):
        return EducationLevel.bachelor
    return None


class Education(BaseModel):
    level: Optional[EducationLevel] = None
    degree: str = ""                 # 显示用，如「工学硕士」「博士在读」
    major: str = ""
    school: str = ""                 # 院校全名
    school_tier: Optional[str] = None  # 985/211/双一流/一本/二本/海外
    department: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    year: Optional[int] = None       # 兼容旧字段，等同 end_year
    status: EducationStatus = EducationStatus.graduated
    ranking_or_gpa: Optional[str] = None
    honors: Optional[str] = None
    thesis_or_focus: Optional[str] = None
    advisor: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        if self.year is not None and self.end_year is None:
            object.__setattr__(self, "end_year", self.year)
        if self.level is None and self.degree:
            inferred = infer_education_level(self.degree)
            if inferred is not None:
                object.__setattr__(self, "level", inferred)
        if self.status == EducationStatus.graduated and self.degree and "在读" in self.degree:
            object.__setattr__(self, "status", EducationStatus.enrolled)

    def resolved_level(self) -> EducationLevel | None:
        if self.level is not None:
            return self.level
        return infer_education_level(self.degree)

    def level_label(self) -> str:
        lv = self.resolved_level()
        if lv is not None:
            return LEVEL_CN[lv]
        return self.degree or "学历"

    def school_looks_like_tier_only(self) -> bool:
        s = self.school.strip()
        return bool(s) and s in TIER_ONLY_SCHOOL_LABELS

    def graduation_hint(self) -> str:
        if self.end_year is None:
            return ""
        if self.status == EducationStatus.enrolled:
            return f"预计 {self.end_year}"
        return str(self.end_year)


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

    def sorted_education(self) -> list[Education]:
        order = {EducationLevel.bachelor: 0, EducationLevel.master: 1, EducationLevel.phd: 2}
        return sorted(
            self.education,
            key=lambda e: order.get(e.resolved_level(), 9),
        )

    def education_for(self, level: EducationLevel) -> Education | None:
        for edu in self.education:
            if edu.resolved_level() == level:
                return edu
        return None

    def _education_gaps(self) -> list[str]:
        missing: list[str] = []
        if not self.education:
            missing.append("education（至少填本科院校与专业）")
            return missing

        if self.education_for(EducationLevel.bachelor) is None:
            missing.append("education.bachelor（本科院校与专业）")

        for edu in self.education:
            label = edu.level_label()
            if is_placeholder(edu.school):
                missing.append(f"education.{label}.school（院校全名）")
            elif edu.school_looks_like_tier_only():
                missing.append(
                    f"education.{label}.school 请填院校全名（school_tier 单独填层级）"
                )
            if is_placeholder(edu.major):
                missing.append(f"education.{label}.major（专业）")
        return missing

    def gaps(self) -> list[str]:
        """缺失的关键字段 —— intake 完整性检查。返回空列表表示可进入分析。"""
        missing: list[str] = []
        if not self.education and not self.experience:
            missing.append("education 或 experience 至少要有一个")
        missing.extend(self._education_gaps())
        if not self.skills.core:
            missing.append("skills.core（吃饭的本事）")
        elif any(is_placeholder(s) for s in self.skills.core):
            missing.append("skills.core 含占位内容，请填真实技能")
        if not self.strength_evidence:
            missing.append("strength_evidence（每条优势要挂证据）")
        if not self.preferences.values_ranked:
            missing.append("preferences.values_ranked（价值排序驱动取舍）")
        weak = [
            s.claim
            for s in self.strength_evidence
            if is_placeholder(s.proof) or is_placeholder(s.claim)
        ]
        if weak:
            missing.append(f"strength_evidence 缺证据或占位: {weak}")
        if self.name and is_placeholder(self.name):
            missing.append("name 仍为占位，请替换为真实姓名或标识")
        if self.current_role and is_placeholder(self.current_role):
            missing.append("current_role 仍为占位")
        return missing


def validate_profile_text_fields(profile: Profile) -> ValidationResult:
    """额外文本字段校验（warnings）。"""
    warnings: list[ValidationIssue] = []
    for exp in profile.experience:
        if is_placeholder(exp.company) or is_placeholder(exp.scope):
            warnings.append(ValidationIssue(
                level="warning", field="experience",
                message=f"经历 {exp.role!r} 的公司/职责含占位内容",
            ))
    for edu in profile.education:
        label = edu.level_label()
        if is_placeholder(edu.school):
            warnings.append(ValidationIssue(
                level="warning", field="education",
                message=f"学历 {label} 的学校含占位内容",
            ))
        elif edu.school_looks_like_tier_only():
            warnings.append(ValidationIssue(
                level="warning", field="education",
                message=f"学历 {label} 的 school 仅为层级标签，请填院校全名",
            ))
        if is_placeholder(edu.major):
            warnings.append(ValidationIssue(
                level="warning", field="education",
                message=f"学历 {label} 的专业含占位内容",
            ))
    return ValidationResult(warnings=warnings)


class Constraints(BaseModel):
    geo: list[str] = Field(default_factory=list)
    visa: Optional[str] = None
    family: Optional[str] = None
    financial_runway_months: int = Field(default=0, ge=0)
    risk_appetite: RiskAppetite = RiskAppetite.medium
    reversibility_bias: str = "high"  # high=偏好可逆决策, low=愿意 all-in
    age: Optional[int] = None          # 年龄 —— 国内学术路线对年龄敏感（青基/博新年龄线）
    notes: str = ""                    # 其他硬约束的补充说明


def validate_constraints(constraints: Constraints) -> ValidationResult:
    """约束文件语义校验。"""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not constraints.geo:
        warnings.append(ValidationIssue(
            level="warning", field="geo",
            message="geo 为空 —— 分析阶段无法过滤地理约束",
        ))
    elif any(is_placeholder(g) for g in constraints.geo):
        warnings.append(ValidationIssue(
            level="warning", field="geo",
            message="geo 含占位内容，请填真实可接受地点",
        ))

    if constraints.family and is_placeholder(constraints.family):
        warnings.append(ValidationIssue(
            level="warning", field="family",
            message="family 仍为占位",
        ))

    if constraints.financial_runway_months == 0:
        warnings.append(ValidationIssue(
            level="warning", field="financial_runway_months",
            message="financial_runway_months=0 —— 建议填真实财务缓冲（月）",
        ))

    return ValidationResult(errors=errors, warnings=warnings)


# narrative.md 期望的关键章节（intake 引导用）
NARRATIVE_SECTIONS: tuple[str, ...] = ("职业故事", "我想要的", "红线")


def validate_narrative(text: str) -> ValidationResult:
    """narrative.md 章节与占位校验。"""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if not text.strip():
        errors.append(ValidationIssue(
            level="error", field="narrative.md",
            message="文件为空",
        ))
        return ValidationResult(errors=errors, warnings=warnings)

    for section in NARRATIVE_SECTIONS:
        pattern = rf"##\s*{re.escape(section)}"
        match = re.search(pattern, text)
        if not match:
            warnings.append(ValidationIssue(
                level="warning", field="narrative.md",
                message=f"缺少章节「{section}」",
            ))
            continue
        # 取该章节到下一 ## 之间的内容
        start = match.end()
        next_h = re.search(r"\n##\s", text[start:])
        body = text[start: start + next_h.start()] if next_h else text[start:]
        body = re.sub(r"^>.*$", "", body, flags=re.MULTILINE).strip()
        if not body or is_placeholder(body):
            warnings.append(ValidationIssue(
                level="warning", field="narrative.md",
                message=f"章节「{section}」仍为占位或为空",
            ))

    return ValidationResult(errors=errors, warnings=warnings)


class Signal(BaseModel):
    topic: str
    finding: str
    source: str
    source_url: Optional[HttpUrl] = None
    retrieved_on: date
    confidence: str = "medium"


def signal_staleness_days(signal: Signal, max_age_days: int = 90) -> int:
    """信号距今天数；超过 max_age_days 视为 stale（返回正数差值）。"""
    return (date.today() - signal.retrieved_on).days


def is_signal_stale(signal: Signal, max_age_days: int = 90) -> bool:
    return signal_staleness_days(signal, max_age_days) > max_age_days


def count_signals(signals_dir: Path) -> int:
    """统计 signals/ 下所有 yaml 中的信号条数。"""
    total = 0
    if not signals_dir.exists():
        return 0
    for p in signals_dir.glob("*.yaml"):
        raw = _load_yaml(p)
        total += len(raw.get("signals", []))
    return total


# ---------- 机会矩阵（核心交付物）----------

class RoleFamily(BaseModel):
    """Phase 2：岗位族推荐（结构化）。"""
    role: str
    seniority: str = ""           # 如 "1-3年" / "博士直聘"
    match_score: Optional[float] = Field(default=None, ge=0, le=1)
    competition_index: Optional[float] = Field(default=None, ge=0, le=1)


class SkillGap(BaseModel):
    """Phase 2：技能缺口。"""
    skill: str
    current_level: str = ""       # 如 "adjacent" / "frontier"
    target_level: str = ""        # 如 "core for target role"
    priority: str = "medium"      # high / medium / low
    notes: str = ""


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
    synergizes_with: list[str] = Field(default_factory=list)  # 与另一层方向的协同
    # Phase 2 可选字段（Schema 2.0，向后兼容）
    industry: Optional[str] = None
    value_chain_node: Optional[str] = None
    role_families: list[RoleFamily] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    competition_index: Optional[float] = Field(default=None, ge=0, le=1)


class OpportunityMatrix(BaseModel):
    generated_on: date
    unified_theme: str = ""
    shared_assets: list[str] = Field(default_factory=list)
    synergy_notes: str = ""
    primary: list[Opportunity] = Field(default_factory=list)
    side: list[Opportunity] = Field(default_factory=list)
    directions: list[Opportunity] = Field(default_factory=list)  # 旧字段，加载时迁移到 primary

    _RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    def model_post_init(self, __context: object) -> None:
        if self.directions and not self.primary and not self.side:
            object.__setattr__(self, "primary", list(self.directions))

    def _ranked(self, items: list[Opportunity]) -> list[Opportunity]:
        return sorted(
            items,
            key=lambda o: self._RANK.get(o.composite.strip().upper(), 9),
        )

    def ranked_primary(self) -> list[Opportunity]:
        return self._ranked(self.primary)

    def ranked_side(self) -> list[Opportunity]:
        return self._ranked(self.side)

    def ranked(self) -> list[Opportunity]:
        """向后兼容：默认返回主业排序列表。"""
        return self.ranked_primary()

    def all_directions(self) -> list[Opportunity]:
        return list(self.primary) + list(self.side)


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


# ---------- Industry Graph + Role Taxonomy（Phase 2）----------

class ValueChainNode(BaseModel):
    id: str
    name: str
    value_is_in: str = ""
    trap: str = ""


class Subsector(BaseModel):
    id: str
    name: str
    value_chain_nodes: list[ValueChainNode] = Field(default_factory=list)


class Industry(BaseModel):
    id: str
    name: str
    why_hot: str = ""
    subsectors: list[Subsector] = Field(default_factory=list)


class IndustryGraph(BaseModel):
    industries: list[Industry] = Field(default_factory=list)

    def find_node(self, industry_id: str, subsector_id: str, node_id: str) -> ValueChainNode | None:
        for ind in self.industries:
            if ind.id != industry_id:
                continue
            for sub in ind.subsectors:
                if sub.id != subsector_id:
                    continue
                for node in sub.value_chain_nodes:
                    if node.id == node_id:
                        return node
        return None

    def industry_name(self, industry_id: str) -> str:
        for ind in self.industries:
            if ind.id == industry_id:
                return ind.name
        return industry_id


class TaxonomyRoleFamily(BaseModel):
    """岗位族定义（taxonomy 层，区别于 Opportunity 内的 RoleFamily 评分快照）。"""
    id: str
    industry_id: str
    subsector_id: str
    value_chain_node_id: str
    role: str
    typical_seniority: str = ""
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    typical_companies: dict[str, list[str]] = Field(default_factory=dict)


class RoleTaxonomy(BaseModel):
    role_families: list[TaxonomyRoleFamily] = Field(default_factory=list)


def load_industry_graph(path: Path) -> IndustryGraph:
    return IndustryGraph.model_validate(_load_yaml(path))


def load_role_taxonomy(path: Path) -> RoleTaxonomy:
    return RoleTaxonomy.model_validate(_load_yaml(path))


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


# ---------- 投递追踪（Phase 3）----------

class ApplicationStatus(str, Enum):
    applied = "applied"
    phone = "phone"
    onsite = "onsite"
    offer = "offer"
    rejected = "rejected"
    ghosted = "ghosted"
    withdrawn = "withdrawn"


class ApplicationTier(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class Application(BaseModel):
    id: str
    company: str
    role: str
    direction: str = ""           # 对应机会矩阵 direction
    tier: ApplicationTier = ApplicationTier.B
    applied_on: date
    channel: str = ""             # 内推 / 官网 / 猎头
    status: ApplicationStatus = ApplicationStatus.applied
    feedback: str = ""
    notes: str = ""


class ApplicationsFile(BaseModel):
    updated_on: date
    applications: list[Application] = Field(default_factory=list)


def load_applications(path: Path) -> ApplicationsFile:
    return ApplicationsFile.model_validate(_load_yaml(path))


def save_applications(path: Path, data: ApplicationsFile) -> None:
    path.write_text(
        yaml.safe_dump(data.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


# ---------- 感兴趣岗位库（收藏 JD）----------

class SavedJobStatus(str, Enum):
    interested = "interested"       # 刚收藏
    researching = "researching"     # 调研中
    ready_to_apply = "ready"        # 准备投递
    applied = "applied"             # 已转 track 投递
    archived = "archived"


class SavedJob(BaseModel):
    id: str
    company: str
    role: str
    description: str = ""         # 完整 JD 文本
    location: str = ""
    source: str = "招聘软件"       # Boss/猎聘/官网/内推链接
    saved_on: date
    status: SavedJobStatus = SavedJobStatus.interested
    linked_direction: str = ""    # 关联机会矩阵 direction
    notes: str = ""               # 用户备注（如「暂无 CCF-A」）


class SavedJobsFile(BaseModel):
    updated_on: date
    jobs: list[SavedJob] = Field(default_factory=list)


def load_saved_jobs(path: Path) -> SavedJobsFile:
    return SavedJobsFile.model_validate(_load_yaml(path))


def save_saved_jobs(path: Path, data: SavedJobsFile) -> None:
    path.write_text(
        yaml.safe_dump(data.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
