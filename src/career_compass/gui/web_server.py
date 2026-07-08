"""本地 HTTP 服务 —— 在浏览器中打开北斗星 UI（WSL 友好）。"""
from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from .web_shim import WEB_API_SHIM

if TYPE_CHECKING:
    from .app import AppApi


def inject_web_shim(html: str) -> str:
    marker = "<script>"
    if marker not in html:
        return html
    return html.replace(marker, f"<script>\n{WEB_API_SHIM}\n", 1)


class _Handler(BaseHTTPRequestHandler):
    api: AppApi
    page_html: str

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("", "/"):
            body = self.page_html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/load_all":
            self._send_json(200, self.api.load_all())
            return
        if path == "/api/chat_state":
            self._send_json(200, self.api.chat_state())
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        data = self._read_json()
        try:
            if path == "/api/chat_send":
                self._send_json(200, self.api.chat_send(str(data.get("message", ""))))
                return
            if path == "/api/chat_reset":
                self._send_json(200, self.api.chat_reset())
                return
            if path == "/api/run_command":
                self._send_json(200, self.api.run_command(str(data.get("cmd", ""))))
                return
        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})
            return
        self.send_error(404)


def run_web_server(api: AppApi, *, html: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    page = inject_web_shim(html)
    handler = type(
        "BeidouHandler",
        (_Handler,),
        {"api": api, "page_html": page},
    )
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"北斗星 Web UI: {url}")
    print("在 Windows 浏览器打开上述地址（WSL 下 localhost 通常可用）")
    print("Ctrl+C 停止")

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()
