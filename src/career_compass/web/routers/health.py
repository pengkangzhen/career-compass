"""`/api/health` — liveness probe that also pings the database."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from career_compass.web.db import get_db

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health(session: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, object]:
    try:
        await session.execute(text("SELECT 1"))
        db_status = "up"
    except Exception as exc:  # noqa: BLE001
        db_status = "down"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"database unreachable: {exc}",
        ) from exc
    return {"ok": True, "db": db_status}
