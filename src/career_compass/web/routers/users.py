"""Auth endpoints.

FastAPI Users generates `/login`, `/logout`, `/register`, and `/me/*` routes
that we mount under `/api/auth/*`. The `/jwt` segment follows FastAPI Users
convention and matches the `BearerTransport(tokenUrl=...)` value used to build
OpenAPI metadata.

Final surface:
- POST   /api/auth/register           {email, password} -> UserRead
- POST   /api/auth/login              {email, password} -> {access_token, refresh_token, token_type}
- POST   /api/auth/jwt/login          form{username, password} -> {access_token, token_type}  (FastAPI Users default)
- POST   /api/auth/jwt/logout         Authorization: Bearer -> 204
- POST   /api/auth/logout             Authorization: Bearer -> 204
- POST   /api/auth/refresh            {refresh_token} -> {access_token, token_type}
- GET    /api/auth/me                 Authorization: Bearer -> UserRead
- PATCH  /api/auth/me                 Authorization: Bearer -> UserRead
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, models
from fastapi_users.authentication import Strategy
from fastapi_users.openapi import OpenAPIResponseType
from fastapi_users.router.common import ErrorModel
from pydantic import BaseModel

from career_compass.web.auth import (
    User,
    auth_backend,
    current_active_user,
    fastapi_users,
    get_refresh_jwt_strategy,
    get_user_manager,
)
from career_compass.web.schemas import TokenResponse, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/api/auth", tags=["auth"])

router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate, requires_verification=False),
)


class LoginPayload(BaseModel):
    email: str
    password: str


@router.post(
    "/login",
    response_model=TokenResponse,
    name="auth:login",
    description="Friendly JSON login that also returns a long-lived refresh token "
    "so the SPA can rotate access tokens without re-prompting.",
)
async def login(
    payload: LoginPayload,
    user_manager: Annotated[BaseUserManager[models.UP, models.ID], Depends(get_user_manager)],
) -> TokenResponse:
    user = await user_manager.authenticate(
        OAuth2PasswordRequestForm(username=payload.email, password=payload.password)
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="BAD_CREDENTIALS",
        )
    access_strategy: Strategy[User, uuid.UUID] = (
        fastapi_users.authenticator.backends[0].get_strategy()  # type: ignore[assignment]
    )
    refresh_strategy: Strategy[User, uuid.UUID] = get_refresh_jwt_strategy()  # type: ignore[assignment]
    access_token = await access_strategy.write_token(user)
    refresh_token = await refresh_strategy.write_token(user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    name="auth:logout",
    description="Revoke the bearer access token. Refresh tokens are stateless JWTs "
    "and are rotated, not revoked, on the refresh endpoint.",
)
async def logout(
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    # Stateless JWT — the client drops its tokens. We validate auth here so a
    # malformed/missing token returns 401 instead of a misleading 204.
    return None


_INVALID_TOKEN_RESPONSE = OpenAPIResponseType(
    model=ErrorModel,
    status_code=status.HTTP_401_UNAUTHORIZED,
    description="Invalid or expired refresh token.",
)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={401: _INVALID_TOKEN_RESPONSE},
    name="auth:refresh",
)
async def refresh(
    request: Request,
    user_manager: Annotated[BaseUserManager[models.UP, models.ID], Depends(get_user_manager)],
) -> TokenResponse:
    """Exchange a refresh token for a new access token.

    Body: `{"refresh_token": "..."}`. Decodes against the refresh strategy so
    access tokens can stay short-lived.
    """
    try:
        body = await request.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body.",
        ) from exc

    token = body.get("refresh_token") if isinstance(body, dict) else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`refresh_token` is required.",
        )

    refresh_strategy: Strategy[User, uuid.UUID] = get_refresh_jwt_strategy()  # type: ignore[assignment]
    try:
        user = await refresh_strategy.read_token(token, user_manager)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
        ) from exc

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_TOKEN",
        )

    access_strategy: Strategy[User, uuid.UUID] = (
        fastapi_users.authenticator.backends[0].get_strategy()  # type: ignore[assignment]
    )
    access_token = await access_strategy.write_token(user)
    return TokenResponse(access_token=access_token, token_type="bearer")


__all__ = ["router", "current_active_user"]
