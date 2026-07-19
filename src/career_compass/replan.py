"""Phase 3 — 反馈闭环 / replan。

基于投递漏斗与面试反馈，对机会矩阵提出修订建议。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .schema import (
    ApplicationStatus,
    Opportunity,
    OpportunityMatrix,
    load_applications,
    load_opportunities,
    save_opportunities,
)
from .track import funnel_stats

# 反馈关键词 → 方向降权 / 技能缺口提示
_FEEDBACK_GAP_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"分布式|训练|deepspeed|fsdp", "分布式训练"),
    (r"cuda|kernel|推理优化|serving", "推理优化 / Serving"),
    (r"论文|发表|顶会", "学术发表"),
    (r"学历|本科|第一学历", "学历背景"),
    (r"经验不足|年限", "工作年限"),
    (r"业务理解|行业", "行业 domain 知识"),
    (r"沟通|协作|management", "软技能 / 协作"),
)


@dataclass
class ReplanSuggestion:
    kind: str  # downgrade_direction | add_skill_gap | tier_adjust | tripwire
    target: str
    reason: str
    action: str = ""


@dataclass
class ReplanReport:
    generated_on: date
    funnel: dict
    suggestions: list[ReplanSuggestion] = field(default_factory=list)
    revised_matrix: OpportunityMatrix | None = None


def _direction_key(app_direction: str, opp_direction: str) -> bool:
    if not app_direction:
        return False
    a = app_direction.strip().lower()
    o = opp_direction.strip().lower()
    return a in o or o in a or any(w in o for w in a.split() if len(w) > 2)


def _composite_downgrade(composite: str) -> str:
    order = ["A", "B", "C", "D", "E", "F"]
    c = composite.strip().upper()
    if c not in order:
        return "D"
    idx = min(len(order) - 1, order.index(c) + 1)
    return order[idx]


def analyze_replan(
    applications_path: Path,
    opportunities_path: Path,
    *,
    ghosted_tripwire: int = 3,
    zero_interview_weeks: int = 4,
) -> ReplanReport:
    """读 tracker + 机会矩阵，产出修订建议（可选生成 revised matrix）。"""
    funnel = funnel_stats(applications_path)
    suggestions: list[ReplanSuggestion] = []

    if not opportunities_path.exists():
        suggestions.append(ReplanSuggestion(
            kind="tripwire",
            target="opportunities",
            reason="尚无机会矩阵，无法 replan",
            action="先完成 analyze 阶段",
        ))
        return ReplanReport(generated_on=date.today(), funnel=funnel, suggestions=suggestions)

    matrix = load_opportunities(opportunities_path)
    apps = load_applications(applications_path).applications if applications_path.exists() else []

    # Tripwire: 大量 ghosted
    if funnel["ghosted_count"] >= ghosted_tripwire:
        suggestions.append(ReplanSuggestion(
            kind="tripwire",
            target="全局",
            reason=f"已有 {funnel['ghosted_count']} 条 ghosted（≥{ghosted_tripwire}）",
            action="检查叙事定位 / 目标 tier 是否过高；考虑降档 B/C 或换岗位族",
        ))

    # Tripwire: 零面试响应
    if funnel["total"] >= 5 and funnel["interview_rate"] == 0:
        suggestions.append(ReplanSuggestion(
            kind="tripwire",
            target="全局",
            reason=f"已投 {funnel['total']} 条，面试率 0%",
            action="定位可能偏了：重跑 match，或换 composite 更高的方向",
        ))

    # 按方向统计拒绝/ghosted
    dir_stats: dict[str, dict[str, int]] = {}
    for app in apps:
        key = app.direction or app.role
        if key not in dir_stats:
            dir_stats[key] = {"rejected": 0, "ghosted": 0, "offer": 0, "total": 0}
        dir_stats[key]["total"] += 1
        if app.status == ApplicationStatus.rejected:
            dir_stats[key]["rejected"] += 1
        elif app.status == ApplicationStatus.ghosted:
            dir_stats[key]["ghosted"] += 1
        elif app.status == ApplicationStatus.offer:
            dir_stats[key]["offer"] += 1

    for direction, stats in dir_stats.items():
        if stats["total"] >= 2 and stats["rejected"] + stats["ghosted"] >= stats["total"]:
            suggestions.append(ReplanSuggestion(
                kind="downgrade_direction",
                target=direction,
                reason=f"该方向 {stats['total']} 投全拒/ghosted",
                action=f"将机会矩阵中「{direction}」composite 降一档",
            ))

    # 从 feedback 提取技能缺口
    for fb in funnel["feedback_keywords"]:
        for pattern, skill in _FEEDBACK_GAP_PATTERNS:
            if re.search(pattern, fb, re.I):
                suggestions.append(ReplanSuggestion(
                    kind="add_skill_gap",
                    target=skill,
                    reason=f"面试反馈提及: {fb[:80]}",
                    action=f"优先补齐「{skill}」证据或副项目",
                ))

    # A 档 tier 全挂 → 建议降档
    a_apps = [a for a in apps if a.tier.value == "A"]
    if len(a_apps) >= 2 and all(
        a.status in (ApplicationStatus.rejected, ApplicationStatus.ghosted) for a in a_apps
    ):
        suggestions.append(ReplanSuggestion(
            kind="tier_adjust",
            target="A 档公司",
            reason="A 档投递全部未进面试",
            action="主投转向 B 档，A 档保留 1-2 个冲刺位",
        ))

    return ReplanReport(
        generated_on=date.today(),
        funnel=funnel,
        suggestions=suggestions,
    )


def apply_replan_suggestions(
    matrix: OpportunityMatrix,
    suggestions: list[ReplanSuggestion],
) -> OpportunityMatrix:
    """根据建议生成修订版矩阵（确定性规则，不调用 LLM）。"""
    from .schema import SkillGap

    primary = [o.model_copy(deep=True) for o in matrix.primary]
    cross = [c.model_copy(deep=True) for c in matrix.cross_matrix]
    primary_lists = [primary]
    cell_lists = [cross]

    for sug in suggestions:
        if sug.kind != "downgrade_direction":
            continue
        for directions in primary_lists:
            for opp in directions:
                if _direction_key(sug.target, opp.direction):
                    opp.composite = _composite_downgrade(opp.composite)
                    opp.costs = list(opp.costs) + [f"[replan] {sug.reason}"]
        for cells in cell_lists:
            for cell in cells:
                label = f"{cell.capability_id}:{cell.employer_id}"
                if _direction_key(sug.target, label) or _direction_key(sug.target, cell.capability_id):
                    cell.composite = _composite_downgrade(cell.composite)
                    cell.costs = list(cell.costs) + [f"[replan] {sug.reason}"]

    for sug in suggestions:
        if sug.kind != "add_skill_gap":
            continue
        for directions in primary_lists:
            for opp in directions:
                existing = {g.skill for g in opp.skill_gaps}
                if sug.target not in existing:
                    opp.skill_gaps.append(SkillGap(
                        skill=sug.target,
                        current_level="none",
                        target_level="market feedback",
                        priority="high",
                        notes=sug.reason[:120],
                    ))
        for cells in cell_lists:
            for cell in cells:
                existing = {g.skill for g in cell.skill_gaps}
                if sug.target not in existing:
                    cell.skill_gaps.append(SkillGap(
                        skill=sug.target,
                        current_level="none",
                        target_level="market feedback",
                        priority="high",
                        notes=sug.reason[:120],
                    ))

    return OpportunityMatrix(
        generated_on=date.today(),
        unified_theme=matrix.unified_theme,
        shared_assets=list(matrix.shared_assets),
        capability_axes=list(matrix.capability_axes),
        employer_axes=list(matrix.employer_axes),
        cross_matrix=cross,
        primary=primary,
    )


def replan_and_optional_write(
    applications_path: Path,
    opportunities_path: Path,
    output_path: Path,
    *,
    write: bool = False,
) -> ReplanReport:
    report = analyze_replan(applications_path, opportunities_path)
    if opportunities_path.exists() and report.suggestions:
        revised = apply_replan_suggestions(
            load_opportunities(opportunities_path),
            report.suggestions,
        )
        report.revised_matrix = revised
        if write:
            save_opportunities(output_path, revised)
    return report
