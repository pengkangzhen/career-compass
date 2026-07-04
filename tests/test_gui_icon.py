from career_compass.gui.app import _app_icon_path


def test_app_icon_exists():
    path = _app_icon_path()
    assert path is not None
    assert path.endswith("app-icon.png")
