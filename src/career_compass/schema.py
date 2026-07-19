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
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator

__all__ = [
    "RiskAppetite", "EducationLevel", "EducationStatus", "Education", "EducationSummary", "Experience", "StrengthEvidence",
    "Preferences", "Skills", "Profile", "derive_education_summary", "Constraints", "EmployerPreference", "PublicSectorGates", "Signal",
    "RoleFamily", "SkillGap", "Opportunity", "OpportunityMatrix", "CapabilityAxis", "EmployerAxis",
    "MatrixCell", "Sector", "EmployerType", "EmployerTypesFile",
    "ValueChainNode", "Subsector", "Industry", "IndustryGraph",
    "TaxonomyRoleFamily", "RoleTaxonomy",
    "ValidationError", "ValidationIssue", "ValidationResult",
    "PLACEHOLDER_PATTERNS", "is_placeholder",
    "validate_constraints", "validate_narrative", "validate_profile_text_fields",
    "signal_staleness_days", "count_signals",
    "load_profile", "load_constraints", "load_signals",
    "load_opportunities", "save_opportunities", "load_sectors",
    "load_industry_graph", "load_role_taxonomy", "load_employer_types",
    "ApplicationStatus", "ApplicationTier", "Application", "ApplicationsFile",
    "load_applications", "save_applications",
    "SavedJobStatus", "SavedJob", "SavedJobsFile",
    "load_saved_jobs", "save_saved_jobs",
    "MatrixFeedbackAction", "MatrixFeedbackFile",
    "load_matrix_feedback", "save_matrix_feedback",
]

# 雇主性质轴 ID（与 data/employer_types.yaml 一致）
DEFAULT_EMPLOYER_TYPES: tuple[str, ...] = (
    "private",
    "foreign",
    "central_soe",
    "local_soe",
    "public_institution",
    "civil_service",
)


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
    is_first_degree: bool = False  # 本科为第一学历（model_post_init 自动置位）

    def model_post_init(self, __context: object) -> None:
        if self.year is not None and self.end_year is None:
            object.__setattr__(self, "end_year", self.year)
        if self.level is None and self.degree:
            inferred = infer_education_level(self.degree)
            if inferred is not None:
                object.__setattr__(self, "level", inferred)
        if self.status == EducationStatus.graduated and self.degree and "在读" in self.degree:
            object.__setattr__(self, "status", EducationStatus.enrolled)
        if self.resolved_level() == EducationLevel.bachelor and not self.is_first_degree:
            object.__setattr__(self, "is_first_degree", True)

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


class EducationSummary(BaseModel):
    """画像学历摘要 —— 资格闸门（EligibilityGate）的关键输入。

    区分「第一学历」(bachelor) 与「最高学历」层级，用于教职/头部研究院 CV 关筛选。
    `pedigree_pattern` 是面向人可读的学历轨迹摘要（如 "二本本_211硕博"）。
    `same_institution_risk` 在 match 阶段对照典型目标院校计算。
    """
    first_degree_tier: Optional[str] = None       # 本科 school_tier
    highest_degree_tier: Optional[str] = None     # 最高学历 school_tier
    highest_degree_school: Optional[str] = None
    phd_status: str = "none"  # "in_hand" | "enrolled" | "none"
    pedigree_pattern: str = ""  # e.g. "二本本_211硕博"
    same_institution_risk: bool = False  # 博士校 == 任一典型目标院校？match 时算


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


def derive_education_summary(profile: Profile) -> EducationSummary:
    """从 Profile 派生学历摘要（EligibilityGate 输入）。same_institution_risk 默认 False，
    match 阶段对照目标典型院校再置位。"""
    bachelor = profile.education_for(EducationLevel.bachelor)
    master = profile.education_for(EducationLevel.master)
    phd = profile.education_for(EducationLevel.phd)

    # 最高学历：博士 > 硕士 > 本科
    highest = phd or master or bachelor
    highest_tier = highest.school_tier if highest else None
    highest_school = highest.school if highest else None

    first_tier = bachelor.school_tier if bachelor else None

    # phd_status
    if phd is None:
        phd_status = "none"
    elif phd.status == EducationStatus.enrolled:
        phd_status = "enrolled"
    else:
        phd_status = "in_hand"

    # pedigree_pattern
    def _tag(edu: Education | None, label: str) -> str:
        if edu is None or not edu.school_tier:
            return ""
        return f"{edu.school_tier}{label}"

    parts = [p for p in (
        _tag(bachelor, "本"),
        _tag(master, "硕"),
        _tag(phd, "博"),
    ) if p]
    pedigree = "_".join(parts)

    return EducationSummary(
        first_degree_tier=first_tier,
        highest_degree_tier=highest_tier,
        highest_degree_school=highest_school,
        phd_status=phd_status,
        pedigree_pattern=pedigree,
        same_institution_risk=False,  # match 时对照 typical_companies 再算
    )


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


