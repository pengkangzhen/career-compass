"""感兴趣岗位库 —— 从招聘软件收藏 JD，与画像/机会矩阵对照分析。

与 track（已投递）分离：saved_jobs = 观望/研究中的岗位。
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .jd_analyze import analyze_jd_text
from .jd_link import load_matrix_for_linking, resolve_linked_direction
from .schema import (
    Constraints,
    EducationLevel,
    EducationStatus,
    OpportunityMatrix,
    Profile,
    ProjectsFile,
    SavedJob,
    SavedJobStatus,
    SavedJobsFile,
    load_constraints,
    load_saved_jobs,
    save_saved_jobs,
)

# 硬性门槛关键词（启发式，命中则标为 barrier）
_BARRIER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"CCF-A|CCF A|顶会.*一作|一作.*顶会", "CCF-A 一作论文"),
    (r"博士学位|具有博士", "博士学位（在读可能不满足「具有」）"),
    (r"(\d+)\s*年.*经验", "工作年限"),
    (r"SCI\s*Q1|Nature|Science|Cell", "顶级期刊"),
)


@dataclass
class JobFitReport:
    job_id: str
    company: str
    role: str
    coverage_rate: float
    matched_skills: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)
    barriers: list[str] = field(default_factory=list)
    linked_direction: str = ""
    notes: str = ""
    summary: str = ""


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip().lower())
    return s.strip("-")[:30] or "job"


def new_job_id(company: str, role: str) -> str:
    return f"{_slug(company)}-{_slug(role)}-{uuid.uuid4().hex[:6]}"


def add_saved_job(
    path: Path,
    company: str,
    role: str,
    description: str,
    *,
    location: str = "",
    source: str = "招聘软件",
    direction: str = "",
    notes: str = "",
    linked_direction: str = "",
) -> SavedJob:
    """保存一条感兴趣岗位（同 company+role 则更新 description）。"""
    existing = load_saved_jobs(path) if path.exists() else SavedJobsFile(updated_on=date.today())
    for j in existing.jobs:
        if j.company == company and j.role == role:
            j.description = description
            j.location = location or j.location
            j.notes = notes or j.notes
            j.linked_direction = linked_direction or j.linked_direction
            j.source = source or j.source
            existing.updated_on = date.today()
            save_saved_jobs(path, existing)
            return j

    job = SavedJob(
        id=new_job_id(company, role),
        company=company,
        role=role,
        description=description,
        location=location,
        source=source,
        saved_on=date.today(),
        status=SavedJobStatus.interested,
        linked_direction=linked_direction,
        notes=notes,
    )
    existing.jobs.append(job)
    existing.updated_on = date.today()
    save_saved_jobs(path, existing)
    return job


def list_saved_jobs(path: Path) -> list[SavedJob]:
    if not path.exists():
        return []
    return load_saved_jobs(path).jobs


def get_saved_job(path: Path, job_id: str) -> SavedJob | None:
    for j in list_saved_jobs(path):
        if j.id == job_id:
            return j
    return None


def remove_saved_job(path: Path, job_id: str) -> bool:
    if not path.exists():
        return False
    data = load_saved_jobs(path)
    before = len(data.jobs)
    data.jobs = [j for j in data.jobs if j.id != job_id]
    if len(data.jobs) == before:
        return False
    data.updated_on = date.today()
    save_saved_jobs(path, data)
    return True


def _detect_barriers(
    description: str,
    profile: Profile,
    constraints: Constraints | None,
    *,
    company: str = "",
) -> list[str]:
    barriers: list[str] = []
    for pattern, label in _BARRIER_PATTERNS:
        m = re.search(pattern, description, re.I)
        if m:
            if label.startswith("工作年限") and m.lastindex:
                barriers.append(f"要求约 {m.group(1)} 年工作经验")
            else:
                barriers.append(label)

    if re.search(r"CCF-A|顶会.*一作", description, re.I):
        barriers.append("当前：无 CCF-A 一作（仅有在投论文时可能不满足「已发表」要求）")

    if re.search(r"博士学位|具有博士", description, re.I):
        phd = profile.education_for(EducationLevel.phd)
        if phd and phd.status == EducationStatus.enrolled:
            grad = phd.graduation_hint() or "毕业"
            barriers.append(f"当前：博士在读（{grad}）——「具有博士学位」可能需毕业后再投")
        elif profile.current_role and "在读" in (profile.current_role + "博士"):
            barriers.append("当前：博士在读——「具有博士学位」可能需毕业后再投")

    bachelor = profile.education_for(EducationLevel.bachelor)
    first_tier = (bachelor.school_tier if bachelor else None) or ""
    if not first_tier and constraints and constraints.notes and "二本" in constraints.notes:
        first_tier = "二本"
    if first_tier and "二本" in first_tier:
        head_tier = f"{company} {description}"
        if re.search(r"字节|ByteDance|腾讯|华为.*研究院|达摩院|AI Lab", head_tier, re.I):
            barriers.append("结构性：第一学历二本，头部研究院/研究岗简历关可能偏严（非 JD 明文）")

    return list(dict.fromkeys(barriers))


def analyze_saved_job(
    job: SavedJob,
    profile: Profile,
    projects: ProjectsFile | None = None,
    constraints: Constraints | None = None,
    *,
    matrix: OpportunityMatrix | None = None,
    data_dir: Path | None = None,
) -> JobFitReport:
    """JD vs 画像：覆盖率、缺口、硬门槛、关联机会矩阵方向。"""
    if matrix is None and data_dir is not None:
        matrix = load_matrix_for_linking(data_dir)
    jd = analyze_jd_text(
        job.description,
        profile,
        projects,
        source=f"{job.company}/{job.role}",
    )

    matched: list[str] = []
    for skill in jd.top_skills:
        if skill not in [g.skill for g in jd.skill_gaps]:
            matched.append(skill)

    barriers = _detect_barriers(job.description, profile, constraints, company=job.company)

    linked = job.linked_direction
    if not linked:
        blob = f"{job.company} {job.role} {job.description[:800]}"
        linked = resolve_linked_direction(blob, matrix=matrix, data_dir=data_dir)

    gap_names = [g.skill for g in jd.skill_gaps[:8]]
    summary_parts = [
        f"技能覆盖率约 {jd.coverage_rate:.0%}",
        f"匹配: {', '.join(matched[:6]) or '—'}",
    ]
    if barriers:
        summary_parts.append(f"硬门槛/风险: {'; '.join(barriers[:3])}")
    if gap_names:
        summary_parts.append(f"缺口: {', '.join(gap_names[:5])}")

    return JobFitReport(
        job_id=job.id,
        company=job.company,
        role=job.role,
        coverage_rate=jd.coverage_rate,
        matched_skills=matched,
        skill_gaps=gap_names,
        barriers=barriers,
        linked_direction=linked,
        notes=job.notes,
        summary=" · ".join(summary_parts),
    )
