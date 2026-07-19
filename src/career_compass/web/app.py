"""FastAPI application factory.

Usage:
    uvicorn career_compass.web.main:app --reload

CORS is open for local development. Production deployment will tighten the
allowed origins list (see docs/saas-migration-plan.md §4.3).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from career_compass.web.routers.health import router as health_router
from career_compass.web.routers.users import router as users_router

Lifespan = Callable[[FastAPI], AsyncIterator[None]]


def create_app(lifespan: Lifespan | None = None) -> FastAPI:
    app = FastAPI(
        title="北斗星 API",
        version="0.3.0",
        description="Pre-application career decision engine — SaaS layer.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:4173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(users_router)

    return app


app = create_app()