class EmployerPreference(BaseModel):
    """雇主性质偏好 —— 与能力方向正交；strong_preference 时 exclude 以外轴不参与矩阵。"""
    include: list[str] = Field(default_factory=lambda: list(DEFAULT_EMPLOYER_TYPES))
    exclude: list[str] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)   # 排序越前越偏好（影响 composite 加权）
    strong_preference: bool = False                     # True = 仅保留 include \ exclude


class PublicSectorGates(BaseModel):
    """体制内路径硬门槛与备考意愿（可选，analyze 阶段 L5 评分用）。

    注：就业地域/户口不属于择业方向约束，已从北斗星引擎移除（见 docs/matching-engine.md）。
    """
    accept_exam_prep_months: Optional[int] = None
    accept_non_research_roles: Optional[bool] = None
    party_member: Optional[bool] = None


class Constraints(BaseModel):
    """硬约束。就业地域(geo)/签证/户口不属于择业方向范畴，已移除——
    北斗星只确定「做什么方向 × 什么性质雇主」，不决定「在哪个城市」。
    家庭/runway/风险偏好/年龄/雇主性质 仍是硬墙。
    """
    family: Optional[str] = None
    financial_runway_months: int = Field(default=0, ge=0)
    risk_appetite: RiskAppetite = RiskAppetite.medium
    reversibility_bias: str = "high"  # high=偏好低试错成本, low=愿意 all-in
    age: Optional[int] = None          # 年龄 —— 国内学术路线对年龄敏感（青基/博新年龄线）
    notes: str = ""                    # 其他硬约束的补充说明
    employer_preference: EmployerPreference = Field(default_factory=EmployerPreference)
    public_sector_gates: PublicSectorGates = Field(default_factory=PublicSectorGates)

    def allowed_employer_ids(self) -> set[str]:
        """strong_preference=True 时仅保留 include\\exclude；否则展示全部默认轴（除 exclude）。"""
        exclude = set(self.employer_preference.exclude or [])
        universe = set(DEFAULT_EMPLOYER_TYPES) - exclude
        if self.employer_preference.strong_preference:
            include = set(self.employer_preference.include or DEFAULT_EMPLOYER_TYPES)
            return (include & universe) if include else universe
        return universe


