"""FastAPI Users wiring: SQLAlchemy adapter, JWT bearer backend, user manager.

The spec asks for both bearer (Authorization header) and an optional cookie
transport. We register the bearer backend with FastAPIUsers so it is the default
for the standard `/auth/jwt/*` routes; cookie transport is left as a stub for
a future milestone.
"""
from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from career_compass.web.db import AsyncSession, get_db
from career_compass.web.models import User

ACCESS_TOKEN_LIFETIME = 3600
REFRESH_TOKEN_LIFETIME = 7 * 24 * 3600


def _secret() -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "SECRET_KEY is not set. Generate one with: openssl rand -hex 32"
        )
    return secret


async def get_user_db(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AsyncGenerator[SQLAlchemyUserDatabase, None]:
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = _secret()
    verification_token_secret = _secret()

    async def on_after_register(
        self, user: User, request: Request | None = None
    ) -> None:
        return None

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        return None


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl="api/auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(
        secret=_secret(),
        lifetime_seconds=ACCESS_TOKEN_LIFETIME,
    )


def get_refresh_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(
        secret=_secret(),
        lifetime_seconds=REFRESH_TOKEN_LIFETIME,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

refresh_backend = AuthenticationBackend(
    name="jwt-refresh",
    transport=bearer_transport,
    get_strategy=get_refresh_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)


__all__ = [
    "fastapi_users",
    "auth_backend",
    "refresh_backend",
    "current_active_user",
    "get_user_db",
    "get_user_manager",
    "get_jwt_strategy",
    "get_refresh_jwt_strategy",
    "UserManager",
    "ACCESS_TOKEN_LIFETIME",
    "REFRESH_TOKEN_LIFETIME",
]
