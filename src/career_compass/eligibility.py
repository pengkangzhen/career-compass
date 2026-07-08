"""Schema 2.3 资格闸门（EligibilityGate）—— 招聘资格（hiring fit）确定性引擎。

与「domain fit」（研究/能力对齐，由 match 引擎的四层评分衡量）正交：
- domain fit 高 ≠ hiring fit 通过。一个研究强对齐的候选人仍可能被第一学历门槛 CV screen 掉。
- 本引擎在 composite 评分**之前**运行，输出 EligibilityResult：
  - fail  → composite 不得 > composite_cap（通常 D），cell.blocked=True
  - review → composite 不得 > B（保留但降权）
  - pass  → 不干预

规则取最严：fail > review > pass。规则来源 `data/hiring_eligibility_rules.yaml`，
不杜撰 URL（sources 用「用户案例」「待补: ...」占位）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schema import (
    Constraints,
    EducationSummary,
    Profile,
    TaxonomyRoleFamily,
    derive_education_summary,
)

__all__ = [
    "EligibilityResult",
    "EligibilityRule",
    "EligibilityRulesFile",
    "evaluate_eligibility",
    "load_eligibility_rules",
    "institution_tier_rank",
    "composite_to_hiring_fit",
]

# 院校层级排序（越大越精英）—— institution_tier_min 比较用
_TIER_RANK: dict[str, int] = {
    "985": 6,
    "211": 5,
    "双一流": 5,
    "一本": 4,
    "二本": 3,
    "三本": 2,
    "普通本科": 3,
    "应用型本科": 2,
    "高职高专": 1,
    "科研院所": 3,
    "": 0,
}


def institution_tier_rank(tier: str | None) -> int:
    if not tier:
        return 0
    return _TIER_RANK.get(tier.strip(), 0)


def composite_to_hiring_fit(status: str) -> str:
    """eligibility status → hiring_fit 标签（pass→高 / review→中 / fail→低）。"""
    return {"pass": "高", "review": "中", "fail": "低"}.get(status, "高")


@dataclass
class EligibilityResult:
    status: str  # "pass" | "fail" | "review"
    rationale: str
    composite_cap: str | None  # "D" when fail, "B" when review, None when pass
    blocked: bool  # True when fail
    rules_matched: list[str] = field(default_factory=list)

    @property
    def hiring_fit(self) -> str:
        return composite_to_hiring_fit(self.status)


# ---------- 规则模型 ----------


@dataclass
class EligibilityRule:
    id: str
    applies_to: dict[str, Any]
    conditions: dict[str, Any]
    effect: str  # "block" | "warn" | "cap_composite_at"
    composite_cap: str | None
    rationale: str
    sources: list[str]

    @staticmethod
    def from_raw(raw: dict) -> "EligibilityRule":
        return EligibilityRule(
            id=raw["id"],
            applies_to=raw.get("applies_to", {}) or {},
            conditions=raw.get("conditions", {}) or {},
            effect=raw.get("effect", "warn"),
            composite_cap=raw.get("composite_cap"),
            rationale=raw.get("rationale", ""),
            sources=list(raw.get("sources", []) or []),
        )


@dataclass
class EligibilityRulesFile:
    rules: list[EligibilityRule]

    @staticmethod
    def from_raw(raw: dict) -> "EligibilityRulesFile":
        return EligibilityRulesFile(
            rules=[EligibilityRule.from_raw(r) for r in raw.get("rules", []) or []],
        )


def load_eligibility_rules(path: Path) -> EligibilityRulesFile:
    with path.open("r", encoding="utf-8") as f:
        return EligibilityRulesFile.from_raw(yaml.safe_load(f) or {})


# ---------- 适用性判定 ----------


def _rule_applies(
    rule: EligibilityRule,
    role_family: TaxonomyRoleFamily,
    institution_tier: str,
) -> bool:
    """applies_to 多键 AND（所有出现的键都要命中），单键内列表 OR。"""
    ap = rule.applies_to
    if not ap:
        return True  # 无约束 → 通用

    # employer_subtypes：role.employer_subtype 命中列表
    if "employer_subtypes" in ap:
        subtypes = ap["employer_subtypes"] or []
        if role_family.employer_subtype not in subtypes:
            return False

    # institution_tier_min：目标 tier rank >= 规则 tier rank
    if "institution_tier_min" in ap:
        rule_rank = institution_tier_rank(ap["institution_tier_min"])
        target_rank = institution_tier_rank(institution_tier)
        if target_rank < rule_rank:
            return False

    # institution_tiers：目标 tier 命中列表
    if "institution_tiers" in ap:
        tiers = ap["institution_tiers"] or []
        if institution_tier not in tiers:
            return False

    # role_keywords：role.role 命中任一关键词
    if "role_keywords" in ap:
        keywords = ap["role_keywords"] or []
        role_text = role_family.role or ""
        if not any(kw.lower() in role_text.lower() for kw in keywords):
            return False

    return True


# ---------- 条件评估 ----------

# 单条件裁决：("deny" | "uncertain" | "allow")
_VERDICT_RANK = {"allow": 0, "uncertain": 1, "deny": 2}


def _eval_bachelor_tier(
    cond: dict,
    edu_summary: EducationSummary,
) -> str:
    first = (edu_summary.first_degree_tier or "").strip()
    allow = cond.get("allow", []) or []
    deny = cond.get("deny", []) or []
    uncertain = cond.get("uncertain", []) or []
    if first in deny:
        return "deny"
    if first in uncertain:
        return "uncertain"
    if first in allow:
        return "allow"
    # 未分类 → 谨慎视为 uncertain（不轻易放行，也不轻易 hard fail）
    return "uncertain" if (allow or deny or uncertain) else "allow"


def _eval_phd_in_hand_required(
    cond: dict,
    edu_summary: EducationSummary,
) -> str:
    if not cond.get("phd_in_hand_required"):
        return "allow"
    status = edu_summary.phd_status
    if status == "in_hand":
        return "allow"
    if status == "enrolled":
        return "uncertain"  # 将毕业，按 review
    return "deny"  # 无博士 → 不满足「已取得博士学位」


def _eval_age_max(
    cond: dict,
    constraints: Constraints,
) -> str:
    age_max = cond.get("age_max")
    if age_max is None:
        return "allow"
    age = constraints.age
    if age is None:
        # 年龄未声明 → 不阻断（无法判定）；分析阶段可人工补
        return "allow"
    if age > int(age_max):
        return "deny"
    return "allow"


def _eval_same_institution(
    cond: dict,
    edu_summary: EducationSummary,
) -> str:
    if not cond.get("same_institution"):
        return "allow"
    return "uncertain" if edu_summary.same_institution_risk else "allow"


def _eval_conditions(
    rule: EligibilityRule,
    edu_summary: EducationSummary,
    constraints: Constraints,
) -> str:
    """合并所有条件，取最严（deny > uncertain > allow）。"""
    conds = rule.conditions
    verdicts: list[str] = []
    if "bachelor_tier" in conds:
        verdicts.append(_eval_bachelor_tier(conds["bachelor_tier"], edu_summary))
    if conds.get("phd_in_hand_required"):
        verdicts.append(_eval_phd_in_hand_required(conds, edu_summary))
    if conds.get("age_max") is not None:
        verdicts.append(_eval_age_max(conds, constraints))
    if conds.get("same_institution"):
        verdicts.append(_eval_same_institution(conds, edu_summary))
    if not verdicts:
        return "allow"
    return max(verdicts, key=lambda v: _VERDICT_RANK[v])


# ---------- 裁决映射 ----------

# status 严格度：fail > review > pass
_STATUS_RANK = {"pass": 0, "review": 1, "fail": 2}


def _verdict_to_status(verdict: str, effect: str) -> str:
    """verdict (deny/uncertain/allow) + effect (block/warn) → status (pass/review/fail)。"""
    if verdict == "allow":
        return "pass"
    if effect == "block":
        # deny → fail；uncertain → review
        return "fail" if verdict == "deny" else "review"
    # warn / cap_composite_at：不阻断，仅 review
    return "review"


def _status_cap(status: str, rule: EligibilityRule) -> str | None:
    if status == "fail":
        return rule.composite_cap or "D"
    if status == "review":
        # warn 规则的 composite_cap 一般为 B；block 规则 uncertain 走 review 也封 B
        return rule.composite_cap if rule.effect != "block" else "B"
    return None


# ---------- 主入口 ----------


def evaluate_eligibility(
    role_family: TaxonomyRoleFamily,
    profile: Profile,
    constraints: Constraints,
    *,
    institution_tier: str = "",
    typical_companies: list[str] | None = None,
    rules: list[EligibilityRule] | None = None,
    rules_path: Path | None = None,
) -> EligibilityResult:
    """对单个 (role_family, profile, target institution_tier) 运行资格闸门。

    institution_tier 来自 role_family.institution_tier 或调用方显式传入（如 cell）。
    typical_companies 用于 same_institution_risk 复算（博士校 == 典型目标院校）。
    rules 未提供时从 rules_path 加载；二者皆无 → 返回 pass（无规则即放行）。
    """
    if rules is None:
        if rules_path is None:
            return EligibilityResult(
                status="pass",
                rationale="未加载资格规则，默认放行",
                composite_cap=None,
                blocked=False,
                rules_matched=[],
            )
        rules = load_eligibility_rules(rules_path).rules

    edu_summary = derive_education_summary(profile)
    # 复算 same_institution_risk：博士校 == 任一典型目标院校
    if typical_companies and edu_summary.highest_degree_school:
        schools = {s.strip() for s in typical_companies}
        if edu_summary.highest_degree_school.strip() in schools:
            edu_summary = edu_summary.model_copy(update={"same_institution_risk": True})

    tier = institution_tier or role_family.institution_tier

    best_status = "pass"
    best_rule: EligibilityRule | None = None
    matched: list[str] = []

    for rule in rules:
        if not _rule_applies(rule, role_family, tier):
            continue
        verdict = _eval_conditions(rule, edu_summary, constraints)
        status = _verdict_to_status(verdict, rule.effect)
        if status != "pass":
            matched.append(rule.id)
        if _STATUS_RANK[status] > _STATUS_RANK[best_status]:
            best_status = status
            best_rule = rule
        elif _STATUS_RANK[status] == _STATUS_RANK[best_status] and best_rule is None and status != "pass":
            best_rule = rule

    if best_status == "pass":
        return EligibilityResult(
            status="pass",
            rationale="资格闸门：无规则阻断",
            composite_cap=None,
            blocked=False,
            rules_matched=matched,
        )

    cap = _status_cap(best_status, best_rule)  # type: ignore[arg-type]
    rationale = best_rule.rationale if best_rule else "资格闸门触发"
    return EligibilityResult(
        status=best_status,
        rationale=rationale,
        composite_cap=cap,
        blocked=(best_status == "fail"),
        rules_matched=matched,
    )


def apply_composite_cap(composite: str, cap: str | None) -> str:
    """若 cap 非空且 composite 优于 cap（字母更小），则下调到 cap。"""
    if cap is None:
        return composite
    order = ["A", "B", "C", "D", "E", "F"]
    c = composite.strip().upper()
    k = cap.strip().upper()
    if c not in order or k not in order:
        return composite
    if order.index(c) < order.index(k):
        return k
    return composite
