from pathlib import Path

from career_compass.gui.view_data import build_all_views, build_profile_view
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
