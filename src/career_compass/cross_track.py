"""交叉赛道识别 —— 方法论可迁移 vs 行业背景缺口 vs 赛道饱和。

设计原则（泛化，非个人定制）：
- **饱和 / 交叉机会** 写在 `data/industry_graph.yaml` 与 `data/cross_track.yaml`（全用户共享）
- **是否对当前用户生效** 由「赛道亲和度」决定，而非 OR 画像硬编码
- **扫描信号** 可动态抬高竞争感知（saturation 与 estimate_competition_index 叠加）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .schema import (
    CrossTrackFile,
    CrossTrackOpportunity,
    IndustryGraph,
    Profile,
    Signal,
    TaxonomyRoleFamily,
    load_cross_track,
)

from .registry import load_method_patterns

# 竞争信号关键词（与 match.estimate_competition_index 对齐）
_COMP_HIGH = ("内卷", "过剩", "裁员", "供过于求", "饱和", "竞争激烈", "红海", "降本裁员")
_COMP_LOW = ("缺口", "人才短缺", "需求增长", "供不应求", "蓝海", "紧缺", "扩招")

_DEFAULT_CROSS_TRACK_PATH = Path.cwd() / "data" / "cross_track.yaml"


def _pattern_markers(pattern: str) -> tuple[str, ...]:
    mp = load_method_patterns()
    spec = mp.patterns.get(pattern)
    if not spec:
        return ()
    return tuple(_normalize(m) for m in spec.markers)


def _domain_specific_skills() -> frozenset[str]:
    mp = load_method_patterns()
    skills: set[str] = set()
    for spec in mp.patterns.values():
        skills.update(_normalize(s) for s in spec.domain_specific_skills)
    return frozenset(skills)


def _affinity_thresholds() -> tuple[float, float]:
    mp = load_method_patterns()
    return mp.affinity.get("domain_min", 0.5), mp.affinity.get("match_min", 0.55)


def _cross_track_scoring() -> tuple[float, float, float]:
    mp = load_method_patterns()
    sc = mp.cross_track_scoring
    return (
        sc.get("method_weight", 0.65),
        sc.get("domain_weight", 0.35),
        sc.get("or_native_blend", 0.8),
    )


def _method_strength_from_markers(profile: Profile, markers: tuple[str, ...]) -> float:
    if not markers:
        return 0.0
    blob = _blob(profile)
    hits = sum(1 for m in markers if m in blob)
    if hits >= 4:
        return 1.0
    if hits >= 2:
        return 0.75
    if hits >= 1:
        return 0.5
    return 0.0


@dataclass
class CrossTrackAssessment:
    is_cross_track: bool = False
    or_method_strength: float = 0.0
    is_or_method_role: bool = False
    saturation: str = ""          # high / medium / ""
    saturation_note: str = ""
    potential: str = ""           # emerging / adjacent / ""
    cross_label: str = ""
    method_transfer: str = ""     # 高 / 中 / 低
    method_transfer_rationale: str = ""
    domain_gap: str = ""          # 高 / 中 / 低
    domain_gap_note: str = ""
    opens_up_note: str = ""
    costs: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    return text.strip().lower()


def _blob(profile: Profile) -> str:
    parts: list[str] = []
    parts.extend(profile.skills.core)
    parts.extend(profile.skills.adjacent)
    parts.extend(profile.skills.frontier)
    for ev in profile.strength_evidence:
        parts.append(ev.claim)
        parts.append(ev.proof)
    return _normalize(" ".join(parts))


def or_method_strength(profile: Profile) -> float:
    """画像 OR 方法论强度 0–1。"""
    return _method_strength_from_markers(profile, _pattern_markers("or"))


def llm_method_strength(profile: Profile) -> float:
    blob = _blob(profile)
    markers = _pattern_markers("llm")
    hits = sum(1 for m in markers if m in blob)
    if hits >= 2:
        return 1.0
    if hits >= 1:
        return 0.6
    return 0.0


def method_pattern_strength(profile: Profile, pattern: str) -> float:
    """按 cross_track.yaml 的 method_pattern 评估方法论画像强度。"""
    if not pattern:
        return or_method_strength(profile)
    markers = _pattern_markers(pattern)
    if markers:
        return _method_strength_from_markers(profile, markers)
    if pattern == "llm":
        return llm_method_strength(profile)
    if pattern == "or":
        return or_method_strength(profile)
    return 0.5


def is_or_method_role(role_family: TaxonomyRoleFamily) -> bool:
    """岗位是否以 OR 方法论技能为主（而非强领域门槛）。"""
    required = role_family.required_skills
    if not required:
        return False
    domain_skills = _domain_specific_skills()
    domain_hits = sum(
        1 for s in required
        if any(ds in _normalize(s) for ds in domain_skills)
    )
    if domain_hits > 0:
        return False
    or_markers = _pattern_markers("or")
    or_hits = sum(
        1 for s in required
        if any(m in _normalize(s) for m in or_markers)
    )
    return or_hits >= max(1, len(required) // 2)


def track_affinity_relevant(domain_anchor: float, raw_match_score: float) -> bool:
    """用户与该赛道是否「够相关」——饱和/交叉提示的触发门槛（全画像通用）。"""
    domain_min, match_min = _affinity_thresholds()
    return domain_anchor >= domain_min or raw_match_score >= match_min


def _signal_competition_level(
    role_family: TaxonomyRoleFamily,
    industry_name: str,
    signals: dict[str, list[Signal]],
) -> str:
    """从 scan 信号推断竞争密度（与 match.estimate_competition_index 同逻辑，避免循环导入）。"""
    text_parts: list[str] = [role_family.role, role_family.industry_id, industry_name]
    text_parts.extend(role_family.required_skills)
    for sigs in signals.values():
        for sig in sigs:
            text_parts.extend([sig.topic, sig.finding])
    blob = " ".join(text_parts).lower()
    high_hits = sum(1 for k in _COMP_HIGH if k in blob)
    low_hits = sum(1 for k in _COMP_LOW if k in blob)
    if high_hits > low_hits + 1:
        return "high"
    if low_hits > high_hits + 1:
        return "low"
    return "medium"


def resolve_market_saturation(
    role_family: TaxonomyRoleFamily,
    graph: IndustryGraph,
    signals: dict[str, list[Signal]],
    *,
    domain_anchor: float,
    raw_match_score: float,
    industry_name: str = "",
) -> CrossTrackAssessment:
    """从产业图谱节点读取赛道饱和（用户无关）；按亲和度决定是否对当前用户生效。"""
    out = CrossTrackAssessment()
    if not track_affinity_relevant(domain_anchor, raw_match_score):
        return out

    node = graph.find_node(
        role_family.industry_id,
        role_family.subsector_id,
        role_family.value_chain_node_id,
    )
    if not node or not node.market_saturation:
        # 无节点标注时，仅信号驱动
        sig_comp = _signal_competition_level(role_family, industry_name, signals)
        if sig_comp == "high":
            out.saturation = "medium"
            out.saturation_note = "扫描信号显示该赛道竞争加剧（关键词：内卷/饱和/红海）"
            out.costs.append(f"赛道饱和: {out.saturation_note}")
        return out

    out.saturation = node.market_saturation
    out.saturation_note = node.saturation_note or f"{node.name} 赛道竞争偏高"
    out.costs.append(f"赛道饱和: {out.saturation_note}")

    sig_comp = _signal_competition_level(role_family, industry_name, signals)
    if sig_comp == "high" and out.saturation == "medium":
        out.saturation = "high"
        out.saturation_note += "；扫描信号亦指向供给过剩"
        out.costs[-1] = f"赛道饱和: {out.saturation_note}"

    return out


def _method_transfer_level(method_strength: float, match_score: float) -> str:
    combined = 0.6 * method_strength + 0.4 * match_score
    if combined >= 0.7:
        return "高"
    if combined >= 0.45:
        return "中"
    return "低"


def _domain_gap_level(anchor: float) -> str:
    if anchor >= 0.75:
        return "低"
    if anchor >= 0.5:
        return "中"
    return "高"


def assess_cross_track(
    profile: Profile,
    role_family: TaxonomyRoleFamily,
    *,
    domain_anchor: float,
    raw_match_score: float,
    cross_track_file: CrossTrackFile | None = None,
) -> CrossTrackAssessment:
    """评估交叉赛道（方法论迁移 + 行业缺口）；饱和由 resolve_market_saturation 单独处理。"""
    cross_data = cross_track_file or load_cross_track(_DEFAULT_CROSS_TRACK_PATH)
    or_str = or_method_strength(profile)
    or_role = is_or_method_role(role_family)
    out = CrossTrackAssessment(
        or_method_strength=or_str,
        is_or_method_role=or_role,
    )

    cross = cross_data.lookup(
        role_family.industry_id,
        role_family.value_chain_node_id,
    )
    native_anchor = domain_anchor >= 0.75

    if not cross or native_anchor:
        return out

    pattern = cross.method_pattern or ""
    method_str = method_pattern_strength(profile, pattern)
    if pattern and method_str < 0.5:
        return out
    if not pattern and not track_affinity_relevant(domain_anchor, raw_match_score):
        return out

    out.is_cross_track = True
    out.potential = cross.potential
    out.cross_label = cross.label
    out.method_transfer = _method_transfer_level(method_str, raw_match_score)
    out.method_transfer_rationale = (
        f"方法论强度 {method_str:.0%}；{cross.method_note}"
    )
    out.domain_gap = _domain_gap_level(domain_anchor)
    out.domain_gap_note = cross.domain_gap_note
    out.opens_up_note = cross.opens_up
    out.costs.append(f"行业背景缺口（{out.domain_gap}）: {cross.domain_gap_note}")
    return out


def merge_saturation_into_assessment(
    base: CrossTrackAssessment,
    saturation: CrossTrackAssessment,
) -> CrossTrackAssessment:
    """合并 resolve_market_saturation 结果到 assess 输出。"""
    if saturation.saturation:
        base.saturation = saturation.saturation
        base.saturation_note = saturation.saturation_note
        for c in saturation.costs:
            if c not in base.costs:
                base.costs.append(c)
    if (
        base.is_or_method_role
        and base.or_method_strength >= 0.75
        and saturation.saturation
        and not base.is_cross_track
    ):
        base.method_transfer = "高"
        base.method_transfer_rationale = (
            "方法论与深耕赛道匹配，但该赛道供给饱和，建议同步关注交叉行业"
        )
        base.domain_gap = "低"
    return base


def cross_track_match_adjustment(
    raw_score: float,
    domain_anchor: float,
    assessment: CrossTrackAssessment,
) -> float:
    """交叉赛道打分：方法论可迁移时不过度惩罚行业锚点低分。"""
    method_w, domain_w, or_blend = _cross_track_scoring()
    if assessment.is_cross_track:
        return round(raw_score * (method_w + domain_w * domain_anchor), 3)
    if assessment.is_or_method_role and assessment.or_method_strength >= 0.75:
        return round(raw_score * (or_blend + (1 - or_blend) * domain_anchor), 3)
    if domain_anchor >= 0.75:
        return raw_score
    return round(raw_score * domain_anchor, 3)


def render_cross_track_section(profile: Profile, matrix) -> str:
    """为机会矩阵 Markdown 生成交叉赛道洞察（矩阵内有饱和/交叉单元才展示）。"""
    cells = getattr(matrix, "cross_matrix", []) or []
    sat_notes: list[str] = []
    cross_cells: list = []
    for cell in cells:
        for cost in getattr(cell, "costs", []) or []:
            if cost.startswith("赛道饱和:") and cost not in sat_notes:
                sat_notes.append(cost)
        if any(c.startswith("行业背景缺口") for c in (getattr(cell, "costs", []) or [])):
            cross_cells.append(cell)

    or_str = or_method_strength(profile)
    if not sat_notes and not cross_cells and or_str < 0.75:
        return ""

    lines = [
        "## 交叉赛道洞察",
        "",
        "下列判断来自 **产业图谱 + 扫描信号 + 你的画像亲和度**，不是个人定制规则：",
        "",
        "| 维度 | 含义 |",
        "|------|------|",
        "| **赛道饱和** | 该价值链节点在 `industry_graph.yaml` 标注的市场供需（全用户共享） |",
        "| **方法论可迁移** | 你的硬技能能否复用到新价值链 |",
        "| **行业语境需补** | 业务约束/术语/数据体系缺口 |",
        "",
    ]

    if sat_notes:
        lines.append("**对你相关的饱和赛道（逆风）**")
        lines.append("")
        for note in sat_notes[:5]:
            lines.append(f"- {note.removeprefix('赛道饱和: ')}")
        lines.append("")

    cross_data = load_cross_track(_DEFAULT_CROSS_TRACK_PATH)
    emerging = [o for o in cross_data.opportunities if o.potential == "emerging"]
    show_emerging = emerging and (cross_cells or sat_notes or or_str >= 0.75)
    if show_emerging:
        lines.append("**潜力交叉方向**（方法论可迁移、竞争低于饱和主赛道）：")
        lines.append("")
        limit = 6 if or_str >= 0.75 else 4
        for info in emerging[:limit]:
            lines.append(f"- **{info.label}**")
            lines.append(f"  - 可迁移：{info.method_note}")
            lines.append(f"  - 需补齐：{info.domain_gap_note}")
        lines.append("")

    if cross_cells:
        lines.append("**矩阵内交叉赛道单元**：")
        lines.append("")
        cap_map = {ax.id: ax.name for ax in getattr(matrix, "capability_axes", [])}
        for cell in cross_cells[:4]:
            name = cap_map.get(cell.capability_id, cell.capability_id)
            lines.append(
                f"- {name} · 综合 {cell.composite}"
                f" · 方法论迁移 {cell.skill_transfer or '—'}"
            )
        lines.append("")

    lines.append(
        "> 饱和标注写在产业节点上；仅当你的画像与该赛道 **亲和度 ≥ 50%** "
        "或 **技能匹配 ≥ 55%** 时才对你生效。"
    )
    lines.append("")
    return "\n".join(lines)
