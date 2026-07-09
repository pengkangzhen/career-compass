"""LLM 提供方抽象：Anthropic、OpenAI、腾讯云 CloudBase AI。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from career_compass.env import DEFAULT_CLOUDBASE_BASE_URL, DEFAULT_LLM_MODEL, ensure_llm_env_defaults


class LLMError(Exception):
    """LLM 调用或配置错误。"""


@dataclass(frozen=True)
class LLMConfig:
    provider: str  # "anthropic" | "openai" | "cloudbase"
    model: str
    configured: bool
    base_url: str | None = None


def _env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _cloudbase_credentials() -> tuple[str, str]:
    ensure_llm_env_defaults()
    api_key = _env("CC_CLOUDBASE_API_KEY", "CLOUDBASE_API_KEY")
    base_url = _env("CC_CLOUDBASE_BASE_URL", "CLOUDBASE_BASE_URL") or DEFAULT_CLOUDBASE_BASE_URL
    return api_key, base_url


def get_llm_config() -> LLMConfig:
    """返回当前 LLM 配置（不发起网络请求）。"""
    ensure_llm_env_defaults()
    provider = _env("CC_LLM_PROVIDER").lower()
    model = _env("CC_LLM_MODEL")
    cloudbase_key, cloudbase_base = _cloudbase_credentials()

    if provider == "cloudbase":
        model = model or DEFAULT_LLM_MODEL
        return LLMConfig(
            provider="cloudbase",
            model=model,
            configured=bool(cloudbase_key and cloudbase_base),
            base_url=cloudbase_base or None,
        )
    if provider == "anthropic":
        model = model or "claude-sonnet-4-20250514"
        return LLMConfig(provider="anthropic", model=model, configured=bool(_env("ANTHROPIC_API_KEY")))
    if provider == "openai":
        model = model or "gpt-4o"
        return LLMConfig(provider="openai", model=model, configured=bool(_env("OPENAI_API_KEY")))

    if cloudbase_key and cloudbase_base:
        model = model or DEFAULT_LLM_MODEL
        return LLMConfig(
            provider="cloudbase",
            model=model,
            configured=True,
            base_url=cloudbase_base,
        )
    if _env("ANTHROPIC_API_KEY"):
        model = model or "claude-sonnet-4-20250514"
        return LLMConfig(provider="anthropic", model=model, configured=True)
    if _env("OPENAI_API_KEY"):
        model = model or "gpt-4o"
        return LLMConfig(provider="openai", model=model, configured=True)

    model = model or DEFAULT_LLM_MODEL
    return LLMConfig(provider="cloudbase", model=model, configured=False)


class LLMClient(Protocol):
    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str: ...


class AnthropicClient:
    def __init__(self, model: str) -> None:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("未安装 anthropic，请运行: uv sync --group llm") from e
        api_key = _env("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError("缺少 ANTHROPIC_API_KEY 环境变量")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=messages,
        )
        parts = [block.text for block in response.content if block.type == "text"]
        if not parts:
            raise LLMError("Anthropic 返回空响应")
        return "\n".join(parts)


class OpenAICompatibleClient:
    """OpenAI SDK + 自定义 base_url（OpenAI 官方或 CloudBase 等兼容网关）。"""

    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        try:
            import openai
        except ImportError as e:
            raise LLMError("未安装 openai，请运行: uv sync --group llm") from e
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")
        self._client = openai.OpenAI(**kwargs)
        self._model = model

    def complete(self, *, system: str, messages: list[dict[str, str]]) -> str:
        payload = [{"role": "system", "content": system}, *messages]
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=4096,
            messages=payload,
        )
        choice = response.choices[0].message.content
        if not choice:
            raise LLMError("模型返回空响应")
        return choice


def create_llm_client(config: LLMConfig | None = None) -> LLMClient:
    cfg = config or get_llm_config()
    if not cfg.configured:
        raise LLMError(
            "未配置 LLM。请设置 CloudBase（CC_CLOUDBASE_API_KEY + CC_CLOUDBASE_BASE_URL）、"
            "或 ANTHROPIC_API_KEY、或 OPENAI_API_KEY；"
            "可选 CC_LLM_PROVIDER=cloudbase|anthropic|openai、CC_LLM_MODEL=模型名"
        )
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg.model)
    if cfg.provider == "openai":
        api_key = _env("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("缺少 OPENAI_API_KEY 环境变量")
        return OpenAICompatibleClient(api_key=api_key, model=cfg.model)
    if cfg.provider == "cloudbase":
        api_key, base_url = _cloudbase_credentials()
        if not api_key or not base_url:
            raise LLMError("缺少 CC_CLOUDBASE_API_KEY 或 CC_CLOUDBASE_BASE_URL")
        return OpenAICompatibleClient(api_key=api_key, model=cfg.model, base_url=base_url)
    raise LLMError(f"未知 LLM 提供方: {cfg.provider}")
