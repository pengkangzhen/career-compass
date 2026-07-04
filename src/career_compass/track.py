"""Phase 3 — 投递追踪器。

记录投递 → 面试 → offer 漏斗，为 replan 反馈闭环提供数据。
"""
from __future__ import annotations

import re
import uuid
from datetime import date
from pathlib import Path

from .schema import (
    Application,
    ApplicationStatus,
    ApplicationTier,
    ApplicationsFile,
    load_applications,
    save_applications,
)

# 漏斗阶段顺序（用于转化率）
_FUNNEL_STAGES = (
    ApplicationStatus.applied,
    ApplicationStatus.phone,
    ApplicationStatus.onsite,
    ApplicationStatus.offer,
)


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text.strip().lower())
    return s.strip("-")[:40] or "app"


def new_application_id(company: str, role: str) -> str:
    return f"{_slug(company)}-{_slug(role)}-{uuid.uuid4().hex[:6]}"


def add_application(
    path: Path,
    company: str,
    role: str,
    *,
    tier: ApplicationTier = ApplicationTier.B,
    direction: str = "",
    channel: str = "",
    applied_on: date | None = None,
    status: ApplicationStatus = ApplicationStatus.applied,
    feedback: str = "",
    notes: str = "",
) -> Application:
    """追加一条投递记录。"""
    existing = load_applications(path) if path.exists() else ApplicationsFile(updated_on=date.today())
    app = Application(
        id=new_application_id(company, role),
        company=company,
        role=role,
        tier=tier,
        direction=direction,
        channel=channel,
        applied_on=applied_on or date.today(),
        status=status,
        feedback=feedback,
        notes=notes,
    )
    existing.applications.append(app)
    existing.updated_on = date.today()
    save_applications(path, existing)
    return app


def update_application(
    path: Path,
    app_id: str,
    *,
    status: ApplicationStatus | None = None,
    feedback: str | None = None,
    notes: str | None = None,
) -> Application | None:
    """按 id 更新投递状态/反馈。"""
    if not path.exists():
        return None
    data = load_applications(path)
    for app in data.applications:
        if app.id == app_id:
            if status is not None:
                app.status = status
            if feedback is not None:
                app.feedback = feedback
            if notes is not None:
                app.notes = notes
            data.updated_on = date.today()
            save_applications(path, data)
            return app
    return None


def funnel_stats(path: Path) -> dict:
    """计算投递漏斗统计。"""
    if not path.exists():
        return {
            "total": 0,
            "by_status": {},
            "by_tier": {},
            "response_rate": 0.0,
            "interview_rate": 0.0,
            "offer_rate": 0.0,
            "ghosted_count": 0,
            "rejected_count": 0,
            "feedback_keywords": [],
        }

    data = load_applications(path)
    apps = data.applications
    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}

    for app in apps:
        by_status[app.status.value] = by_status.get(app.status.value, 0) + 1
        by_tier[app.tier.value] = by_tier.get(app.tier.value, 0) + 1

    total = len(apps)
    responded = sum(
        1 for a in apps
        if a.status not in (ApplicationStatus.applied, ApplicationStatus.ghosted)
    )
    interviewed = sum(
        1 for a in apps
        if a.status in (ApplicationStatus.phone, ApplicationStatus.onsite, ApplicationStatus.offer)
    )
    offers = sum(1 for a in apps if a.status == ApplicationStatus.offer)
    ghosted = sum(1 for a in apps if a.status == ApplicationStatus.ghosted)
    rejected = sum(1 for a in apps if a.status == ApplicationStatus.rejected)

    feedback_words: list[str] = []
    for a in apps:
        if a.feedback.strip():
            feedback_words.append(a.feedback.strip())

    return {
        "total": total,
        "by_status": by_status,
        "by_tier": by_tier,
        "response_rate": responded / total if total else 0.0,
        "interview_rate": interviewed / total if total else 0.0,
        "offer_rate": offers / total if total else 0.0,
        "ghosted_count": ghosted,
        "rejected_count": rejected,
        "feedback_keywords": feedback_words,
    }


def list_applications(path: Path) -> list[Application]:
    if not path.exists():
        return []
    return load_applications(path).applications
