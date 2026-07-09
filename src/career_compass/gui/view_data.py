"""Structured view payloads for the modern SPA (JSON API)."""
from __future__ import annotations

from pathlib import Path

from career_compass.jobs import analyze_saved_job
from career_compass.pipeline import run_validation
from career_compass.schema import (
    EducationStatus,
    load_constraints,
    load_opportunities,
    load_profile,
    load_projects,
    load_saved_jobs,
    load_sectors,
    load_signals,
)


def build_profile_view(data_dir: Path) -> dict:
    profile_path = data_dir / "profile.yaml"
    if not profile_path.exists():
        return {
            "empty": True,
            "message": "尚无个人画像。请在「对话」开始「认识自己」，或在编码助手中启动 intake。",
        }

    profile = load_profile(profile_path)
    errors, warnings = run_validation(data_dir)

    education = []
    for edu in profile.sorted_education():
        years: list[str] = []
        if edu.start_year:
            years.append(str(edu.start_year))
        grad = edu.graduation_hint()
        if grad:
            years.append(grad)
        notes: list[str] = []
        if edu.status == EducationStatus.enrolled:
            notes.append("在读")
        if edu.ranking_or_gpa:
            notes.append(edu.ranking_or_gpa)
        if edu.honors:
            notes.append(edu.honors)
        if edu.thesis_or_focus:
            notes.append(edu.thesis_or_focus)
        if edu.advisor:
            notes.append(f"导师: {edu.advisor}")
        education.append(
            {
                "level": edu.level_label(),
                "school": edu.school,
                "school_tier": edu.school_tier,
                "major": edu.major,
                "department": edu.department,
                "time": "–".join(years) if years else "—",
                "notes": " · ".join(notes) if notes else "—",
            }
        )

    constraints = None
    cp = data_dir / "constraints.yaml"
    if cp.exists():
        c = load_constraints(cp)
        constraints = {
            "age": c.age,
            "risk_appetite": c.risk_appetite.value,
            "notes": c.notes,
        }

    narrative_path = data_dir / "narrative.md"
    narrative_md = narrative_path.read_text(encoding="utf-8") if narrative_path.exists() else None

    return {
        "empty": False,
        "title": profile.current_role or "个人画像",
        "validation": {"errors": errors, "warnings": warnings},
        "education": education,
        "core_skills": list(profile.skills.core),
        "adjacent_skills": list(profile.skills.adjacent[:8]),
        "evidence": [
            {"claim": ev.claim, "proof": ev.proof} for ev in profile.strength_evidence
        ],
        "constraints": constraints,
        "narrative_md": narrative_md,
    }


def build_trends_view(data_dir: Path) -> dict:
    signals_dir = data_dir / "signals"
    sectors_path = data_dir / "sectors.yaml"
    domain_labels = {"trends": "行业趋势", "market": "市场供需", "landscape": "产业格局"}

    signals = load_signals(signals_dir)
    signal_groups = []
    for domain, sigs in signals.items():
        signal_groups.append(
            {
                "domain": domain,
                "label": domain_labels.get(domain, domain),
                "items": [
                    {
                        "topic": s.topic,
                        "finding": s.finding,
                        "confidence": s.confidence,
                        "retrieved_on": str(s.retrieved_on),
                        "source": s.source,
                        "source_url": s.source_url,
                    }
                    for s in sigs
                ],
            }
        )

    sectors = []
    if sectors_path.exists():
        for sec in load_sectors(sectors_path)[:9]:
            sectors.append(
                {
                    "name": sec.name,
                    "why_hot": sec.why_hot,
                    "value_is_in": sec.value_is_in,
                    "trap": sec.trap,
                }
            )

    empty = not signal_groups and not sectors
    return {
        "empty": empty,
        "message": "「探索世界」暂无趋势数据。完成认识自己后，开始采集行业信号。" if empty else None,
        "signals": signal_groups,
        "sectors": sectors,
    }


