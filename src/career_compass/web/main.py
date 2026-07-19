"""Uvicorn entrypoint for `uvicorn career_compass.web.main:app --reload`.

Boots the FastAPI app and verifies DB connectivity on startup so the worker
fails fast if Postgres is unreachable. When `CC_CREATE_TABLES_ON_STARTUP=1`
is set, `Base.metadata.create_all` is invoked — this is a developer escape
hatch for in-memory sqlite / first-run bootstrapping and must NEVER be enabled
in production. The authoritative path is Alembic (`alembic upgrade head`).
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from career_compass.web.app import create_app
from career_compass.web.db import Base, engine

log = logging.getLogger("career_compass.web.main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    if os.getenv("CC_CREATE_TABLES_ON_STARTUP") == "1":
        log.warning("CC_CREATE_TABLES_ON_STARTUP=1 — creating all tables via metadata")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        log.info("database connectivity verified")
    except Exception as exc:  # noqa: BLE001
        log.warning("database unreachable on startup: %s", exc)

    yield
    await engine.dispose()


app: FastAPI = create_app(lifespan=lifespan)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "career_compass.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
