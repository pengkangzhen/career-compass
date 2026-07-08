from career_compass.gui.web_server import inject_web_shim
from career_compass.gui.web_shim import WEB_API_SHIM


def test_inject_web_shim():
    html = "<html><script>\nconst x = 1;\n</script></html>"
    out = inject_web_shim(html)
    assert WEB_API_SHIM.strip() in out
    assert "const x = 1" in out
