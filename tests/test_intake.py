"""Intake 引擎单元测试（mock LLM，无网络）。"""
from __future__ import annotations

from pathlib import Path

import pytest

from career_compass.intake.engine import IntakeEngine, parse_llm_response
from career_compass.intake.llm import LLMConfig, get_llm_config
from career_compass.intake.session import load_session
from career_compass.intake.writer import apply_updates, bootstrap_data_dir, build_context_snapshot
from career_compass.pipeline import run_validation


class MockLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.response


def test_parse_llm_response_with_json_block():
    raw = """好的，我先记下你的背景。

```json
{
  "reply": "好的，我先记下你的背景。",
  "updates": {
    "profile.yaml": "name: Test\\ncurrent_role: engineer\\n"
  }
}
```"""
    reply, updates = parse_llm_response(raw)
    assert "记下" in reply
    assert "profile.yaml" in updates
    assert "name: Test" in updates["profile.yaml"]


def test_parse_llm_response_plain_text():
    reply, updates = parse_llm_response("请再多说一些你的经历。")
    assert reply == "请再多说一些你的经历。"
    assert updates == {}


def test_bootstrap_creates_files(tmp_path: Path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "profile.example.yaml").write_text("name: null\n", encoding="utf-8")
    (templates / "constraints.example.yaml").write_text("geo: []\n", encoding="utf-8")
    data = tmp_path / "data"
    bootstrap_data_dir(data, templates)
    assert (data / "profile.yaml").is_file()
    assert (data / "constraints.yaml").is_file()
    assert (data / "narrative.md").is_file()


def test_apply_updates_writes_allowed_files(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    written = apply_updates(data, {
        "profile.yaml": "name: Alice\ncurrent_role: dev\n",
        "evil.sh": "rm -rf /",
    })
    assert written == ["profile.yaml"]
    assert "Alice" in (data / "profile.yaml").read_text(encoding="utf-8")


def test_intake_engine_chat_persists_session(tmp_path: Path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "profile.example.yaml").write_text(
        "name: Bob\ncurrent_role: engineer\nskills:\n  core:\n    - Python\n"
        "strength_evidence:\n  - claim: x\n    proof: y\n"
        "preferences:\n  values_ranked:\n    - learning\n",
        encoding="utf-8",
    )
    (templates / "constraints.example.yaml").write_text(
        "geo:\n  - Shanghai\nrisk_appetite: medium\n", encoding="utf-8"
    )
    data = tmp_path / "data"

    llm = MockLLM(
        '```json\n{"reply": "收到，已记录。", "updates": {"profile.yaml": '
        '"name: Bob\\ncurrent_role: engineer\\neducation:\\n  - level: bachelor\\n'
        '    school: Test University\\n    major: CS\\n    status: graduated\\n'
        "skills:\\n  core:\\n    - Python\\nstrength_evidence:\\n"
        '  - claim: built systems\\n    proof: shipped v1 in 3 months\\n'
        "preferences:\\n  values_ranked:\\n    - learning\\n"
        '", "narrative.md": "# Narrative\\n\\n## 职业故事\\n\\nStory\\n\\n'
        '## 我想要的\\n\\nImpact\\n\\n## 红线\\n\\nNo ops\\n"}}\n```'
    )
    engine = IntakeEngine(data, templates_dir=templates, llm=llm)
    result = engine.chat("我是 Bob，做后端开发")

    assert result.ok
    assert result.reply
    session = load_session(data)
    assert len(session.messages) == 2
    assert session.messages[0].role == "user"
    assert session.messages[1].role == "assistant"
    assert (data / "profile.yaml").is_file()


def test_build_context_snapshot_includes_gaps(tmp_path: Path):
    templates = tmp_path / "templates"
    templates.mkdir()
    data = tmp_path / "data"
    bootstrap_data_dir(data, templates)
    ctx = build_context_snapshot(data)
    assert "profile.yaml" in ctx
    assert "validate" in ctx


def test_get_llm_config_prefers_explicit_provider(monkeypatch):
    monkeypatch.setenv("CC_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = get_llm_config()
    assert cfg.provider == "openai"
    assert cfg.configured is True


def test_get_llm_config_auto_anthropic(monkeypatch):
    monkeypatch.delenv("CC_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("CC_CLOUDBASE_API_KEY", raising=False)
    monkeypatch.delenv("CC_CLOUDBASE_BASE_URL", raising=False)
    monkeypatch.delenv("CLOUDBASE_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDBASE_BASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = get_llm_config()
    assert cfg.provider == "anthropic"


def test_get_llm_config_cloudbase(monkeypatch):
    monkeypatch.delenv("CC_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("CC_CLOUDBASE_API_KEY", "test-key")
    monkeypatch.setenv(
        "CC_CLOUDBASE_BASE_URL",
        "https://dev-xxx.api.tcloudbasegateway.com/v1/ai/cloudbase",
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = get_llm_config()
    assert cfg.provider == "cloudbase"
    assert cfg.configured is True
    assert cfg.model == "hy3-preview"


def test_get_llm_config_explicit_cloudbase(monkeypatch):
    monkeypatch.setenv("CC_LLM_PROVIDER", "cloudbase")
    monkeypatch.setenv("CC_LLM_MODEL", "deepseek-v3")
    monkeypatch.setenv("CC_CLOUDBASE_API_KEY", "k")
    monkeypatch.setenv("CC_CLOUDBASE_BASE_URL", "https://example.com/v1/ai/cloudbase")
    cfg = get_llm_config()
    assert cfg.provider == "cloudbase"
    assert cfg.model == "deepseek-v3"
