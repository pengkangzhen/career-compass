from pathlib import Path

from career_compass.env import (
    DEFAULT_CLOUDBASE_BASE_URL,
    ensure_llm_env_defaults,
    load_project_env,
)


def test_load_project_env_does_not_override(monkeypatch, tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("CC_CLOUDBASE_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("CC_CLOUDBASE_API_KEY", "already-set")
    monkeypatch.chdir(tmp_path)
    load_project_env(force=True)
    assert __import__("os").environ["CC_CLOUDBASE_API_KEY"] == "already-set"


def test_ensure_llm_env_defaults_sets_base_url(monkeypatch):
    monkeypatch.delenv("CC_CLOUDBASE_BASE_URL", raising=False)
    monkeypatch.delenv("CLOUDBASE_BASE_URL", raising=False)
    monkeypatch.delenv("CC_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CC_CLOUDBASE_API_KEY", raising=False)
    ensure_llm_env_defaults()
    import os

    assert os.environ["CC_CLOUDBASE_BASE_URL"] == DEFAULT_CLOUDBASE_BASE_URL
    assert "CC_LLM_PROVIDER" not in os.environ
