"""项目根目录 .env 加载（不覆盖已设置的环境变量）。"""
from __future__ import annotations

import os
from pathlib import Path

# 默认 CloudBase 网关（Base URL 可公开；API Key 仅放 .env，不入库）
DEFAULT_CLOUDBASE_BASE_URL = (
    "https://dev-d7gjfebo329689c3b.api.tcloudbasegateway.com/v1/ai/cloudbase"
)
DEFAULT_LLM_MODEL = "hy3-preview"
DEFAULT_LLM_PROVIDER = "cloudbase"

_ENV_LOADED = False


def find_project_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists() and (cwd / "src" / "career_compass").exists():
        return cwd
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "src" / "career_compass").exists():
            return parent
    return cwd


def load_project_env(*, force: bool = False) -> Path | None:
    """读取项目根 `.env` 写入 os.environ（已有变量不覆盖）。"""
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return find_project_root() / ".env" if (find_project_root() / ".env").is_file() else None

    env_path = find_project_root() / ".env"
    if not env_path.is_file():
        _ENV_LOADED = True
        return None

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

    _ENV_LOADED = True
    return env_path


def ensure_llm_env_defaults() -> None:
    """未显式配置时写入 CloudBase 默认项（不含 API Key）。"""
    load_project_env()
    if not os.getenv("CC_CLOUDBASE_BASE_URL") and not os.getenv("CLOUDBASE_BASE_URL"):
        os.environ.setdefault("CC_CLOUDBASE_BASE_URL", DEFAULT_CLOUDBASE_BASE_URL)
    os.environ.setdefault("CC_LLM_MODEL", DEFAULT_LLM_MODEL)
    if not os.getenv("CC_LLM_PROVIDER"):
        key = os.getenv("CC_CLOUDBASE_API_KEY") or os.getenv("CLOUDBASE_API_KEY")
        if key:
            os.environ.setdefault("CC_LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
