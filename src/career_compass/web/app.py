"""FastAPI application factory.

Usage:
    uvicorn career_compass.web.main:app --reload

CORS allowed origins are read from the ``CORS_ALLOW_ORIGINS`` env var
(comma-separated). Defaults cover local dev (Vite on 5173/4173/3000).
Production deployments set ``CORS_ALLOW_ORIGINS=https://your-app.vercel.app``.
"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from career_compass.web.routers.data import router as data_router
from career_compass.web.routers.health import router as health_router
from career_compass.web.routers.users import router as users_router

Lifespan = Callable[[FastAPI], AsyncIterator[None]]


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    # Dev defaults — Vite dev server on 5173 / 4173, plus CRA-style 3000.
    return [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
        "http://127.0.0.1:3000",
    ]


def create_app(lifespan: Lifespan | None = None) -> FastAPI:
    app = FastAPI(
        title="北斗星 API",
        version="0.3.0",
        description="Pre-application career decision engine — SaaS layer.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(data_router)

    return app


app = create_app()
