import sys

from career_compass.gui.platform import webview_gui


def test_webview_gui_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert webview_gui() == "gtk"


def test_webview_gui_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert webview_gui() == "cocoa"


def test_webview_gui_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert webview_gui() == "edgechromium"
