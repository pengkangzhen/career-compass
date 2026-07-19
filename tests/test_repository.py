"""Unit tests for the DB-backed Repository (M3).

Verifies CRUD round-trips through the tmpdir strategy, user isolation,
and that the public method names match what routers/data.py expects.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from career_compass.web.models import Base, Constraints, Profile, User
from career_compass.web.repository import Repository

# Pre-import career_compass.cli so that the regression test below mirrors the
# SaaS web-server scenario where cli is imported once at process startup (with
# whatever CC_DATA is then) and reused for every request. Without the fix in
# _run_cli, cli.DATA / cli.PROFILE / ... would stay bound to that initial
# value regardless of the per-request CC_DATA override.
import career_compass.cli  # noqa: E402,F401


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
async def make_user(session_maker):
    """Returns (user_id, repo_factory) for a freshly registered user."""
    async with session_maker() as s:
        user_id = uuid.uuid4()
        s.add(User(id=user_id, email=f"u-{user_id.hex[:6]}@x.com", hashed_password="x"))
        await s.commit()

    def factory(session) -> Repository:
        return Repository(session, user_id)

    return user_id, factory


@pytest.mark.asyncio
async def test_load_all_empty_user(session_maker, make_user):
    """Empty user should get a valid load_all payload (no exceptions)."""
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        data = await repo.load_all()
    assert "views" in data
    assert "journey" in data
    assert data["intake_complete"] is False
    # User-owned views are empty for a fresh user.
    for view_name in ("profile", "jobs", "matrix", "execution", "track"):
        view = data["views"][view_name]
        assert view.get("empty") is True, f"{view_name} should be empty for fresh user"
    # trends is never empty for a fresh user — it always shows the repo's
    # bundled sectors.yaml (shared, read-only industry pool). User-scanned
    # signals (data.views.trends.signals) start empty.
    trends = data["views"]["trends"]
    assert trends.get("empty") is False
    assert trends["signals"] == []
    assert len(trends["sectors"]) > 0


@pytest.mark.asyncio
async def test_jobs_add_and_list(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        res = await repo.jobs_add(
            company="Acme",
            role="Engineer",
            description="Build things",
        )
        assert res["ok"] is True
        job = res["job"]
        assert job["company"] == "Acme"
        assert job["status"] == "interested"
        new_id = job["id"]

    # Verify it round-trips through DB on next load
    async with session_maker() as s:
        repo = factory(s)
        # jobs_add with same (company, role) should upsert
        res2 = await repo.jobs_add(
            company="Acme",
            role="Engineer",
            description="Updated JD text",
        )
        assert res2["ok"] is True
        assert res2["job"]["id"] == new_id
        assert res2["job"]["description"] == "Updated JD text"


@pytest.mark.asyncio
async def test_jobs_update(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        add = await repo.jobs_add(company="G", role="R", description="d")
        job_id = add["job"]["id"]
        upd = await repo.jobs_update(
            job_id,
            status="ready",
            notes="applied via referral",
            linked_direction="AI · private",
        )
        assert upd["ok"] is True
        assert upd["job"]["status"] == "ready"
        assert upd["job"]["notes"] == "applied via referral"
        assert upd["job"]["linked_direction"] == "AI · private"


@pytest.mark.asyncio
async def test_jobs_remove(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        add = await repo.jobs_add(company="X", role="Y", description="d")
        job_id = add["job"]["id"]
        rm = await repo.jobs_remove(job_id)
        assert rm["ok"] is True
        # Removing again should fail gracefully
        rm2 = await repo.jobs_remove(job_id)
        assert rm2["ok"] is False


@pytest.mark.asyncio
async def test_matrix_feedback_lifecycle(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        # Add a remove action
        r1 = await repo.matrix_feedback_add(action="remove", direction="AI · private")
        assert r1["ok"] is True
        r2 = await repo.matrix_feedback_add(
            action="note", direction="AI · private", details={"text": "looks promising"}
        )
        assert r2["ok"] is True
        r3 = await repo.matrix_feedback_add(action="reset")
        assert r3["ok"] is True

        list_res = await repo.matrix_feedback()
        actions = list_res["actions"]
        # After reset, only the reset marker remains
        assert len(actions) == 1
        assert actions[0]["action"] == "reset"


@pytest.mark.asyncio
async def test_user_isolation(session_maker, make_user):
    """User A's saved jobs must not be visible to User B."""
    user_a, _ = make_user

    # Make a second user
    user_b = uuid.uuid4()
    async with session_maker() as s:
        s.add(User(id=user_b, email="b@x.com", hashed_password="x"))
        await s.commit()

    # A adds a job
    async with session_maker() as s:
        repo_a = Repository(s, user_a)
        await repo_a.jobs_add(company="Acorp", role="R1", description="a-job")

    # B should see zero jobs
    async with session_maker() as s:
        repo_b = Repository(s, user_b)
        data_b = await repo_b.load_all()
        assert data_b["views"]["jobs"]["empty"] is True

    # B's attempt to update A's job should fail with "not found"
    async with session_maker() as s:
        repo_a = Repository(s, user_a)
        a_jobs = (await repo_a.load_all())["views"]["jobs"]
        # a_jobs is non-empty
        assert a_jobs.get("empty") is False
        a_job_id = a_jobs["jobs"][0]["id"]

    async with session_maker() as s:
        repo_b = Repository(s, user_b)
        res = await repo_b.jobs_update(a_job_id, notes="attempted takeover")
        assert res["ok"] is False
        assert "not found" in res["error"]


