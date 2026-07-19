"""SaaS data-layer endpoints — file-based, per-user isolated.

Mirrors the legacy desktop server's ``/api/*`` surface
(``src/career_compass/gui/web_server.py``) so the SPA needs no changes, but
every call is bound to the authenticated user's own data directory via
``AppApi``. This is the M2 "data layer without a DB migration" step; the
endpoints move to a DB-backed Repository in a later milestone
(docs/saas-migration-plan.md §3, §4.1).
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends

from career_compass.gui.app import AppApi
from career_compass.web.auth import current_active_user
from career_compass.web.models import User
from career_compass.web.user_data import ensure_user_data_dir

router = APIRouter(prefix="/api", tags=["data"])

UserDep = Annotated[User, Depends(current_active_user)]


def _api_for(user: User) -> AppApi:
    """Build a per-user AppApi bound to that user's isolated data dir."""
    return AppApi(data_dir=ensure_user_data_dir(user.id))


# Handlers are intentionally sync (``def``, not ``async def``): AppApi methods
# do blocking file I/O / subprocess work, so FastAPI dispatches them to its
# threadpool rather than blocking the event loop.


@router.get("/load_all")
def load_all(user: UserDep) -> dict[str, Any]:
    return _api_for(user).load_all()


@router.get("/chat_state")
def chat_state(user: UserDep) -> dict[str, Any]:
    return _api_for(user).chat_state()


@router.post("/chat_send")
def chat_send(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return _api_for(user).chat_send(str(body.get("message", "")))


@router.post("/chat_reset")
def chat_reset(user: UserDep) -> dict[str, Any]:
    return _api_for(user).chat_reset()


@router.get("/matrix_feedback")
def matrix_feedback(user: UserDep) -> dict[str, Any]:
    return _api_for(user).matrix_feedback()


@router.post("/matrix_feedback/add")
def matrix_feedback_add(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return _api_for(user).matrix_feedback_add(
        action=str(body.get("action", "")),
        direction=str(body.get("direction", "") or ""),
        details=body.get("details") or None,
        timestamp=body.get("timestamp") or None,
    )


@router.post("/jobs/add")
def jobs_add(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return _api_for(user).jobs_add(
        company=str(body.get("company", "")).strip(),
        role=str(body.get("role", "")).strip(),
        description=str(body.get("description", "")),
        location=str(body.get("location", "")).strip(),
        source=str(body.get("source", "")).strip() or "手动添加",
        linked_direction=str(body.get("linked_direction", "")).strip(),
        notes=str(body.get("notes", "")).strip(),
    )


@router.post("/jobs/update")
def jobs_update(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    job_id = str(body.get("id", "")).strip()
    if not job_id:
        return {"ok": False, "error": "missing id"}
    # AppApi.jobs_update picks the keys it understands; the rest (incl. id) is ignored.
    return _api_for(user).jobs_update(job_id, **body)


@router.post("/jobs/remove")
def jobs_remove(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    job_id = str(body.get("id", "")).strip()
    if not job_id:
        return {"ok": False, "error": "missing id"}
    return _api_for(user).jobs_remove(job_id)


@router.post("/run_command")
def run_command(
    user: UserDep,
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return _api_for(user).run_command(str(body.get("cmd", "")))
