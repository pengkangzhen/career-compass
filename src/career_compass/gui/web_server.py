"""Local HTTP server — modern SPA + JSON API (WSL-friendly)."""
from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from .static_files import resolve_static_file, spa_index_path
from .web_shim import inject_web_shim

if TYPE_CHECKING:
    from .app import AppApi

_API_PREFIX = "/api/"


class _Handler(BaseHTTPRequestHandler):
    api: AppApi
    legacy_html: str | None

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        pass

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_spa_index(self) -> None:
        index = spa_index_path()
        if index is None:
            if self.legacy_html:
                page = inject_web_shim(self.legacy_html)
                self._send_bytes(200, page.encode("utf-8"), "text/html; charset=utf-8")
                return
            self.send_error(503, "Frontend not built. Run: ./scripts/build-frontend.sh")
            return
        body = index.read_bytes()
        self._send_bytes(200, body, "text/html; charset=utf-8")

    def _serve_static(self, path: str) -> bool:
        file_path = resolve_static_file(path)
        if file_path is None:
            return False
        mime, _ = mimetypes.guess_type(str(file_path))
        self._send_bytes(200, file_path.read_bytes(), mime or "application/octet-stream")
        return True

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path.startswith(_API_PREFIX):
            api_path = path[len(_API_PREFIX) :]
            if api_path == "load_all":
                self._send_json(200, self.api.load_all())
                return
            if api_path == "chat_state":
                self._send_json(200, self.api.chat_state())
                return
            self.send_error(404)
            return

        if path.startswith("/assets/") or path.endswith(
            (".js", ".css", ".svg", ".png", ".ico", ".woff", ".woff2", ".map")
        ):
            if self._serve_static(path.lstrip("/")):
                return
            self.send_error(404)
            return

        if path in ("", "/"):
            self._serve_spa_index()
            return

        # SPA client-side routes → index.html
        if spa_index_path() is not None and not path.startswith(_API_PREFIX):
            self._serve_spa_index()
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if not path.startswith(_API_PREFIX):
            self.send_error(404)
            return

        api_path = path[len(_API_PREFIX) :]
        data = self._read_json()
        try:
            if api_path == "chat_send":
                self._send_json(200, self.api.chat_send(str(data.get("message", ""))))
                return
            if api_path == "chat_reset":
                self._send_json(200, self.api.chat_reset())
                return
            if api_path == "run_command":
                self._send_json(200, self.api.run_command(str(data.get("cmd", ""))))
                return
        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})
            return
        self.send_error(404)


def run_web_server(
    api: AppApi,
    *,
    legacy_html: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
) -> None:
    handler = type(
        "BeidouHandler",
        (_Handler,),
        {"api": api, "legacy_html": legacy_html},
    )
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"北斗星 · Beidou UI: {url}")
    print(f"数据目录: {api.data_dir}")
    print("Ctrl+C 停止")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()


def start_web_server_background(
    api: AppApi,
    *,
    legacy_html: str | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> tuple[ThreadingHTTPServer, str]:
    """Start server in a daemon thread (desktop shell)."""
    handler = type(
        "BeidouHandler",
        (_Handler,),
        {"api": api, "legacy_html": legacy_html},
    )
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://{host}:{port}/"
