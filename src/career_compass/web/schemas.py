"""Pydantic v2 schemas for user read/create/update and JWT tokens."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import BaseModel, Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = Field(default="bearer")


__all__ = ["UserRead", "UserCreate", "UserUpdate", "TokenResponse"]
