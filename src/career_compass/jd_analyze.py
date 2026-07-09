"""Phase 3 — JD 聚类与技能缺口分析（heuristic，无 LLM）。"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .registry import jd_skill_vocab
from .match import skill_match_level
from .schema import Profile, ProjectsFile, SkillGap

# 过滤噪声词
_JD_NOISE = re.compile(
    r"^(负责|要求|具备|熟悉|了解|优先|以上|相关|经验|能力|工作|团队|公司|岗位|职责|我们|您|的|和|与|等)$",
    re.I,
)


@dataclass
class JDAnalysis:
    source: str
    skill_frequency: dict[str, int] = field(default_factory=dict)
    top_skills: list[str] = field(default_factory=list)
    skill_gaps: list[SkillGap] = field(default_factory=list)
    coverage_rate: float = 0.0


def _extract_skills_from_text(text: str) -> Counter:
    """从 JD 文本提取技能词频。"""
    counts: Counter = Counter()
    lower = text.lower()
    for skill in jd_skill_vocab():
        # 整词或子串命中
        pattern = re.escape(skill.lower())
        hits = len(re.findall(pattern, lower, re.I))
        if hits:
            counts[skill] += hits

    # 额外：抓取「熟悉 X」「精通 X」模式
    for m in re.finditer(r"(?:熟悉|精通|掌握|了解|具备)\s*([^\s，,；;。.]{2,20})", text):
        token = m.group(1).strip()
        if not _JD_NOISE.match(token) and len(token) >= 2:
            counts[token] += 1

    return counts


def analyze_jd_text(
    text: str,
    profile: Profile,
    projects: ProjectsFile | None = None,
    *,
    source: str = "inline",
    top_k: int = 15,
) -> JDAnalysis:
    """单份或多份 JD 合并分析 vs 画像。"""
    counts = _extract_skills_from_text(text)
    top_skills = [s for s, _ in counts.most_common(top_k)]

    matched = 0
    gaps: list[SkillGap] = []

    for skill, freq in counts.most_common(top_k):
        level = skill_match_level(skill, profile, projects)
        if level:
            matched += 1
        else:
            priority = "high" if freq >= 2 else "medium"
            gaps.append(SkillGap(
                skill=skill,
                current_level="none",
                target_level="JD required",
                priority=priority,
                notes=f"JD 出现 {freq} 次",
            ))

    coverage = matched / len(top_skills) if top_skills else 0.0

    return JDAnalysis(
        source=source,
        skill_frequency=dict(counts.most_common(top_k)),
        top_skills=top_skills,
        skill_gaps=gaps,
        coverage_rate=round(coverage, 3),
    )


def analyze_jd_file(
    path: Path,
    profile: Profile,
    projects: ProjectsFile | None = None,
) -> JDAnalysis:
    text = path.read_text(encoding="utf-8")
    return analyze_jd_text(text, profile, projects, source=path.name)