def validate_constraints(constraints: Constraints) -> ValidationResult:
    """约束文件语义校验。"""
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

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

    pref = constraints.employer_preference
    if not pref.include:
        warnings.append(ValidationIssue(
            level="warning", field="employer_preference.include",
            message="employer_preference.include 为空 —— 机会矩阵将缺少雇主性质轴",
        ))
    elif pref.strong_preference and len(pref.include) <= 2:
        warnings.append(ValidationIssue(
            level="warning", field="employer_preference",
            message="strong_preference 且 include 仅 1-2 项 —— 矩阵会较窄，确认是否为硬偏好",
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


# L4 试错成本：低 = 走错第一步代价小；高 = 一次性投入 / 难退出
_TRIAL_COST_ALIASES: dict[str, str] = {
    "低": "低",
    "高": "高",
    "可逆": "低",      # legacy
    "commit": "高",   # legacy
}


def normalize_trial_cost(value: str) -> str:
    """Map legacy 可逆/commit labels to 低/高."""
    key = value.strip()
    if key in _TRIAL_COST_ALIASES:
        return _TRIAL_COST_ALIASES[key]
    return key


class ScoredPath(BaseModel):
    """四层评分 + 综合评级 —— Opportunity 与 MatrixCell 共用。"""
    fit: str                             # 高/中/低 — L1 比较优势
    fit_rationale: str
    match: str                           # 高/中/低 — L2 Ikigai 四圈 + 期权
    match_rationale: str
    wind: str                            # 顺风/弱顺风/逆风 — L3
    wind_rationale: str
    risk: str                            # 低/高 — L4 试错成本
    risk_rationale: str
    composite: str = "C"                 # A-F
    opens_up: list[str] = Field(default_factory=list)
    costs: list[str] = Field(default_factory=list)
    first_step: str = ""
    role_families: list[RoleFamily] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    competition_index: Optional[float] = Field(default=None, ge=0, le=1)
    # Schema 2.3 资格闸门（EligibilityGate）—— 与 domain fit 正交的 hiring fit
    eligibility: str = "pass"            # "pass" | "fail" | "review"
    eligibility_rationale: str = ""      # 闸门依据
    domain_fit: str = ""                 # 与 fit 同义，澄清语义；空时回退到 fit
    hiring_fit: str = ""                 # pass→高 / review→中 / fail→低
    blocked: bool = False                # fail 且 strong_preference 时被剔除；否则留格但标灰

    @field_validator("risk", mode="before")
    @classmethod
    def _normalize_trial_cost_scored(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_trial_cost(value)
        return value


class Opportunity(ScoredPath):
    direction: str
    # Phase 2 可选字段（Schema 2.0，向后兼容）
    industry: Optional[str] = None
    value_chain_node: Optional[str] = None
    employer_id: Optional[str] = None    # 关联 employer_axes.id（legacy primary 可为空）
    # 展示用（正交矩阵合成时填充；旧 YAML 可由 render 回退解析）
    capability_name: str = ""
    employer_label: str = ""
    summary: str = ""                    # 核心工作 / 价值链价值一句话


class CapabilityAxis(BaseModel):
    """正交轴 1：能力 / 行业方向（与雇主性质无关）。"""
    id: str
    name: str
    summary: str = ""
    industry: Optional[str] = None
    value_chain_node: Optional[str] = None
    role_families: list[RoleFamily] = Field(default_factory=list)


class EmployerAxis(BaseModel):
    """正交轴 2：雇主性质轨（与具体技能方向无关）。"""
    id: str
    name: str
    stability: str = "medium"            # low / medium / high
    ceiling: str = "medium"              # 长期天花板
    value_is_in: str = ""
    trap: str = ""
    entry_paths: list[str] = Field(default_factory=list)
    typical_orgs: list[str] = Field(default_factory=list)


class MatrixCell(ScoredPath):
    """能力方向 × 雇主性质 交叉单元 —— Schema 2.2 核心交付单元。"""
    capability_id: str
    employer_id: str
    entry_mechanism: str = ""             # 校招 / 国考 / 省考 / 教职招聘 …
    hard_gates: list[str] = Field(default_factory=list)
    skill_transfer: str = ""              # 高 / 中 / 低 — L5 技能迁移度
    skill_transfer_rationale: str = ""
    # Schema 2.3 资格闸门元数据 —— 从 role_family 同步，供 validate/render 使用
    institution_tier: str = ""            # 211 / 985 / 普通本科 / 科研院所 / 高职高专 / ""
    employer_subtype: str = ""            # university_faculty / research_institute / ...
    eligibility_rules: list[str] = Field(default_factory=list)  # 命中的 rule ids

    @property
    def direction_label(self) -> str:
        return f"{self.capability_id} × {self.employer_id}"


class OpportunityMatrix(BaseModel):
    generated_on: date
    unified_theme: str = ""
    shared_assets: list[str] = Field(default_factory=list)
    # Schema 2.2 正交矩阵
    capability_axes: list[CapabilityAxis] = Field(default_factory=list)
    employer_axes: list[EmployerAxis] = Field(default_factory=list)
    cross_matrix: list[MatrixCell] = Field(default_factory=list)
    # Schema 2.1 legacy（与 cross_matrix 可并存；primary 可由最佳 cell 同步）
    primary: list[Opportunity] = Field(default_factory=list)
    directions: list[Opportunity] = Field(default_factory=list)  # 旧字段，加载时迁移到 primary

    _RANK = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5}

    def model_post_init(self, __context: object) -> None:
        if self.directions and not self.primary:
            object.__setattr__(self, "primary", list(self.directions))

    def uses_orthogonal_matrix(self) -> bool:
        return bool(self.cross_matrix and self.capability_axes and self.employer_axes)

    def _ranked(self, items: list[Opportunity]) -> list[Opportunity]:
        return sorted(
            items,
            key=lambda o: self._RANK.get(o.composite.strip().upper(), 9),
        )

    def _ranked_cells(self, cells: list[MatrixCell]) -> list[MatrixCell]:
        return sorted(
            cells,
            key=lambda c: self._RANK.get(c.composite.strip().upper(), 9),
        )

    def ranked_cross_matrix(self) -> list[MatrixCell]:
        return self._ranked_cells(self.cross_matrix)

    def cells_for_capability(self, capability_id: str) -> list[MatrixCell]:
        return self._ranked_cells([c for c in self.cross_matrix if c.capability_id == capability_id])

    def cells_for_employer(self, employer_id: str) -> list[MatrixCell]:
        return self._ranked_cells([c for c in self.cross_matrix if c.employer_id == employer_id])

    def best_cell_per_capability(self, include_blocked: bool = False) -> list[MatrixCell]:
        seen: set[str] = set()
        out: list[MatrixCell] = []
        for cell in self.ranked_cross_matrix():
            if not include_blocked and cell.blocked:
                continue
            if cell.capability_id in seen:
                continue
            seen.add(cell.capability_id)
            out.append(cell)
        return out

    def _cell_to_opportunity(self, cell: MatrixCell, cap: CapabilityAxis | None) -> Opportunity:
        cap_name = cap.name if cap else cell.capability_id
        emp = next((e for e in self.employer_axes if e.id == cell.employer_id), None)
        emp_name = emp.name if emp else cell.employer_id
        return Opportunity(
            direction=f"{cap_name}（{emp_name}）",
            capability_name=cap_name,
            employer_label=emp_name,
            summary=(cap.summary if cap else "") or (cap.value_chain_node if cap else ""),
            industry=cap.industry if cap else None,
            value_chain_node=cap.value_chain_node if cap else None,
            employer_id=cell.employer_id,
            fit=cell.fit,
            fit_rationale=cell.fit_rationale,
            match=cell.match,
            match_rationale=cell.match_rationale,
            wind=cell.wind,
            wind_rationale=cell.wind_rationale,
            risk=cell.risk,
            risk_rationale=cell.risk_rationale,
            composite=cell.composite,
            opens_up=list(cell.opens_up),
            costs=list(cell.costs),
            first_step=cell.first_step,
            role_families=list(cell.role_families),
            skill_gaps=list(cell.skill_gaps),
            competition_index=cell.competition_index,
            eligibility=cell.eligibility,
            eligibility_rationale=cell.eligibility_rationale,
            domain_fit=cell.domain_fit,
            hiring_fit=cell.hiring_fit,
            blocked=cell.blocked,
        )

    def synthesized_primary(self, include_blocked: bool = False) -> list[Opportunity]:
        """从 cross_matrix 每能力轴取最佳雇主 cell，供 legacy 渲染/execute 使用。
        默认跳过 blocked cell（资格关 fail），与推荐语义一致。"""
        cap_map = {c.id: c for c in self.capability_axes}
        return [
            self._cell_to_opportunity(cell, cap_map.get(cell.capability_id))
            for cell in self.best_cell_per_capability(include_blocked=include_blocked)
        ]

    def blocked_cells(self) -> list[MatrixCell]:
        """资格关未过的 cell —— 仅供完整对比展示，不参与推荐。"""
        return [c for c in self.cross_matrix if c.blocked]

    def ranked_primary(self, include_blocked: bool = False) -> list[Opportunity]:
        if self.primary:
            primary = [o for o in self.primary if include_blocked or not o.blocked]
            return self._ranked(primary)
        if self.uses_orthogonal_matrix():
            return self._ranked(self.synthesized_primary(include_blocked=include_blocked))
        return []

    def ranked(self) -> list[Opportunity]:
        """向后兼容：默认返回排序列表。"""
        return self.ranked_primary()

    def all_directions(self) -> list[Opportunity]:
        return list(self.ranked_primary())


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
    # 市场供需（赛道级，与用户无关；匹配时按画像亲和度决定是否触发）
    market_saturation: str = ""       # high | medium | "" 
    saturation_note: str = ""


class Subsector(BaseModel):
    id: str
    name: str
    value_chain_nodes: list[ValueChainNode] = Field(default_factory=list)


class Industry(BaseModel):
    id: str
    name: str
    why_hot: str = ""
    domain_markers: list[str] = Field(default_factory=list)
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

    def domain_markers_for(self, industry_id: str) -> tuple[str, ...]:
        for ind in self.industries:
            if ind.id == industry_id:
                return tuple(ind.domain_markers)
        return ()


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
    capability_id: str = ""              # 正交轴 1；空则用 value_chain_node_id
    employer_type_id: str = "private"    # 正交轴 2；见 employer_types.yaml
    entry_mechanism: str = ""
    hard_gates: list[str] = Field(default_factory=list)
    skill_transfer_default: str = ""     # 高/中/低 heuristic 默认
    # Schema 2.3 资格闸门 —— 比 employer_type_id 更细的颗粒
    institution_tier: str = ""            # 211 / 985 / 普通本科 / 科研院所 / 高职高专 / ""
    employer_subtype: str = ""            # university_faculty / research_institute / ...


class RoleTaxonomy(BaseModel):
    role_families: list[TaxonomyRoleFamily] = Field(default_factory=list)


class EmployerType(BaseModel):
    id: str
    name: str
    stability: str = "medium"
    ceiling: str = "medium"
    value_is_in: str = ""
    trap: str = ""
    entry_paths: list[str] = Field(default_factory=list)
    typical_orgs: list[str] = Field(default_factory=list)


class EmployerTypesFile(BaseModel):
    employer_types: list[EmployerType] = Field(default_factory=list)

    def by_id(self) -> dict[str, EmployerType]:
        return {e.id: e for e in self.employer_types}


def load_industry_graph(path: Path) -> IndustryGraph:
    return IndustryGraph.model_validate(_load_yaml(path))


def load_role_taxonomy(path: Path) -> RoleTaxonomy:
    data = _load_yaml(path)
    public_path = path.parent / "role_taxonomy_public.yaml"
    if public_path.exists():
        extra = _load_yaml(public_path)
        data.setdefault("role_families", [])
        data["role_families"] = list(data["role_families"]) + list(
            extra.get("role_families", [])
        )
    return RoleTaxonomy.model_validate(data)


def load_employer_types(path: Path) -> EmployerTypesFile:
    return EmployerTypesFile.model_validate(_load_yaml(path))


class CrossTrackOpportunity(BaseModel):
    """交叉赛道：方法论可迁移、行业语境需补（数据驱动，非用户定制）。"""
    industry_id: str
    value_chain_node_id: str
    potential: str = "emerging"       # emerging | adjacent
    label: str
    method_note: str
    domain_gap_note: str
    opens_up: str = ""
    method_pattern: str = ""          # 空=任意；or / llm / ml 等，限制方法论画像


class CrossTrackFile(BaseModel):
    opportunities: list[CrossTrackOpportunity] = Field(default_factory=list)

    def lookup(self, industry_id: str, node_id: str) -> CrossTrackOpportunity | None:
        for o in self.opportunities:
            if o.industry_id == industry_id and o.value_chain_node_id == node_id:
                return o
        return None


def load_cross_track(path: Path) -> CrossTrackFile:
    if not path.is_file():
        return CrossTrackFile()
    return CrossTrackFile.model_validate(_load_yaml(path))


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


# ---------- 矩阵反馈（用户对机会矩阵的 remove / reorder / reset 操作）----------

class MatrixFeedbackAction(BaseModel):
    """用户在矩阵 UI 上的一次操作。

    action:
      - "remove": 用户隐藏某条 direction
      - "reorder": 用户拖拽重排，details.from_rank/to_rank 记录位移
      - "reset": 用户点击「还原」，清空全部历史（保留为终结标记）
      - "note": 用户给某条 direction 加备注，details.text 存文本（最新一条覆盖旧）
    """
    action: str                              # "remove" | "reorder" | "reset" | "note"
    direction: str = ""                      # Opportunity.direction（reset 时可为空）
    timestamp: str                           # ISO 字符串；UI/Agent 都按字符串处理
    details: dict = Field(default_factory=dict)


class MatrixFeedbackFile(BaseModel):
    updated_on: Optional[date] = None
    actions: list[MatrixFeedbackAction] = Field(default_factory=list)


def load_matrix_feedback(path: Path) -> MatrixFeedbackFile:
    if not path.exists():
        return MatrixFeedbackFile()
    return MatrixFeedbackFile.model_validate(_load_yaml(path))


def save_matrix_feedback(path: Path, data: MatrixFeedbackFile) -> None:
    """Atomic write: dump to .tmp then rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = yaml.safe_dump(data.model_dump(mode="json"), allow_unicode=True, sort_keys=False)
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