@pytest.mark.asyncio
async def test_jobs_add_validates_required_fields(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        # Empty company should fail
        res = await repo.jobs_add(company="", role="R", description="d")
        assert res["ok"] is False
        # Empty role should fail
        res = await repo.jobs_add(company="C", role="", description="d")
        assert res["ok"] is False


@pytest.mark.asyncio
async def test_jobs_update_invalid_status(session_maker, make_user):
    user_id, factory = make_user
    async with session_maker() as s:
        repo = factory(s)
        add = await repo.jobs_add(company="C", role="R", description="d")
        bad = await repo.jobs_update(add["job"]["id"], status="nonsense")
        assert bad["ok"] is False
        assert "invalid status" in bad["error"]


@pytest.mark.asyncio
async def test_run_command_validate_uses_tmpdir_data(session_maker, make_user):
    """run_command('validate') must operate on the user's tmpdir, not the
    repo's bundled data/.

    Regression: cli.py binds DATA at import time, so setting CC_DATA in
    _run_cli had no effect — the CLI kept reading whatever CC_DATA was when
    career_compass.cli was first imported. In the SaaS web server the cli
    module is imported once per process, so user B's validate would run
    against user A's tmpdir (or the repo's bundled data/ if cli was imported
    before any request).

    We simulate that scenario by importing career_compass.cli up-front (the
    way a long-running server would), then give the user a profile whose
    `experience[0].role` is a unique marker AND whose `experience[0].company`
    is a placeholder ("TODO"); validate() then emits a warning quoting the
    role: "经历 '<marker>' 的公司/职责含占位内容". Without the fix the CLI
    would keep using the import-time DATA binding and never see the marker.
    """
    # career_compass.cli is pre-imported at module top to mirror a
    # long-running server, where the cli module is imported once at startup
    # (binding DATA / PROFILE / ... at that moment) and reused across
    # requests. The fix in _run_cli rebinds those attrs per call.
    user_id, factory = make_user
    marker = "UniqueValidateMarker9f3a"
    profile_content = {
        "name": "Test User",
        "current_role": "数据工程师",
        "education": [
            {
                "level": "bachelor",
                "degree": "学士",
                "school": "Unique Bachelor College",
                "school_tier": "一本",
                "major": "计算机科学",
                "end_year": 2019,
                "status": "graduated",
            },
            {
                "level": "master",
                "degree": "工学硕士",
                "school": "Unique Test University",
                "school_tier": "985",
                "major": "计算机科学",
                "end_year": 2021,
                "status": "graduated",
            },
        ],
        "experience": [
            {
                "company": "TODO",
                "role": marker,
                "period": "2021-2024",
                "scope": "Building things",
                "quantified_outcomes": ["Shipped X"],
            }
        ],
        "skills": {"core": ["Python / SQL"], "adjacent": [], "frontier": []},
        "strength_evidence": [
            {"claim": "能把混乱规范化", "proof": "事故清零"},
        ],
        "preferences": {
            "energized_by": ["systems"],
            "drained_by": ["repetition"],
            "values_ranked": ["learning", "impact", "autonomy"],
        },
    }
    constraints_content = {"risk_appetite": "medium"}
    async with session_maker() as s:
        repo = factory(s)
        await repo._upsert_single(Profile, {"content": profile_content})
        await repo._upsert_single(Constraints, {"content": constraints_content})
        await s.commit()

    async with session_maker() as s:
        repo = factory(s)
        result = await repo.run_command("validate")

    output = result["output"]
    # The CLI processed the user's tmpdir profile, so the unique role marker
    # appears in validate's placeholder warning. Without the fix this would
    # be absent (CLI would read whatever DATA was bound at import time).
    assert marker in output, f"marker missing from validate output:\n{output}"
