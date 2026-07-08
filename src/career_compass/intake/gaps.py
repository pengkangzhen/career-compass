"""validate 缺口 → 建议追问（规则驱动，补充 LLM 引导）。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..schema import NARRATIVE_SECTIONS

# (关键词匹配, 建议追问)
# 设计原则：用户因迷茫才来北斗星，不应被要求预判方向/价值观/雇主偏好。
# values/employer_preference 由 intake agent 从背景信号推断，用户看完矩阵再校准。
_FOLLOWUP_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("education.bachelor", "本科"), "你的本科是在哪所学校、什么专业读的？大概哪年毕业？"),
    (("education.硕士", "education.master", "master"), "硕士阶段在哪所学校、什么方向？"),
    (("education.博士", "education.phd", "phd", "博士"), "博士的研究方向是什么？预计什么时候毕业？"),
    (("education（", "education 或 experience"), "先聊聊你的教育或工作经历——最近在哪、做什么？"),
    (("skills.core", "core（"), "你最靠得住、能教别人的核心技能有哪几项？（诚实列 3-5 个）"),
    (("strength_evidence", "证据", "proof"), "说一个你最自豪的成果——具体做了什么、有什么数字或结果？"),
    (("constraints.yaml 缺失",), "有哪些硬约束不能动？比如家庭、年龄、财务缓冲？"),
    (("narrative", "职业故事"), "用两三句话讲讲你的职业转折——怎么走到今天的？"),
    (("我想要的",), "三五年后，你希望工作日是什么样子的？"),
    (("红线",), "有什么岗位或工作方式是你绝对不接受的？"),
    (("name", "current_role", "占位"), "怎么称呼你？现在主要在做什么角色？"),
)


@dataclass(frozen=True)
class IntakeProgress:
    percent: int
    checks: list[dict[str, object]]

    def to_dict(self) -> dict:
        return {"percent": self.percent, "checks": self.checks}


def suggest_followups(errors: list[str], extra_gaps: list[str] | None = None) -> list[str]:
    """从 validate 错误与 profile.gaps 生成最多 3 条建议追问。"""
    combined = list(errors) + list(extra_gaps or [])
    hints: list[str] = []
    seen: set[str] = set()

    for gap in combined:
        lower = gap.lower()
        for keywords, question in _FOLLOWUP_RULES:
            if any(kw.lower() in lower for kw in keywords):
                if question not in seen:
                    hints.append(question)
                    seen.add(question)
                break

    if not hints and combined:
        hints.append("还有哪些背景或约束是我还没问到的？")

    return hints[:3]


def compute_intake_progress(
    *,
    has_profile: bool,
    name_ok: bool,
    role_ok: bool,
    education_ok: bool,
    skills_ok: bool,
    evidence_ok: bool,
    values_ok: bool,
    narrative_ok: bool,
) -> IntakeProgress:
    checks = [
        {"label": "基本信息", "done": name_ok and role_ok},
        {"label": "教育背景", "done": education_ok},
        {"label": "核心技能", "done": skills_ok},
        {"label": "优势证据", "done": evidence_ok},
        {"label": "价值排序", "done": values_ok},
        {"label": "职业叙事", "done": narrative_ok},
    ]
    if not has_profile:
        return IntakeProgress(percent=0, checks=checks)

    done = sum(1 for c in checks if c["done"])
    percent = round(done / len(checks) * 100) if checks else 0
    return IntakeProgress(percent=percent, checks=checks)


def narrative_sections_ok(text: str) -> bool:
    if not text.strip():
        return False
    for section in NARRATIVE_SECTIONS:
        pattern = rf"##\s*{re.escape(section)}"
        match = re.search(pattern, text)
        if not match:
            return False
        start = match.end()
        next_h = re.search(r"\n##\s", text[start:])
        body = text[start: start + next_h.start()] if next_h else text[start:]
        body = re.sub(r"^>.*$", "", body, flags=re.MULTILINE).strip()
        if len(body) < 8:
            return False
    return True
