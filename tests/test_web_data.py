"""End-to-end tests for the SaaS /api/* data endpoints (M3).

Runs the full FastAPI app against in-memory sqlite, registers a user, logs
in, and exercises every data endpoint to verify:
- Auth is enforced (401 without token)
- User isolation holds (A cannot read B's data)
- Round-trips through Repository + tmpdir + DB work
- Response shapes match what the SPA expects
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


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def override_get_db(session_maker):
    async def _get_test_db() -> AsyncIterator:
        async with session_maker() as session:
            yield session

    return _get_test_db


@pytest_asyncio.fixture
async def client(override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _register_and_login(client: AsyncClient, email: str, password: str) -> str:
    reg = await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.mark.asyncio
async def test_load_all_requires_auth(client: AsyncClient):
    res = await client.get("/api/load_all")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_load_all_empty_user(client: AsyncClient):
    token = await _register_and_login(client, "load@x.com", "secret-12345")
    res = await client.get(
        "/api/load_all", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "views" in data
    assert "journey" in data
    assert data["intake_complete"] is False


@pytest.mark.asyncio
async def test_jobs_full_lifecycle(client: AsyncClient):
    token = await _register_and_login(client, "jobs@x.com", "secret-12345")
    h = {"Authorization": f"Bearer {token}"}

    # Add
    add = await client.post(
        "/api/jobs/add",
        json={
            "company": "Acme",
            "role": "Engineer",
            "description": "Build stuff",
            "location": "Beijing",
        },
        headers=h,
    )
    assert add.status_code == 200, add.text
    assert add.json()["ok"] is True
    job_id = add.json()["job"]["id"]
    assert add.json()["job"]["status"] == "interested"

    # Load via load_all
    load = await client.get("/api/load_all", headers=h)
    jobs_view = load.json()["views"]["jobs"]
    assert jobs_view.get("empty") is False
    assert jobs_view["count"] == 1
    assert jobs_view["jobs"][0]["id"] == job_id

    # Update
    upd = await client.post(
        "/api/jobs/update",
        json={"id": job_id, "status": "ready", "notes": "referral"},
        headers=h,
    )
    assert upd.status_code == 200
    assert upd.json()["job"]["status"] == "ready"
    assert upd.json()["job"]["notes"] == "referral"

    # Remove
    rm = await client.post(
        "/api/jobs/remove", json={"id": job_id}, headers=h
    )
    assert rm.status_code == 200
    assert rm.json()["ok"] is True

    # Confirm gone
    load2 = await client.get("/api/load_all", headers=h)
    assert load2.json()["views"]["jobs"].get("empty") is True


@pytest.mark.asyncio
async def test_jobs_cross_user_isolation(client: AsyncClient):
    token_a = await _register_and_login(client, "a@x.com", "aaaaa-12345")
    token_b = await _register_and_login(client, "b@x.com", "bbbbb-12345")
    h_a = {"Authorization": f"Bearer {token_a}"}
    h_b = {"Authorization": f"Bearer {token_b}"}

    # A adds a job
    add = await client.post(
        "/api/jobs/add",
        json={"company": "Acorp", "role": "R", "description": "secret"},
        headers=h_a,
    )
    a_job_id = add.json()["job"]["id"]

    # B cannot see it
    load_b = await client.get("/api/load_all", headers=h_b)
    assert load_b.json()["views"]["jobs"].get("empty") is True

    # B cannot update it
    upd_b = await client.post(
        "/api/jobs/update",
        json={"id": a_job_id, "notes": "takeover"},
        headers=h_b,
    )
    assert upd_b.json()["ok"] is False

    # B cannot delete it
    rm_b = await client.post(
        "/api/jobs/remove", json={"id": a_job_id}, headers=h_b
    )
    assert rm_b.json()["ok"] is False


@pytest.mark.asyncio
async def test_matrix_feedback_endpoint(client: AsyncClient):
    token = await _register_and_login(client, "mf@x.com", "secret-12345")
    h = {"Authorization": f"Bearer {token}"}

    # Empty initially
    res = await client.get("/api/matrix_feedback", headers=h)
    assert res.status_code == 200
    assert res.json()["actions"] == []

    # Add a remove action
    add = await client.post(
        "/api/matrix_feedback/add",
        json={"action": "remove", "direction": "AI · private"},
        headers=h,
    )
    assert add.status_code == 200
    assert add.json()["ok"] is True

    # List should show it
    res2 = await client.get("/api/matrix_feedback", headers=h)
    actions = res2.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["action"] == "remove"
    assert actions[0]["direction"] == "AI · private"

    # Reset wipes everything
    await client.post(
        "/api/matrix_feedback/add", json={"action": "reset"}, headers=h
    )
    res3 = await client.get("/api/matrix_feedback", headers=h)
    actions3 = res3.json()["actions"]
    assert len(actions3) == 1
    assert actions3[0]["action"] == "reset"


@pytest.mark.asyncio
async def test_chat_state_fresh_user(client: AsyncClient):
    token = await _register_and_login(client, "chat@x.com", "secret-12345")
    h = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/chat_state", headers=h)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "messages" in data
    assert "llm" in data
    assert "stage" in data
    assert "journey" in data


@pytest.mark.asyncio
async def test_jobs_add_missing_fields_returns_error(client: AsyncClient):
    token = await _register_and_login(client, "val@x.com", "secret-12345")
    h = {"Authorization": f"Bearer {token}"}
    res = await client.post(
        "/api/jobs/add",
        json={"company": "", "role": "", "description": ""},
        headers=h,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
