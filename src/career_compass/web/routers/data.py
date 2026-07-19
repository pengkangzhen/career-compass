"""SaaS data-layer endpoints — DB-backed, per-user isolated (M3).

Every call is bound to the authenticated user's own row set via
``Repository(session, user.id)``. The HTTP surface stays identical to the
M2 file-based version so the SPA needs no changes.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from career_compass.web.auth import current_active_user
from career_compass.web.db import get_db
from career_compass.web.models import User
from career_compass.web.repository import Repository

router = APIRouter(prefix="/api", tags=["data"])

UserDep = Annotated[User, Depends(current_active_user)]
SessionDep = Annotated[AsyncSession, Depends(get_db)]


def _repo_for(user: User, session: AsyncSession) -> Repository:
    return Repository(session, user.id)


@router.get("/load_all")
async def load_all(user: UserDep, session: SessionDep) -> dict[str, Any]:
    return await _repo_for(user, session).load_all()


@router.get("/chat_state")
async def chat_state(user: UserDep, session: SessionDep) -> dict[str, Any]:
    return await _repo_for(user, session).chat_state()


@router.post("/chat_send")
async def chat_send(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await _repo_for(user, session).chat_send(str(body.get("message", "")))


@router.post("/chat_reset")
async def chat_reset(user: UserDep, session: SessionDep) -> dict[str, Any]:
    return await _repo_for(user, session).chat_reset()


@router.get("/matrix_feedback")
async def matrix_feedback(user: UserDep, session: SessionDep) -> dict[str, Any]:
    return await _repo_for(user, session).matrix_feedback()


@router.post("/matrix_feedback/add")
async def matrix_feedback_add(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await _repo_for(user, session).matrix_feedback_add(
        action=str(body.get("action", "")),
        direction=str(body.get("direction", "") or ""),
        details=body.get("details") or None,
        timestamp=body.get("timestamp") or None,
    )


@router.post("/jobs/add")
async def jobs_add(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await _repo_for(user, session).jobs_add(
        company=str(body.get("company", "")).strip(),
        role=str(body.get("role", "")).strip(),
        description=str(body.get("description", "")),
        location=str(body.get("location", "")).strip(),
        source=str(body.get("source", "")).strip() or "手动添加",
        linked_direction=str(body.get("linked_direction", "")).strip(),
        notes=str(body.get("notes", "")).strip(),
    )


@router.post("/jobs/update")
async def jobs_update(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    job_id = str(body.get("id", "")).strip()
    if not job_id:
        return {"ok": False, "error": "missing id"}
    return await _repo_for(user, session).jobs_update(job_id, **body)


@router.post("/jobs/remove")
async def jobs_remove(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    job_id = str(body.get("id", "")).strip()
    if not job_id:
        return {"ok": False, "error": "missing id"}
    return await _repo_for(user, session).jobs_remove(job_id)


@router.post("/run_command")
async def run_command(
    user: UserDep,
    session: SessionDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await _repo_for(user, session).run_command(str(body.get("cmd", "")))
