"""对话式 intake 引擎 —— GUI / 未来 CLI 共用。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..pipeline import run_validation
from .llm import LLMClient, LLMError, create_llm_client, get_llm_config
from .preview import build_intake_status
from .prompts import build_system_prompt
from .resume import ResumeError, extract_profile_from_resume
from .session import ChatMessage, IntakeSession, clear_session, load_session, save_session
from .writer import apply_updates, bootstrap_data_dir, build_context_snapshot

# 复用 chat() 已建立的 LLM 错误兜底文案
_LLM_UNAVAILABLE_REPLY = "⚠️ LLM 暂时不可用，请稍后再试或联系管理员"

WELCOME_MESSAGE = (
    "你好，我是北斗星的职业顾问。\n\n"
    "不用准备简历或填表——随便聊聊就行：你现在是什么阶段？最近在琢磨什么职业问题？"
    "来这里最想解决什么？"
)

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class ChatResult:
    reply: str
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    files_updated: list[str] = field(default_factory=list)
    intake_complete: bool = False
    just_completed: bool = False
    gap_hints: list[str] = field(default_factory=list)
    llm_provider: str = ""
    llm_model: str = ""


def parse_llm_response(raw: str) -> tuple[str, dict[str, str]]:
    """从 LLM 响应解析 reply 与文件 updates。"""
    match = _JSON_BLOCK.search(raw)
    if not match:
        cleaned = raw.strip()
        return cleaned, {}

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        cleaned = _JSON_BLOCK.sub("", raw).strip()
        return cleaned or raw.strip(), {}

    reply = str(payload.get("reply", "")).strip()
    updates_raw = payload.get("updates") or {}
    updates: dict[str, str] = {}
    if isinstance(updates_raw, dict):
        for key, value in updates_raw.items():
            if isinstance(key, str) and isinstance(value, str):
                updates[key] = value

    if not reply:
        reply = _JSON_BLOCK.sub("", raw).strip()

    return reply, updates


class IntakeEngine:
    def __init__(
        self,
        data_dir: Path,
        *,
        templates_dir: Path,
        llm: LLMClient | None = None,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.templates_dir = templates_dir.resolve()
        self._llm = llm

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = create_llm_client()
        return self._llm

    def get_messages(self) -> list[dict[str, str]]:
        session = load_session(self.data_dir)
        if not session.messages:
            return [{"role": "assistant", "content": WELCOME_MESSAGE}]
        return [m.to_dict() for m in session.messages]

    def reset(self) -> None:
        clear_session(self.data_dir)

    def chat(self, user_message: str) -> ChatResult:
        cfg = get_llm_config()
        text = user_message.strip()
        if not text:
            return ChatResult(
                reply="请先输入一些内容。",
                ok=False,
                llm_provider=cfg.provider,
                llm_model=cfg.model,
            )

        bootstrap_data_dir(self.data_dir, self.templates_dir)
        session = load_session(self.data_dir)
        session.messages.append(ChatMessage(role="user", content=text))

        context = build_context_snapshot(self.data_dir)
        system = build_system_prompt(templates_dir=self.templates_dir, context=context)
        llm_messages = [m.to_dict() for m in session.messages]

        try:
            raw = self.llm.complete(system=system, messages=llm_messages)
        except LLMError as e:
            session.messages.pop()
            save_session(self.data_dir, session)
            return ChatResult(
                reply=f"⚠️ {e}",
                ok=False,
                llm_provider=cfg.provider,
                llm_model=cfg.model,
            )

        reply, updates = parse_llm_response(raw)
        if not reply:
            reply = "我收到了，请再多说一些，方便我帮你整理画像。"

        errors_before, _ = run_validation(self.data_dir)
        was_complete_before = not errors_before

        files_updated = apply_updates(self.data_dir, updates)
        errors, warnings = run_validation(self.data_dir)
        intake_complete = not errors
        just_completed = intake_complete and not was_complete_before

        if intake_complete and just_completed:
            reply = (
                reply.rstrip()
                + "\n\n✅ 「认识自己」这一步已完成！你可以切换到「我的画像」查看完整结果，"
                "下一步进入「探索世界」——看看行业趋势，或让 Agent 采集市场信号。"
            )

        session.messages.append(ChatMessage(role="assistant", content=reply))
        save_session(self.data_dir, session)

        status = build_intake_status(self.data_dir)

        return ChatResult(
            reply=reply,
            ok=True,
            errors=errors,
            warnings=warnings,
            files_updated=files_updated,
            intake_complete=intake_complete,
            just_completed=just_completed,
            gap_hints=status["gap_hints"],
            llm_provider=cfg.provider,
            llm_model=cfg.model,
        )

    def ingest_resume(self, *, filename: str, content: bytes) -> ChatResult:
        """上传简历 → 解析 → 字段级 merge 进 profile。

        与 chat 共享 session/validation/ChatResult 协议，前端可以把它当作
        一条特殊的 assistant 消息处理。
        """
        cfg = get_llm_config()
        bootstrap_data_dir(self.data_dir, self.templates_dir)

        errors_before, _ = run_validation(self.data_dir)
        was_complete_before = not errors_before

        try:
            result = extract_profile_from_resume(
                data_dir=self.data_dir,
                filename=filename,
                content=content,
                llm=self.llm,
            )
        except LLMError as e:
            # self.llm 属性访问或 LLM 调用本身失败 —— 比如生产环境未装 openai
            # 包时，create_llm_client() 抛 LLMError，必须接住，否则会冒到
            # FastAPI 兜底成 500（和 chat() 的处理保持一致）。
            return ChatResult(
                reply=f"⚠️ {e}",
                ok=False,
                llm_provider=cfg.provider,
                llm_model=cfg.model,
            )
        except ResumeError as e:
            return ChatResult(
                reply=f"⚠️ {e}",
                ok=False,
                llm_provider=cfg.provider,
                llm_model=cfg.model,
            )

        if not result.ok:
            reply_text = f"⚠️ 简历解析失败：{result.error}"
            return ChatResult(
                reply=reply_text,
                ok=False,
                llm_provider=cfg.provider,
                llm_model=cfg.model,
            )

        # 把简历抽取的摘要作为一条 user + assistant 消息记进 session，让后续
        # chat 能延续上下文（LLM 知道用户已经传过简历了）
        session = load_session(self.data_dir)
        session.messages.append(
            ChatMessage(role="user", content=f"（上传了简历：{filename}）")
        )
        session.messages.append(ChatMessage(role="assistant", content=result.reply))
        save_session(self.data_dir, session)

        errors, warnings = run_validation(self.data_dir)
        intake_complete = not errors
        just_completed = intake_complete and not was_complete_before

        status = build_intake_status(self.data_dir)
        return ChatResult(
            reply=result.reply,
            ok=True,
            errors=errors,
            warnings=warnings,
            files_updated=result.files_updated,
            intake_complete=intake_complete,
            just_completed=just_completed,
            gap_hints=status["gap_hints"],
            llm_provider=cfg.provider,
            llm_model=cfg.model,
        )
