"""End-to-end tests for the SaaS auth layer.

Uses httpx + ASGITransport to run the FastAPI app in-process against an
in-memory sqlite database, so we don't need Postgres or uvicorn here.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from career_compass.web.db import Base, get_db
from career_compass.web.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session_maker(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def override_get_db(test_session_maker):
    async def _get_test_db() -> AsyncIterator:
        async with test_session_maker() as session:
            yield session

    return _get_test_db


@pytest_asyncio.fixture
async def client(override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    res = await client.get("/api/health")
    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["db"] == "up"


@pytest.mark.asyncio
async def test_register_login_me_flow(client: AsyncClient):
    email = "alice@example.com"
    password = "alice-secret-123"

    reg = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["email"] == email

    login = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert token

    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient):
    payload = {"email": "bob@example.com", "password": "bob-secret-123"}
    first = await client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_me_without_token_401(client: AsyncClient):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_json_login_returns_refresh_token(client: AsyncClient):
    email = "carol@example.com"
    password = "carol-secret-123"
    reg = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert reg.status_code == 201, reg.text

    login = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email

    refresh = await client.post(
        "/api/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert refresh.status_code == 200, refresh.text
    assert refresh.json()["access_token"]


@pytest.mark.asyncio
async def test_json_login_bad_password_401(client: AsyncClient):
    email = "dave@example.com"
    password = "dave-secret-123"
    await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    res = await client.post(
        "/api/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert res.status_code == 401
