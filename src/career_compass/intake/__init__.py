"""GUI / CLI 共用的对话式 intake 引擎。"""
from __future__ import annotations

from .engine import ChatResult, IntakeEngine, WELCOME_MESSAGE
from .llm import LLMConfig, LLMError, get_llm_config
from .preview import build_intake_status

__all__ = [
    "ChatResult",
    "IntakeEngine",
    "WELCOME_MESSAGE",
    "LLMConfig",
    "LLMError",
    "get_llm_config",
    "build_intake_status",
]
