from pathlib import Path

from career_compass.gui.view_data import build_all_views, build_jobs_view, build_profile_view
from career_compass.gui.web_shim import WEB_API_SHIM, inject_web_shim


def test_inject_web_shim():
    html = "<html><script>\nconst x = 1;\n</script></html>"
    out = inject_web_shim(html)
    assert WEB_API_SHIM.strip() in out
    assert "const x = 1" in out


def test_build_profile_view_empty(tmp_path: Path):
    view = build_profile_view(tmp_path)
    assert view["empty"] is True


def test_build_all_views_keys(tmp_path: Path):
    views = build_all_views(tmp_path)
    assert set(views) == {"profile", "trends", "jobs", "matrix", "execution", "track"}


def test_build_jobs_view_empty(tmp_path: Path):
    view = build_jobs_view(tmp_path)
    assert view["empty"] is True
    assert view["jobs"] == []


def test_build_jobs_view_after_add(tmp_path: Path):
    from career_compass.jobs import add_saved_job

    jobs_path = tmp_path / "saved_jobs.yaml"
    add_saved_job(
        jobs_path,
        company="测试公司",
        role="算法工程师",
        description="Python LLM Agent 强化学习",
        location="北京",
        source="手动添加",
        linked_direction="AI Agent",
        notes="备注",
    )
    view = build_jobs_view(tmp_path)
    assert view["empty"] is False
    assert view["count"] == 1
    job = view["jobs"][0]
    # New fields exposed for the UI
    assert job["id"]
    assert job["source"] == "手动添加"
    assert job["linked_direction"] == "AI Agent"
    assert "Python" in job["description_preview"]


def test_app_api_jobs_add(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    res = api.jobs_add(
        company="测试公司",
        role="算法工程师",
        description="Python LLM Agent",
        location="北京",
        source="手动添加",
    )
    assert res["ok"] is True
    job = res["job"]
    assert job["company"] == "测试公司"
    assert job["source"] == "手动添加"
    assert (tmp_path / "saved_jobs.yaml").exists()


def test_app_api_jobs_add_validation(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    # Empty company/role/description should be rejected by the frontend; the
    # endpoint itself still stores whatever it gets, but at minimum an empty
    # description should not crash.
    res = api.jobs_add(company="X", role="Y", description="")
    assert res["ok"] is True


def test_app_api_jobs_update(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi
    from career_compass.schema import load_saved_jobs

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    added = api.jobs_add(
        company="测试公司",
        role="算法工程师",
        description="初始描述",
        location="北京",
    )
    assert added["ok"] is True
    job_id = added["job"]["id"]

    res = api.jobs_update(
        job_id,
        description="更新后的描述 Python LLM",
        status="researching",
        notes="测试备注",
    )
    assert res["ok"] is True
    updated = res["job"]
    assert updated["description"] == "更新后的描述 Python LLM"
    assert updated["status"] == "researching"
    assert updated["notes"] == "测试备注"

    # Persistence: re-read the file
    data = load_saved_jobs(tmp_path / "saved_jobs.yaml")
    match = next(j for j in data.jobs if j.id == job_id)
    assert match.description == "更新后的描述 Python LLM"
    assert match.status.value == "researching"


def test_app_api_jobs_update_not_found(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    res = api.jobs_update("nonexistent-id", description="foo")
    assert res["ok"] is False
    assert "not found" in res["error"]


def test_app_api_jobs_update_invalid_status(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    added = api.jobs_add(
        company="测试公司",
        role="算法工程师",
        description="初始描述",
    )
    assert added["ok"] is True
    job_id = added["job"]["id"]

    res = api.jobs_update(job_id, status="bogus")
    assert res["ok"] is False
    assert "invalid status" in res["error"]


def test_app_api_jobs_remove(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi
    from career_compass.schema import load_saved_jobs

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    added = api.jobs_add(
        company="测试公司",
        role="算法工程师",
        description="初始描述",
    )
    job_id = added["job"]["id"]
    assert job_id

    res = api.jobs_remove(job_id)
    assert res["ok"] is True
    assert res["removed"] == job_id

    data = load_saved_jobs(tmp_path / "saved_jobs.yaml")
    assert all(j.id != job_id for j in data.jobs)


def test_app_api_jobs_remove_not_found(tmp_path: Path, monkeypatch):
    from career_compass.gui.app import AppApi

    monkeypatch.setenv("CC_DATA", str(tmp_path))
    api = AppApi()
    res = api.jobs_remove("nonexistent-id")
    assert res["ok"] is False
    assert "not found" in res["error"]


def test_build_jobs_view_has_full_description(tmp_path: Path):
    from career_compass.jobs import add_saved_job
    from career_compass.gui.view_data import build_jobs_view

    jobs_path = tmp_path / "saved_jobs.yaml"
    long_desc = "Line 1\nLine 2\n" + ("x" * 500)
    add_saved_job(
        jobs_path,
        company="测试公司",
        role="算法工程师",
        description=long_desc,
    )
    view = build_jobs_view(tmp_path)
    assert view["empty"] is False
    job = view["jobs"][0]
    # Full description should be present and equal to the original
    assert job["description"] == long_desc.strip()
    # Preview should be present and shorter than the full text
    assert job["description_preview"]
    assert len(job["description_preview"]) < len(long_desc)
