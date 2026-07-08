"""跨平台 pywebview 后端选择。"""
from __future__ import annotations

import sys


def webview_gui() -> str | None:
    """返回 pywebview.start(gui=...) 的平台标识；None 表示自动检测。"""
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform.startswith("linux"):
        return "gtk"
    if sys.platform == "win32":
        return "edgechromium"
    return None