def build_jobs_view(data_dir: Path) -> dict:
    jobs_path = data_dir / "saved_jobs.yaml"
    if not jobs_path.exists():
        return {
            "empty": True,
            "message": "尚无收藏岗位。",
            "hint": "收藏 JD 可帮助北斗星了解你的意向（不阻塞机会矩阵）",
            "jobs": [],
        }

    data = load_saved_jobs(jobs_path)
    profile_path = data_dir / "profile.yaml"
    profile = load_profile(profile_path) if profile_path.exists() else None
    projects_path = data_dir / "projects.yaml"
    projects = load_projects(projects_path) if projects_path.exists() else None
    constraints = None
    cp = data_dir / "constraints.yaml"
    if cp.exists():
        constraints = load_constraints(cp)

    jobs = []
    for job in data.jobs:
        item: dict = {
            "company": job.company,
            "role": job.role,
            "location": job.location,
            "saved_on": str(job.saved_on),
            "status": job.status.value,
            "notes": job.notes,
        }
        if profile:
            report = analyze_saved_job(job, profile, projects, constraints, data_dir=data_dir)
            item["match"] = {
                "summary": report.summary,
                "linked_direction": report.linked_direction,
                "barriers": list(report.barriers),
            }
        jobs.append(item)

    return {"empty": False, "count": len(jobs), "jobs": jobs}


def build_matrix_view(data_dir: Path) -> dict:
    md_path = data_dir / "opportunities.md"
    if md_path.exists():
        return {
            "empty": False,
            "format": "markdown",
            "content": md_path.read_text(encoding="utf-8"),
        }

    yaml_path = data_dir / "opportunities.yaml"
    if yaml_path.exists():
        matrix = load_opportunities(yaml_path)

        def _rows(opps: list, *, synergy: bool = False) -> list[dict]:
            from career_compass.render import _resolve_opportunity_display

            cap_by_name = {c.name: c for c in matrix.capability_axes}
            emp_by_id = {e.id: e.name for e in matrix.employer_axes}
            rows = []
            for i, o in enumerate(opps, 1):
                disp = _resolve_opportunity_display(
                    o, cap_by_name=cap_by_name, emp_by_id=emp_by_id,
                )
                row = {
                    "rank": i,
                    "direction": o.direction,
                    "positioning": disp["positioning"],
                    "track": disp["track"],
                    "summary": disp["summary"],
                    "employer": disp["emp_label"],
                    "fit": o.fit,
                    "match": o.match,
                    "wind": o.wind,
                    "risk": o.risk,
                    "composite": o.composite,
                }
                if synergy:
                    row["synergy"] = "；".join(o.synergizes_with) if o.synergizes_with else "—"
                rows.append(row)
            return rows

        return {
            "empty": False,
            "format": "yaml_summary",
            "unified_theme": matrix.unified_theme,
            "shared_assets": list(matrix.shared_assets),
            "primary": _rows(matrix.ranked_primary()),
            "side": _rows(matrix.ranked_side(), synergy=True),
            "hint": "YAML 摘要 · 运行「渲染矩阵」生成完整 Markdown",
        }

    return {
        "empty": True,
        "message": "「做出决策」尚无机会矩阵。",
        "hint": "完成探索世界后运行 analyze，生成 opportunities.yaml 再渲染矩阵。",
    }


def build_execution_view(data_dir: Path) -> dict:
    path = data_dir / "execution_pack.md"
    if not path.is_file():
        return {
            "empty": True,
            "message": "「开始行动」尚无执行包。",
            "hint": "从机会矩阵选定方向后，点击「生成执行包」或运行 render-execution",
        }
    return {
        "empty": False,
        "format": "markdown",
        "content": path.read_text(encoding="utf-8"),
    }


def build_track_view(data_dir: Path) -> dict:
    from career_compass.track import funnel_stats, list_applications

    apps_path = data_dir / "applications.yaml"
    funnel = funnel_stats(apps_path)
    apps = list_applications(apps_path)

    if not apps:
        return {
            "empty": True,
            "message": "「持续追踪」尚无投递记录。",
            "hint": 'CLI: career-compass track add "公司" "岗位"',
            "funnel": funnel,
            "applications": [],
        }

    return {
        "empty": False,
        "funnel": funnel,
        "applications": [
            {
                "id": a.id,
                "company": a.company,
                "role": a.role,
                "tier": a.tier.value,
                "direction": a.direction,
                "status": a.status.value,
                "applied_on": str(a.applied_on),
                "feedback": a.feedback,
                "notes": a.notes,
            }
            for a in apps
        ],
    }


def build_all_views(data_dir: Path) -> dict:
    return {
        "profile": build_profile_view(data_dir),
        "trends": build_trends_view(data_dir),
        "jobs": build_jobs_view(data_dir),
        "matrix": build_matrix_view(data_dir),
        "execution": build_execution_view(data_dir),
        "track": build_track_view(data_dir),
    }
