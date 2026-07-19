"""SQLAlchemy 2.0 async engine, sessionmaker, and FastAPI dependency.

`DATABASE_URL` is expected to be an async SQLAlchemy URL (e.g.
`postgresql+psycopg://...`). For tests, callers override the `get_db`
dependency with an in-memory sqlite engine.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from career_compass.web.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://beidou:beidou@localhost:5432/beidou")

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def create_all() -> None:
    """Create every table registered on `Base.metadata`. Dev / test bootstrap only.

    Production uses Alembic migrations; never call this against a real database.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    await engine.dispose()


__all__ = ["Base", "engine", "async_session_maker", "get_db", "create_all", "dispose_engine"]
