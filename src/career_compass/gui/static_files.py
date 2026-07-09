"""Built SPA static assets (Vite → gui/static/dist)."""
from __future__ import annotations

from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
DIST_DIR = _PKG_DIR / "static" / "dist"


def spa_index_path() -> Path | None:
    path = DIST_DIR / "index.html"
    return path if path.is_file() else None


def spa_available() -> bool:
    return spa_index_path() is not None


def resolve_static_file(url_path: str) -> Path | None:
    """Map /assets/foo.js → dist/assets/foo.js (path traversal safe)."""
    if not url_path or url_path == "/":
        return None
    rel = url_path.lstrip("/")
    if ".." in rel or rel.startswith("/"):
        return None
    candidate = (DIST_DIR / rel).resolve()
    try:
        candidate.relative_to(DIST_DIR.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None
